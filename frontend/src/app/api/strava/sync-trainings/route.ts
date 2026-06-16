import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

function calculateTSS(
  duration_sec: number | null,
  np: number | null,
  ftp: number | null,
): number | null {
  if (!duration_sec || !np || !ftp || ftp === 0) return null;
  const IF = np / ftp;
  return Math.round((duration_sec * np * IF) / (ftp * 3600) * 100);
}

function calculateNP(powerStream: number[]): number | null {
  if (!powerStream || powerStream.length < 30) return null;
  const windowSize = 30;
  const rolling: number[] = [];
  for (let i = 0; i <= powerStream.length - windowSize; i++) {
    const slice = powerStream.slice(i, i + windowSize);
    const avg = slice.reduce((a, b) => a + b, 0) / windowSize;
    rolling.push(avg);
  }
  const fourthPowers = rolling.map(v => Math.pow(v, 4));
  const meanFourth = fourthPowers.reduce((a, b) => a + b, 0) / fourthPowers.length;
  return Math.round(Math.pow(meanFourth, 0.25));
}

const MMP_DURATIONS = [1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600];
type MmpCurve = Record<string, number>;

function calculateMMP(powerStream: number[]): MmpCurve | null {
  if (!powerStream || powerStream.length < 5) return null;
  const curve: MmpCurve = {};
  for (const dur of MMP_DURATIONS) {
    if (dur > powerStream.length) break;
    let maxAvg = 0;
    for (let i = 0; i <= powerStream.length - dur; i++) {
      let sum = 0;
      for (let j = i; j < i + dur; j++) sum += powerStream[j];
      const avg = sum / dur;
      if (avg > maxAvg) maxAvg = avg;
    }
    if (maxAvg > 0) curve[String(dur)] = Math.round(maxAvg);
  }
  return Object.keys(curve).length > 0 ? curve : null;
}

function mergeBestMMP(existing: MmpCurve | null, newCurve: MmpCurve): MmpCurve {
  const merged: MmpCurve = { ...(existing ?? {}) };
  for (const [dur, watts] of Object.entries(newCurve)) {
    if (!merged[dur] || watts > merged[dur]) merged[dur] = watts;
  }
  return merged;
}

async function refreshStravaToken(refreshToken: string) {
  const res = await fetch('https://www.strava.com/oauth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: process.env.STRAVA_CLIENT_ID!,
      client_secret: process.env.STRAVA_CLIENT_SECRET!,
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
    }),
  });
  if (!res.ok) throw new Error(`Strava token refresh failed: ${await res.text()}`);
  return res.json() as Promise<{ access_token: string; refresh_token: string; expires_at: number }>;
}

