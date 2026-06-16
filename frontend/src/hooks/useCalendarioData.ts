import { useEffect, useMemo, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import type { Training } from '@/types/training';

function formatYMDLocal(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function useCalendarioData(userId: string |undefined, semanaOffset: number) {
  const [hasStrava, setHasStrava] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [trainingsByDate, setTrainingsByDate] = useState<Record<string, Training[]>>({});
  const [refetchTrigger, setRefetchTrigger] = useState(0);
  const [userFtp, setUserFtp] = useState<number | null>(null);
  const [userWeight, setUserWeight] = useState<number | null>(null);

  const { startOfWeek, endOfWeek } = useMemo(() => {
    const hoy = new Date();
    const hoyDia = hoy.getDay() === 0 ? 6 : hoy.getDay() - 1;

    const start = new Date(hoy);
    start.setHours(0, 0, 0, 0);
    start.setDate(hoy.getDate() - hoyDia + semanaOffset * 7);

    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    end.setHours(23, 59, 59, 999);

    return { startOfWeek: start, endOfWeek: end };
  }, [semanaOffset]);

  const refetch = () => {
    setRefetchTrigger(prev => prev + 1);
  };

  useEffect(() => {
    if (!userId) {
      return;
    }

    let cancelled = false;

    const fetchData = async () => {
      try {
        setLoading(true);

        const startStr = formatYMDLocal(startOfWeek);
        const endStr = formatYMDLocal(endOfWeek);

        const { data: stravaAccount, error: stravaError } = await supabase
          .from('strava_accounts')
          .select('strava_id')
          .eq('user_id', userId)
          .maybeSingle();

        if (stravaError) console.error('[useCalendarioData] Strava error:', stravaError);
        if (cancelled) return;

        setHasStrava(!!stravaAccount?.strava_id);

        const { data: userProfile } = await supabase
          .from('users')
          .select('ftp, weight')
          .eq('id', userId)
          .maybeSingle();
        if (!cancelled && userProfile) {
          if (userProfile.ftp) setUserFtp(userProfile.ftp);
          if (userProfile.weight) setUserWeight(userProfile.weight);
        }

        const { data: trainings, error: trainingsError } = await supabase
          .from('trainings')
          .select('activity_id, name, type, date, duration, distance, avgheartrate, weighted_average_watts, altitude, TSS, power_stream, hr_stream, time_stream, laps')
          .eq('user_id', userId)
          .gte('date', startStr)
          .lte('date', endStr);

        if (trainingsError) {
          console.error('[useCalendarioData] Trainings error:', trainingsError);
        }

        if (cancelled) return;

        const grouped: Record<string, Training[]> = {};
        (trainings ?? []).forEach((t: Training) => {
          (grouped[t.date] ||= []).push(t);
        });

        setTrainingsByDate(grouped);
      } catch (err) {
        console.error('[useCalendarioData] Error inesperado:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchData();

    return () => {
      cancelled = true;
    };
  }, [userId, semanaOffset, startOfWeek, endOfWeek, refetchTrigger]);

  useEffect(() => {
    console.groupCollapsed('[useCalendarioData] 📦 state update');
    console.log('loading:', loading);
    console.log('hasStrava:', hasStrava);
    console.log('trainingsByDate keys:', Object.keys(trainingsByDate));
    console.groupEnd();
  }, [loading, hasStrava, trainingsByDate]);

  return {
    hasStrava,
    loading,
    trainingsByDate,
    startOfWeek,
    refetch,
    userFtp,
    userWeight,
  };
}
