'use client';
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { supabase } from '@/lib/supabaseClient';
import { useUser } from '@/context/userContext';
import styles from './trendings.module.css';

type DayPoint = {
  date: string;   // YYYY-MM-DD
  label: string;  // DD/MM
  tss: number;
  ctl: number;
  atl: number;
  tsb: number;
};

// Colores TrainingPeaks
const TP_CTL = '#4a90d9';  // azul
const TP_ATL = '#e05c5c';  // rojo/rosa
const TP_TSB = '#5cb85c';  // verde

function interpretTSB(tsb: number): { label: string; color: string; desc: string } {
  if (tsb > 25)  return { label: 'Muy descansado', color: '#6366f1', desc: 'Riesgo de desentrenamiento. Buen momento para una carrera importante.' };
  if (tsb > 5)   return { label: 'Descansado', color: TP_TSB, desc: 'Forma óptima. Ideal para competir o hacer un test de FTP.' };
  if (tsb > -10) return { label: 'En forma', color: TP_TSB, desc: 'Balance equilibrado. Puedes entrenar con normalidad.' };
  if (tsb > -25) return { label: 'Fatigado', color: TP_ATL, desc: 'Acumulando carga. Considera reducir intensidad.' };
  return           { label: 'Muy fatigado', color: '#c0392b', desc: 'Fatiga elevada. Prioriza recuperación.' };
}

function interpretCTL(ctl: number): string {
  if (ctl < 20)  return 'Nivel principiante';
  if (ctl < 40)  return 'Nivel recreativo';
  if (ctl < 60)  return 'Nivel amateur';
  if (ctl < 80)  return 'Nivel avanzado';
  if (ctl < 100) return 'Nivel competitivo';
  return           'Nivel élite';
}

function SummaryPanel({ latest }: { latest: DayPoint }) {
  const tsb = interpretTSB(latest.tsb);
  return (
    <div className={styles.summaryPanel}>
      <div className={styles.summaryMetrics}>
        <div className={styles.summaryMetric}>
          <span className={styles.summaryValue} style={{ color: TP_CTL }}>{latest.ctl}</span>
          <span className={styles.summaryKey}>CTL</span>
          <span className={styles.summaryHint}>{interpretCTL(latest.ctl)}</span>
        </div>
        <div className={styles.summaryDivider} />
        <div className={styles.summaryMetric}>
          <span className={styles.summaryValue} style={{ color: TP_ATL }}>{latest.atl}</span>
          <span className={styles.summaryKey}>ATL</span>
          <span className={styles.summaryHint}>Fatiga reciente</span>
        </div>
        <div className={styles.summaryDivider} />
        <div className={styles.summaryMetric}>
          <span className={styles.summaryValue} style={{ color: TP_TSB }}>{latest.tsb > 0 ? '+' : ''}{latest.tsb}</span>
          <span className={styles.summaryKey}>TSB</span>
          <span className={styles.summaryHint}>{tsb.label}</span>
        </div>
      </div>
      <p className={styles.summaryDesc}>{tsb.desc}</p>
    </div>
  );
}

