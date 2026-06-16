'use client';
import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';

export type WeeklySummary = {
  iso_year: number;
  iso_week: number;
  week_start_date: string;
  completed_sessions_count: number;
  completed_hours: number;
  completed_distance_km: number;
  completed_tss: number;
  ctl_end: number | null;
  atl_end: number | null;
  tsb_end: number | null;
  power_zones_minutes: Record<string, number> | null;
  hr_zones_minutes: Record<string, number> | null;
};

export type TodayMetrics = {
  ctl: number | null;
  atl: number | null;
  tsb: number | null;
  resting_hr: number | null;
  hrv: number | null;
  sleep_hours: number | null;
  weight: number | null;
};

export type YesterdayMetrics = {
  ctl: number | null;
  atl: number | null;
  tsb: number | null;
};

export type MmpCurve = Record<string, number>; // {"1": 950, "5": 780, ...}

export type AthleteProfile = {
  weight: number | null;
  ftp: number | null;
  best_mmp_curve: MmpCurve | null;
};

export type TrendPoint = {
  date: string;
  label: string;
  ctl: number;
  atl: number;
  tsb: number;
};

export function useDashboardData(userId: string | undefined) {
  const [currentWeek, setCurrentWeek] = useState<WeeklySummary | null>(null);
  const [last9Weeks, setLast9Weeks] = useState<WeeklySummary[]>([]);
  const [today, setToday] = useState<TodayMetrics>({ ctl: null, atl: null, tsb: null, resting_hr: null, hrv: null, sleep_hours: null, weight: null });
  const [yesterday, setYesterday] = useState<YesterdayMetrics>({ ctl: null, atl: null, tsb: null });
  const [profile, setProfile] = useState<AthleteProfile>({ weight: null, ftp: null, best_mmp_curve: null });
  const [trendData, setTrendData] = useState<TrendPoint[]>([]);
  const [recentMmp, setRecentMmp] = useState<MmpCurve | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) return;

    const load = async () => {
      setLoading(true);

      const todayIso = new Date().toISOString().slice(0, 10);
      const since42Days = new Date();
      since42Days.setDate(since42Days.getDate() - 42);
      const sinceStr = since42Days.toISOString().slice(0, 10);

      const yesterdayDate = new Date();
      yesterdayDate.setDate(yesterdayDate.getDate() - 1);
      const yesterdayIso = yesterdayDate.toISOString().slice(0, 10);

      const [weekliesRes, todayRes, profileRes, trendRes, yesterdayRes, recentMmpRes] = await Promise.all([
        supabase
          .from('weekly_summaries')
          .select('iso_year, iso_week, week_start_date, completed_sessions_count, completed_hours, completed_distance_km, completed_tss, ctl_end, atl_end, tsb_end, power_zones_minutes, hr_zones_minutes')
          .eq('user_id', userId)
          .order('week_start_date', { ascending: false })
          .limit(9),

        supabase
          .from('daily_metrics')
          .select('ctl, atl, tsb, resting_hr, hrv, sleep_hours, weight')
          .eq('user_id', userId)
          .eq('date', todayIso)
          .maybeSingle(),

        supabase
          .from('users')
          .select('weight, ftp, best_mmp_curve')
          .eq('id', userId)
          .maybeSingle(),

        supabase
          .from('daily_metrics')
          .select('date, ctl, atl, tsb')
          .eq('user_id', userId)
          .gte('date', sinceStr)
          .order('date', { ascending: true }),

        supabase
          .from('daily_metrics')
          .select('ctl, atl, tsb')
          .eq('user_id', userId)
          .eq('date', yesterdayIso)
          .maybeSingle(),

        // Curva MMP de las últimas 4 semanas
        supabase
          .from('trainings')
          .select('mmp_curve')
          .eq('user_id', userId)
          .gte('date', (() => { const d = new Date(); d.setDate(d.getDate() - 28); return d.toISOString().slice(0, 10); })())
          .not('mmp_curve', 'is', null),
      ]);

      if (weekliesRes.data && weekliesRes.data.length > 0) {
        setCurrentWeek(weekliesRes.data[0]);
        setLast9Weeks([...weekliesRes.data].reverse());
      }

      if (todayRes.data) {
        setToday({
          ctl: todayRes.data.ctl ?? null,
          atl: todayRes.data.atl ?? null,
          tsb: todayRes.data.tsb ?? null,
          resting_hr: todayRes.data.resting_hr ?? null,
          hrv: todayRes.data.hrv ?? null,
          sleep_hours: todayRes.data.sleep_hours ?? null,
          weight: todayRes.data.weight ?? null,
        });
      }

      if (profileRes.data) {
        setProfile({
          weight: profileRes.data.weight ?? null,
          ftp: profileRes.data.ftp ?? null,
          best_mmp_curve: (profileRes.data.best_mmp_curve as MmpCurve) ?? null,
        });
      }

      // Calcular curva MMP de las últimas 4 semanas (máximo por duración)
      if (recentMmpRes.data && recentMmpRes.data.length > 0) {
        const merged: MmpCurve = {};
        for (const row of recentMmpRes.data) {
          const curve = row.mmp_curve as MmpCurve | null;
          if (!curve) continue;
          for (const [dur, watts] of Object.entries(curve)) {
            if (!merged[dur] || watts > merged[dur]) merged[dur] = watts;
          }
        }
        setRecentMmp(Object.keys(merged).length > 0 ? merged : null);
      }

      if (trendRes.data && trendRes.data.length > 0) {
        setTrendData(trendRes.data.map(r => {
          const parts = r.date.split('-');
          return {
            date: r.date,
            label: `${parts[2]}/${parts[1]}`,
            ctl: Number(r.ctl ?? 0),
            atl: Number(r.atl ?? 0),
            tsb: Number(r.tsb ?? 0),
          };
        }));
      }

      if (yesterdayRes.data) {
        setYesterday({
          ctl: yesterdayRes.data.ctl ?? null,
          atl: yesterdayRes.data.atl ?? null,
          tsb: yesterdayRes.data.tsb ?? null,
        });
      }

      setLoading(false);
    };

    load();
  }, [userId]);

  return { currentWeek, last9Weeks, today, yesterday, profile, trendData, recentMmp, loading };
}
