'use client';
import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import type { PlannedWorkout } from '@/components/PlannedWorkoutCard';

export function usePlannedWorkout(userId: string | undefined, dateKey: string | undefined) {
  const [loading, setLoading] = useState(false);
  const [workouts, setWorkouts] = useState<PlannedWorkout[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  useEffect(() => {
    const run = async () => {
      if (!userId || !dateKey) {
        setWorkouts([]);
        return;
      }

      setLoading(true);
      setError(null);

      const { data, error } = await supabase
        .from('planned_workouts')
        .select('id,user_id,date,title,description,planned_duration_s,planned_distance_m,estimated_tss,structure,status,source,created_at,updated_at,nutrition')
        .eq('user_id', userId)
        .eq('date', dateKey)
        .order('created_at', { ascending: true });

      if (error) {
        setError(error.message);
        setWorkouts([]);
      } else {
        setWorkouts((data as PlannedWorkout[]) ?? []);
      }

      setLoading(false);
    };

    run();
  }, [userId, dateKey, refetchTrigger]);

  const refetch = () => setRefetchTrigger(t => t + 1);

  // Expose the first workout for callers that expect a single item.
  return { loading, workouts, workout: workouts[0] ?? null, error, refetch };
}
