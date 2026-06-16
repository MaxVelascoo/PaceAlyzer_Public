'use client';
import React, { useEffect, useState } from 'react';
import { Syne } from 'next/font/google';
import {
  ResponsiveContainer,
  BarChart,
  XAxis,
  YAxis,
  Tooltip,
  Bar,
  CartesianGrid,
  Cell,
} from 'recharts';
import { useUser } from '@/context/userContext';
import { supabase } from '@/lib/supabaseClient';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });

type Lap = {
  activity_id: number;
  lap_index: number;
  duration_seconds: number;
  average_watts: number;
  average_heartrate: number;
};

type Props = {
  laps: Lap[];
};

export default function LapsBarChart({ laps }: Props) {
  const user = useUser()?.user;
  const [ftp, setFtp] = useState<number | null>(null);

  useEffect(() => {
    if (!user) return;
    const fetchFtp = async () => {
      const { data } = await supabase
        .from('users')
        .select('ftp')
        .eq('id', user.id)
        .maybeSingle();

      if (data?.ftp) setFtp(data.ftp);
    };

    fetchFtp();
  }, [user]);

  const data = laps.map((lap) => ({
    lap: `Lap ${lap.lap_index}`,
    potencia: Math.round(lap.average_watts),
  }));

  const getColor = (watts: number): string => {
    if (ftp === null) return '#ccc';
    const ratio = watts / ftp;

    if (ratio < 0.7) return '#A2D2FF';
    if (ratio < 0.9) return '#FFC8A2';
    if (ratio < 1.05) return '#FFB347';
    if (ratio < 1.2) return '#FF6B00';
    return '#FF3B3B';
  };

  return (
    <div className="card laps-bar-chart">
      <h4 className={`card-title ${syne.className}`}>POTENCIA POR LAP</h4>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="lap" />
          <YAxis label={{ value: 'Watts', angle: -90, position: 'insideLeft' }} />
          <Tooltip formatter={(value) => `${value} W`} />
          <Bar dataKey="potencia">
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColor(entry.potencia)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
