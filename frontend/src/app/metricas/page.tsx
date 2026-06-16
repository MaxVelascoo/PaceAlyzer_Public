'use client';
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Syne } from 'next/font/google';
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';
import ProtectedRoute from '@/components/ProtectedRoute';
import { useUser } from '@/context/userContext';
import { supabase } from '@/lib/supabaseClient';
import styles from './metricas.module.css';

const syne = Syne({ subsets: ['latin'], weight: ['700', '800'] });

type DataPoint = {
  date: string;
  label: string;
  weight: number | null;
  resting_hr: number | null;
  hrv: number | null;
  sleep_hours: number | null;
};

function fmt(iso: string) {
  const [, m, d] = iso.split('-');
  return `${d}/${m}`;
}

function avg(arr: (number | null)[]): number | null {
  const vals = arr.filter((v): v is number => v != null);
  return vals.length ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10 : null;
}

function StatCard({
  label, value, unit, color, sub,
}: { label: string; value: string | number | null; unit?: string; color: string; sub?: string }) {
  return (
    <div className={styles.statCard}>
      <span className={styles.statLabel}>{label}</span>
      <div className={styles.statValueRow}>
        <span className={styles.statValue} style={{ color }}>
          {value ?? '—'}
          {value != null && unit && <span className={styles.statUnit}>{unit}</span>}
        </span>
      </div>
      {sub && <span className={styles.statSub}>{sub}</span>}
    </div>
  );
}

function MetricChart({
  data, dataKey, color, label, unit, referenceValue,
}: {
  data: DataPoint[];
  dataKey: keyof DataPoint;
  color: string;
  label: string;
  unit: string;
  referenceValue?: number | null;
}) {
  const filtered = data.filter(d => d[dataKey] != null);
  if (filtered.length === 0) {
    return (
      <div className={styles.chartCard}>
        <div className={styles.chartHeader}>
          <h3 className={`${styles.chartTitle} ${syne.className}`}>{label}</h3>
        </div>
        <div className={styles.chartEmpty}>Sin datos suficientes</div>
      </div>
    );
  }

  const gradId = `grad_${dataKey}`;
  return (
    <div className={styles.chartCard}>
      <div className={styles.chartHeader}>
        <h3 className={`${styles.chartTitle} ${syne.className}`}>{label}</h3>
        <span className={styles.chartUnit}>{unit}</span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.25} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(15,15,20,0.06)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: 'rgba(15,15,20,0.4)' }}
            axisLine={false} tickLine={false}
            interval={Math.max(0, Math.floor(data.length / 8) - 1)}
          />
          <YAxis
            tick={{ fontSize: 10, fill: 'rgba(15,15,20,0.4)' }}
            axisLine={false} tickLine={false}
            domain={['auto', 'auto']}
          />
          <Tooltip
            contentStyle={{ borderRadius: 10, fontSize: 12, border: '1px solid rgba(15,15,20,0.08)' }}
            labelFormatter={v => v}
            formatter={(val: number) => [`${val} ${unit}`, label]}
          />
          {referenceValue != null && (
            <ReferenceLine
              y={referenceValue}
              stroke={color}
              strokeDasharray="4 4"
              strokeOpacity={0.4}
            />
          )}
          <Area
            type="monotone"
            dataKey={dataKey as string}
            stroke={color}
            strokeWidth={2}
            fill={`url(#${gradId})`}
            dot={false}
            connectNulls={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function MetricasPage() {
  const user = useUser()?.user;
  const router = useRouter();
  const [data, setData] = useState<DataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState<30 | 60 | 90>(30);

  useEffect(() => {
    if (!user?.id) return;
    const load = async () => {
      setLoading(true);
      const since = new Date();
      since.setDate(since.getDate() - range);
      const sinceStr = since.toISOString().slice(0, 10);

      const { data: rows } = await supabase
        .from('daily_metrics')
        .select('date, weight, resting_hr, hrv, sleep_hours')
        .eq('user_id', user.id)
        .gte('date', sinceStr)
        .order('date', { ascending: true });

      setData(
        (rows ?? []).map(r => ({
          date: r.date,
          label: fmt(r.date),
          weight: r.weight ?? null,
          resting_hr: r.resting_hr ?? null,
          hrv: r.hrv ?? null,
          sleep_hours: r.sleep_hours ?? null,
        }))
      );
      setLoading(false);
    };
    load();
  }, [user?.id, range]);

  const weights = data.map(d => d.weight);
  const hrs = data.map(d => d.resting_hr);
  const hrvs = data.map(d => d.hrv);
  const sleeps = data.map(d => d.sleep_hours);

  const latest = data[data.length - 1] ?? null;

  return (
    <ProtectedRoute>
      <div className={styles.page}>
        <div className={styles.container}>

          {/* Header */}
          <div className={styles.header}>
            <button className={styles.backBtn} onClick={() => router.back()}>← Volver</button>
            <div className={styles.headerRight}>
              {([30, 60, 90] as const).map(r => (
                <button
                  key={r}
                  className={`${styles.rangeBtn} ${range === r ? styles.rangeBtnActive : ''}`}
                  onClick={() => setRange(r)}
                >
                  {r}d
                </button>
              ))}
            </div>
          </div>

          <h1 className={styles.title}>Métricas personales</h1>
          <p className={styles.subtitle}>Evolución de tus indicadores de salud y recuperación</p>

          {/* Summary cards */}
          <div className={styles.statsGrid}>
            <StatCard
              label="Peso hoy"
              value={latest?.weight ?? null}
              unit="kg"
              color="#f59e0b"
              sub={`Media ${range}d: ${avg(weights) ?? '—'} kg`}
            />
            <StatCard
              label="FC reposo hoy"
              value={latest?.resting_hr ?? null}
              unit="ppm"
              color="#e05c5c"
              sub={`Media ${range}d: ${avg(hrs) ?? '—'} ppm`}
            />
            <StatCard
              label="HRV hoy"
              value={latest?.hrv ?? null}
              unit="ms"
              color="#22c55e"
              sub={`Media ${range}d: ${avg(hrvs) ?? '—'} ms`}
            />
            <StatCard
              label="Sueño hoy"
              value={latest?.sleep_hours ?? null}
              unit="h"
              color="#6366f1"
              sub={`Media ${range}d: ${avg(sleeps) ?? '—'} h`}
            />
          </div>

          {loading ? (
            <div className={styles.loading}>Cargando datos…</div>
          ) : (
            <div className={styles.chartsGrid}>
              <MetricChart
                data={data} dataKey="weight" color="#f59e0b"
                label="Peso" unit="kg"
              />
              <MetricChart
                data={data} dataKey="resting_hr" color="#e05c5c"
                label="FC reposo" unit="ppm"
              />
              <MetricChart
                data={data} dataKey="hrv" color="#22c55e"
                label="HRV" unit="ms"
              />
              <MetricChart
                data={data} dataKey="sleep_hours" color="#6366f1"
                label="Horas de sueño" unit="h"
                referenceValue={8}
              />
            </div>
          )}

        </div>
      </div>
    </ProtectedRoute>
  );
}