async function fetchStravaActivities(accessToken: string, afterEpoch: number) {
  const activities: Array<Record<string, unknown>> = [];
  let page = 1;
  while (true) {
    const url = new URL('https://www.strava.com/api/v3/athlete/activities');
    url.searchParams.set('after', String(afterEpoch));
    url.searchParams.set('per_page', '200');
    url.searchParams.set('page', String(page));
    const res = await fetch(url.toString(), { headers: { Authorization: `Bearer ${accessToken}` } });
    if (!res.ok) throw new Error(`Strava activities failed: ${await res.text()}`);
    const batch = (await res.json()) as Array<Record<string, unknown>>;
    activities.push(...batch);
    if (batch.length < 200) break;
    page += 1;
  }
  return activities;
}

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const userId = body.userId as string | undefined;
    const startDate = body.startDate as string | undefined;
    const endDate = body.endDate as string | undefined;
    const lookbackDays = Number(body.lookbackDays ?? 30);
    const fullImport = body.fullImport === true;

    if (!userId) return NextResponse.json({ error: 'Missing userId' }, { status: 400 });

    // 1) cargar cuenta strava
    const { data: acc, error: accErr } = await supabaseAdmin
      .from('strava_accounts')
      .select('user_id, refresh_token, access_token, expires_at')
      .eq('user_id', userId)
      .maybeSingle();
    if (accErr) throw accErr;
    if (!acc) return NextResponse.json({ error: 'No Strava account' }, { status: 400 });

    // 2) determinar desde cuándo sincronizar
    let afterEpoch: number;
    if (startDate && endDate) {
      afterEpoch = Math.floor(new Date(startDate).getTime() / 1000);
    } else {
      const now = new Date();
      const fallback = new Date(now);
      fallback.setDate(now.getDate() - Number(lookbackDays));
      if (!fullImport) {
        const { data: lastRow, error: lastErr } = await supabaseAdmin
          .from('trainings').select('date').eq('user_id', userId)
          .order('date', { ascending: false }).limit(1).maybeSingle();
        if (lastErr) throw lastErr;
        const sinceDate = lastRow?.date ? new Date(lastRow.date) : fallback;
        sinceDate.setDate(sinceDate.getDate() - 1);
        afterEpoch = Math.floor(sinceDate.getTime() / 1000);
      } else {
        afterEpoch = Math.floor(fallback.getTime() / 1000);
      }
    }

    // 3) refresh token si hace falta
    let accessToken = acc.access_token;
    if (!accessToken || Date.now() / 1000 > (acc.expires_at ?? 0) - 60) {
      const t = await refreshStravaToken(acc.refresh_token);
      accessToken = t.access_token;
      await supabaseAdmin.from('strava_accounts').update({
        access_token: t.access_token,
        refresh_token: t.refresh_token,
        expires_at: t.expires_at,
      }).eq('user_id', userId);
    }

    // 4) actividades
    const activities = await fetchStravaActivities(accessToken, afterEpoch);

    // 5) filtrar ciclismo
    let cycling = activities.filter(a =>
      ['Ride', 'VirtualRide', 'EBikeRide', 'eBikeRide'].includes(String(a.type))
    );
    if (startDate && endDate) {
      cycling = cycling.filter(a => {
        const d = String(a.start_date_local ?? a.start_date).slice(0, 10);
        return d >= startDate && d <= endDate;
      });
    }

    // 5b) FTP del usuario
    const { data: userProfile } = await supabaseAdmin
      .from('users').select('ftp, best_mmp_curve').eq('id', userId).maybeSingle();
    const ftp = userProfile?.ftp ?? null;
    let bestMmp: MmpCurve = (userProfile?.best_mmp_curve as MmpCurve) ?? {};

    // 6) streams + laps en SERIE con delay para respetar rate limit
    const DELAY_MS = 300;
    const rows = [];

    for (const a of cycling) {
      let powerStream: number[] | null = null;
      let hrStream: number[] | null = null;
      let timeStream: number[] | null = null; // segundos reales de cada muestra
      let laps = null;

      // Streams: pedimos time, watts y heartrate juntos (1 sola request)
      try {
        const streamUrl = `https://www.strava.com/api/v3/activities/${a.id}/streams?keys=time,watts,heartrate&key_by_type=true`;
        const streamRes = await fetch(streamUrl, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (streamRes.status === 429) {
          console.warn(`Rate limit fetching streams for ${a.id}`);
        } else if (streamRes.ok) {
          const streams = await streamRes.json() as Record<string, { data: number[] }>;
          timeStream  = streams.time?.data    || null;
          powerStream = streams.watts?.data   || null;
          hrStream    = streams.heartrate?.data || null;
        } else {
          console.warn(`Failed streams for ${a.id}: ${streamRes.status}`);
        }
      } catch (err) {
        console.warn(`Failed streams for ${a.id}:`, err);
      }

      // Laps
      try {
        const lapsRes = await fetch(`https://www.strava.com/api/v3/activities/${a.id}/laps`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (lapsRes.status === 429) {
          console.warn(`Rate limit fetching laps for ${a.id}`);
        } else if (lapsRes.ok) {
          const rawLaps = await lapsRes.json() as Array<Record<string, unknown>>;
          laps = rawLaps.map(l => ({
            index:        Number(l.lap_index ?? 0),
            name:         String(l.name ?? ''),
            elapsed_time: Number(l.elapsed_time ?? 0),
            distance:     Number(l.distance ?? 0),
            avg_watts:    l.average_watts    != null ? Number(l.average_watts)    : null,
            avg_hr:       l.average_heartrate != null ? Number(l.average_heartrate) : null,
            max_hr:       l.max_heartrate    != null ? Number(l.max_heartrate)    : null,
            avg_speed:    l.average_speed    != null ? Number(l.average_speed)    : null,
          }));
        } else {
          console.warn(`Failed laps for ${a.id}: ${lapsRes.status}`);
        }
      } catch (err) {
        console.warn(`Failed laps for ${a.id}:`, err);
      }

      const np = powerStream
        ? calculateNP(powerStream)
        : (a.weighted_average_watts ? Number(a.weighted_average_watts) : null);
      const mmpCurve = powerStream ? calculateMMP(powerStream) : null;
      if (mmpCurve) bestMmp = mergeBestMMP(bestMmp, mmpCurve);

      rows.push({
        user_id:                userId,
        activity_id:            Number(a.id),
        name:                   String(a.name ?? 'Entreno'),
        type:                   String(a.type),
        date:                   String(a.start_date_local ?? a.start_date).slice(0, 10),
        distance:               Number(a.distance),
        duration:               Math.round(Number(a.moving_time ?? a.elapsed_time ?? 0)),
        avgheartrate:           a.average_heartrate ? Number(a.average_heartrate) : null,
        weighted_average_watts: np,
        altitude:               a.total_elevation_gain ? Number(a.total_elevation_gain) : null,
        power_stream:           powerStream,
        hr_stream:              hrStream,
        time_stream:            timeStream,
        mmp_curve:              mmpCurve,
        laps,
        TSS: calculateTSS(
          Math.round(Number(a.moving_time ?? a.elapsed_time ?? 0)),
          np,
          ftp,
        ),
      });

      await sleep(DELAY_MS);
    }

    // 7) UPSERT
    const { error: upErr } = await supabaseAdmin
      .from('trainings')
      .upsert(rows, { onConflict: 'activity_id' });
    if (upErr) throw upErr;

    // 8) best_mmp_curve
    if (Object.keys(bestMmp).length > 0) {
      await supabaseAdmin.from('users').update({ best_mmp_curve: bestMmp }).eq('id', userId);
    }

    // Fire & forget: recalcular métricas
    const backendUrl = process.env.BACKEND_URL ?? 'http://localhost:8000';
    fetch(`${backendUrl}/api/metrics/recalculate?user_id=${userId}`, { method: 'POST' }).catch(() => {});

    return NextResponse.json({
      insertedOrUpdated: rows.length,
      dateRange: startDate && endDate ? `${startDate} to ${endDate}` : 'auto',
    });
  } catch (e) {
    const error = e as Error;
    console.error(error);
    return NextResponse.json({ error: error.message ?? 'Unknown error' }, { status: 500 });
  }
}
