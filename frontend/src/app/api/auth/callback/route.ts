// src/app/api/auth/callback/route.ts
import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

type StravaActivity = {
  id: number;
  name: string;
  start_date: string;
  distance: number;
  moving_time: number;
  average_heartrate: number | null;
  weighted_average_watts: number | null;
  average_watts: number | null;
  total_elevation_gain: number;
  type: string;
};

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const code = searchParams.get('code');
  const stateUserId = searchParams.get('state');

  if (!code || !stateUserId) {
    return NextResponse.json({ error: 'Missing code or user state' }, { status: 400 });
  }

  const tokenRes = await fetch('https://www.strava.com/oauth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: process.env.STRAVA_CLIENT_ID,
      client_secret: process.env.STRAVA_CLIENT_SECRET,
      code,
      grant_type: 'authorization_code',
      redirect_uri: process.env.STRAVA_REDIRECT_URI,
    }),
  });

  const tokenData = await tokenRes.json();

  if (!tokenRes.ok) {
    console.error('Strava token error:', tokenData);
    return NextResponse.json({ error: 'Token exchange failed' }, { status: 500 });
  }

  const athlete = tokenData.athlete;

  // Guardar en strava_accounts
  const { error } = await supabase.from('strava_accounts').upsert(
    {
      strava_id: athlete.id,
      firstname: athlete.firstname,
      lastname: athlete.lastname,
      access_token: tokenData.access_token,
      refresh_token: tokenData.refresh_token,
      expires_at: tokenData.expires_at,
      user_id: stateUserId,
    },
    { onConflict: 'strava_id' }
  );

  if (error) {
  console.error('Supabase error:', error);
  return NextResponse.json(
    { error: error.message, details: error.details, hint: error.hint, code: error.code },
    { status: 500 }
  );
  }


  // Cargar actividades de los últimos 7 días
  const after = Math.floor(Date.now() / 1000) - 7 * 24 * 60 * 60;
  const activitiesRes = await fetch(
    `https://www.strava.com/api/v3/athlete/activities?after=${after}`,
    {
      headers: {
        Authorization: `Bearer ${tokenData.access_token}`,
      },
    }
  );

  const activitiesData: StravaActivity[] = await activitiesRes.json();

  const trainings = activitiesData.map((a) => ({
    activity_id: a.id,
    name: a.name,
    date: new Date(a.start_date).toISOString().split('T')[0],
    distance: a.distance,
    duration: a.moving_time,
    avgheartrate: a.average_heartrate,
    avgpower: a.average_watts,
    weighted_average_watts: a.weighted_average_watts,
    type: a.type,
    user_id: stateUserId,
  }));

  if (trainings.length) {
    const { error: insertError } = await supabase
      .from('trainings')
      .upsert(trainings, { onConflict: 'activity_id' });

    if (insertError) {
      console.error('Error inserting trainings:', insertError);
    }
  }

  const redirectUrl = new URL('/calendario', process.env.BASE_URL || 'http://localhost:3000');
  return NextResponse.redirect(redirectUrl);
}
