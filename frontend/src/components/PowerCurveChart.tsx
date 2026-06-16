'use client';
import React, { useEffect, useMemo, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { supabase } from '@/lib/supabaseClient';
import type { MmpCurve } from '@/hooks/useDashboardData';
import styles from '@/app/dashboard/dashboard.module.css';

// ─── Períodos predefinidos ────────────────────────────────────────────────────

type PeriodKey = '1w' | '2w' | '1m' | '3m' | '6m' | '1y' | 'custom';

const PERIODS: { key: PeriodKey; label: string; days?: number }[] = [
  { key: '1w',  label: 'Última semana',    days: 7   },
  { key: '2w',  label: 'Últimas 2 semanas', days: 14  },
  { key: '1m',  label: 'Último mes',        days: 30  },
  { key: '3m',  label: 'Último trimestre',  days: 90  },
  { key: '6m',  label: 'Últimos 6 meses',   days: 180 },
  { key: '1y',  label: 'Último año',        days: 365 },
  { key: 'custom', label: 'Personalizado'             },
];

// ─── MMP durations ────────────────────────────────────────────────────────────

const MMP_DURATIONS = [1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600];
const MMP_LABELS: Record<number, string> = {
  1: '1s', 5: '5s', 10: '10s', 30: '30s',
  60: '1min', 120: '2min', 300: '5min', 600: '10min',
  1200: '20min', 1800: '30min', 3600: '60min',
};

function isoDate(d: Date) {
  return d.toISOString().slice(0, 10);
}

function daysAgo(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return isoDate(d);
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function PowerCurveChart({
  userId,
  bestMmp,
}: {
  userId: string | undefined;
  bestMmp: MmpCurve | null;
}) {
  const [period, setPeriod] = useState<PeriodKey>('1m');
  const [customFrom, setCustomFrom] = useState(() => daysAgo(30));
  const [customTo, setCustomTo] = useState(() => isoDate(new Date()));
  const [showCustom, setShowCustom] = useState(false);
  const [periodMmp, setPeriodMmp] = useState<MmpCurve | null>(null);
  const [loading, setLoading] = useState(false);

  // Calcular rango de fechas activo
  const { fromDate, toDate } = useMemo(() => {
    if (period === 'custom') return { fromDate: customFrom, toDate: customTo };
    const p = PERIODS.find(p => p.key === period);
    return {
      fromDate: daysAgo(p?.days ?? 30),
      toDate: isoDate(new Date()),
    };
  }, [period, customFrom, customTo]);

  // Fetch MMP del período seleccionado
  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    setLoading(true);

    supabase
      .from('trainings')
      .select('mmp_curve')
      .eq('user_id', userId)
      .gte('date', fromDate)
      .lte('date', toDate)
      .not('mmp_curve', 'is', null)
      .then(({ data }) => {
        if (cancelled) return;
        if (!data || data.length === 0) { setPeriodMmp(null); setLoading(false); return; }
        const merged: MmpCurve = {};
        for (const row of data) {
          const curve = row.mmp_curve as MmpCurve | null;
          if (!curve) continue;
          for (const [dur, watts] of Object.entries(curve)) {
            if (!merged[dur] || watts > merged[dur]) merged[dur] = watts;
          }
        }
        setPeriodMmp(Object.keys(merged).length > 0 ? merged : null);
        setLoading(false);
      });

    return () => { cancelled = true; };
  }, [userId, fromDate, toDate]);

  // Datos para la gráfica
  const chartData = useMemo(() =>
    MMP_DURATIONS.map(dur => ({
      label: MMP_LABELS[dur],
      alltime: bestMmp?.[String(dur)] ?? null,
      period: periodMmp?.[String(dur)] ?? null,
    })).filter(d => d.alltime !== null || d.period !== null),
  [bestMmp, periodMmp]);

  const selectedPeriod = PERIODS.find(p => p.key === period);

  if (!bestMmp && !periodMmp && !loading) return null;

  return (
    <section className={styles.mmpCard}>
      <div className={styles.mmpHeader}>
        <div className={styles.cardTitle} style={{ margin: 0 }}>Curva de potencia</div>

        <div className={styles.mmpControls}>
          <select
            className={styles.mmpSelect}
            value={period}
            onChange={e => {
              const val = e.target.value as PeriodKey;
              setPeriod(val);
              setShowCustom(val === 'custom');
            }}
          >
            {PERIODS.map(p => (
              <option key={p.key} value={p.key}>{p.label}</option>
            ))}
          </select>

          {showCustom && (
            <div className={styles.mmpCustomRange}>
              <input
                type="date"
                value={customFrom}
                max={customTo}
                onChange={e => setCustomFrom(e.target.value)}
                className={styles.mmpDateInput}
              />
              <span className={styles.mmpDateSep}>→</span>
              <input
                type="date"
                value={customTo}
                min={customFrom}
                max={isoDate(new Date())}
                onChange={e => setCustomTo(e.target.value)}
                className={styles.mmpDateInput}
              />
            </div>
          )}
        </div>
      </div>

      <div className={styles.mmpInner}>
        {loading ? (
          <div className={styles.mmpLoading}>Cargando…</div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                stroke="rgba(0,0,0,0.25)"
                axisLine={false}
                tickLine={false}
                interval={0}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                stroke="rgba(0,0,0,0.25)"
                axisLine={false}
                tickLine={false}
                unit=" W"
                width={52}
              />
              <Tooltip
                contentStyle={{ borderRadius: 8, fontSize: 12 }}
                formatter={(v: number | undefined, name: string | undefined) =>
                  [`${v ?? '—'} W`, name === 'alltime' ? 'Histórico' : selectedPeriod?.label ?? 'Período'] as [string, string]
                }
              />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: 12 }}
                formatter={v => v === 'alltime' ? 'Histórico' : selectedPeriod?.label ?? 'Período'}
              />
              <Line type="monotone" dataKey="alltime" stroke="#6366f1" strokeWidth={2.5} dot={{ r: 4, fill: '#6366f1' }} connectNulls />
              <Line type="monotone" dataKey="period" stroke="#FC4C02" strokeWidth={2} strokeDasharray="5 3" dot={{ r: 3, fill: '#FC4C02' }} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