function buildSeries(rows: { date: string; TSS: number | null }[]): DayPoint[] {
  // Construir mapa de TSS por fecha
  const tssMap: Record<string, number> = {};
  for (const r of rows) {
    if (r.date && r.TSS != null) {
      tssMap[r.date] = Number(r.TSS);
    }
  }

  // Generar los últimos 180 días
  const today = new Date();
  const days: DayPoint[] = [];
  let ctl = 0;
  let atl = 0;

  for (let i = 179; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const iso = d.toISOString().slice(0, 10);
    const label = `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
    const tss = tssMap[iso] ?? 0;

    ctl = ctl + (tss - ctl) / 42;
    atl = atl + (tss - atl) / 7;
    const tsb = ctl - atl;

    days.push({
      date: iso,
      label,
      tss: Math.round(tss),
      ctl: Math.round(ctl * 10) / 10,
      atl: Math.round(atl * 10) / 10,
      tsb: Math.round(tsb * 10) / 10,
    });
  }

  return days;
}

function ChartCard({
  title,
  subtitle,
  accentColor,
  children,
}: {
  title: string;
  subtitle: string;
  accentColor: string;
  children: React.ReactNode;
}) {
  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <div className={styles.cardTitleRow}>
          <span className={styles.cardDot} style={{ background: accentColor }} />
          <h2 className={styles.cardTitle}>{title}</h2>
        </div>
        <p className={styles.cardSubtitle}>{subtitle}</p>
      </div>
      <div className={styles.chartWrap}>{children}</div>
    </div>
  );
}

function TrendingsContent() {
  const user = useUser()?.user;
  const router = useRouter();
  const [data, setData] = useState<DayPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  const loadData = async (userId: string) => {
    setLoading(true);

    // Leer los últimos 180 días de métricas ya calculadas
    const since = new Date();
    since.setDate(since.getDate() - 180);
    const sinceStr = since.toISOString().slice(0, 10);

    const { data: rows, error } = await supabase
      .from('daily_metrics')
      .select('date, ctl, atl, tsb, tss')
      .eq('user_id', userId)
      .gte('date', sinceStr)
      .order('date', { ascending: true });

    console.log('[Trendings] daily_metrics rows:', rows?.length, 'error:', error);
    if (rows?.length) {
      console.log('[Trendings] first row:', rows[0]);
      console.log('[Trendings] last row:', rows[rows.length - 1]);
    }

    if (rows && rows.length > 0) {
      setData(rows.map(r => ({
        date: r.date,
        label: `${r.date.slice(8, 10)}/${r.date.slice(5, 7)}`,
        tss: Number(r.tss ?? 0),
        ctl: Number(r.ctl ?? 0),
        atl: Number(r.atl ?? 0),
        tsb: Number(r.tsb ?? 0),
      })));
    } else {
      // Fallback: calcular en cliente si no hay datos en daily_metrics
      const fallbackSince = new Date();
      fallbackSince.setDate(fallbackSince.getDate() - 365);
      const { data: tssRows } = await supabase
        .from('trainings')
        .select('date, TSS')
        .eq('user_id', userId)
        .gte('date', fallbackSince.toISOString().slice(0, 10))
        .order('date', { ascending: true });
      setData(buildSeries(tssRows ?? []));
    }

    setLoading(false);
  };

  useEffect(() => {
    if (!user?.id) return;
    loadData(user.id);
  }, [user?.id]);

  const handleSync = async () => {
    if (!user?.id || syncing) return;
    setSyncing(true);
    setSyncMsg(null);

    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 180);

    const startStr = start.toISOString().slice(0, 10);
    const endStr = end.toISOString().slice(0, 10);

    try {
      const res = await fetch('/api/strava/sync-trainings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: user.id, startDate: startStr, endDate: endStr }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error ?? 'Error sincronizando');
      setSyncMsg(`✓ ${json.insertedOrUpdated} actividades sincronizadas`);
      await loadData(user.id);
    } catch (e) {
      setSyncMsg(`Error: ${(e as Error).message}`);
    } finally {
      setSyncing(false);
    }
  };

  // Mostrar solo los últimos 180 días en las gráficas
  const chartData = data.slice(-180);

  // Tick cada ~30 días
  const tickInterval = Math.floor(chartData.length / 6);

  if (loading) {
    return <div className={styles.loading}>Cargando datos…</div>;
  }

  const latest = chartData[chartData.length - 1];

  return (
    <>
      <div className={styles.topNav}>
        <button className={styles.backBtn} onClick={() => router.back()}>← Volver</button>
        <div className={styles.syncRow}>
          <button
            type="button"
            className={styles.syncBtn}
            onClick={handleSync}
            disabled={syncing}
          >
            {syncing ? 'Sincronizando…' : 'Sincronizar últimos 180 días'}
          </button>
          {syncMsg && <span className={styles.syncMsg}>{syncMsg}</span>}
        </div>
      </div>

      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Tendencias</h1>
          <p className={styles.pageSubtitle}>Evolución de tu carga de entrenamiento — últimos 180 días</p>
        </div>
        {latest && <SummaryPanel latest={latest} />}
      </div>
      {/* CTL */}
      <ChartCard
        title="CTL — Fitness crónico"
        subtitle="Carga acumulada a largo plazo (42 días). Refleja tu forma física base."
        accentColor={TP_CTL}
      >
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="ctlGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={TP_CTL} stopOpacity={0.35} />
                <stop offset="100%" stopColor={TP_CTL} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(15,15,20,0.06)" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="rgba(15,15,20,0.3)" interval={tickInterval} />
            <YAxis tick={{ fontSize: 11 }} stroke="rgba(15,15,20,0.3)" width={36} />
            <Tooltip
              contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: 13 }}
              formatter={(v) => [`${v}`, 'CTL']}
              labelFormatter={(l) => `Fecha: ${l}`}
            />
            <Area type="monotone" dataKey="ctl" stroke={TP_CTL} strokeWidth={2} fill="url(#ctlGrad)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* ATL */}
      <ChartCard
        title="ATL — Fatiga aguda"
        subtitle="Carga reciente (7 días). Indica tu nivel de fatiga actual."
        accentColor={TP_ATL}
      >
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="atlGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={TP_ATL} stopOpacity={0.35} />
                <stop offset="100%" stopColor={TP_ATL} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(15,15,20,0.06)" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="rgba(15,15,20,0.3)" interval={tickInterval} />
            <YAxis tick={{ fontSize: 11 }} stroke="rgba(15,15,20,0.3)" width={36} />
            <Tooltip
              contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: 13 }}
              formatter={(v) => [`${v}`, 'ATL']}
              labelFormatter={(l) => `Fecha: ${l}`}
            />
            <Area type="monotone" dataKey="atl" stroke={TP_ATL} strokeWidth={2} fill="url(#atlGrad)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* TSB */}
      <ChartCard
        title="TSB — Forma del día"
        subtitle="Balance entre fitness y fatiga (CTL − ATL). Positivo = descansado, negativo = fatigado."
        accentColor={TP_TSB}
      >
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="tsbGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={TP_TSB} stopOpacity={0.35} />
                <stop offset="100%" stopColor={TP_TSB} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(15,15,20,0.06)" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="rgba(15,15,20,0.3)" interval={tickInterval} />
            <YAxis tick={{ fontSize: 11 }} stroke="rgba(15,15,20,0.3)" width={36} />
            <ReferenceLine y={0} stroke="rgba(15,15,20,0.25)" strokeDasharray="4 4" />
            <Tooltip
              contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: 13 }}
              formatter={(v) => [`${v}`, 'TSB']}
              labelFormatter={(l) => `Fecha: ${l}`}
            />
            <Area type="monotone" dataKey="tsb" stroke={TP_TSB} strokeWidth={2} fill="url(#tsbGrad)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>
    </>
  );
}

export default function TrendingsPage() {
  return (
    <ProtectedRoute>
      <div className={styles.page}>
        <div className={styles.container}>
          <TrendingsContent />
        </div>
      </div>
    </ProtectedRoute>
  );
}
