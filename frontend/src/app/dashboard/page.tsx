'use client';
import React, { useState } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import Link from 'next/link';
import {
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';
import styles from './dashboard.module.css';
import { useUser } from '@/context/userContext';
import { useDashboardData } from '@/hooks/useDashboardData';
import PowerCurveChart from '@/components/PowerCurveChart';

const ZONE_COLORS = ['#4a90d9', '#5cb85c', '#2ecc71', '#f0ad4e', '#e67e22', '#e05c5c', '#c0392b'];
const ZONE_COLORS_HR = ['#4a90d9', '#5cb85c', '#2ecc71', '#f0ad4e', '#e67e22'];

function ZoneBar({ zone, hours, pct, color }: { zone: string; hours: string; pct: number; color: string }) {
  return (
    <div className={styles.zoneRow}>
      <span className={styles.zoneLabel} style={{ color }}>{zone}</span>
      <div className={styles.zoneTrack}>
        <div className={styles.zoneFill} style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className={styles.zoneHours}>{hours}</span>
    </div>
  );
}

function CustomDot(props: { cx?: number; cy?: number; index?: number; dataLength?: number }) {
  const { cx, cy, index, dataLength } = props;
  if (cx == null || cy == null) return null;
  const isLast = index === (dataLength ?? 0) - 1;
  return (
    <circle cx={cx} cy={cy} r={isLast ? 7 : 4}
      fill="#FC4C02" stroke="#fff" strokeWidth={isLast ? 2 : 1.5} />
  );
}

export default function DashboardPage() {
  const user = useUser()?.user;
  const { currentWeek, last9Weeks, today, yesterday, profile, trendData, loading: loadingWeek } = useDashboardData(user?.id);

  const arrow = (current: number | null, prev: number | null) => {
    if (current == null || prev == null) return null;
    return current >= prev ? '↑' : '↓';
  };
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  const handleSync = async () => {
    if (!user?.id || syncing) return;
    setSyncing(true);
    setSyncMsg(null);
    try {
      const res = await fetch('/api/strava/sync-trainings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: user.id, lookbackDays: 30 }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error ?? 'Error sincronizando');
      setSyncMsg(`✓ ${json.insertedOrUpdated} actividades`);
    } catch (e) {
      setSyncMsg(`Error: ${(e as Error).message}`);
    } finally {
      setSyncing(false);
    }
  };

  // W/kg calculado en cliente
  const wPerKg = (profile.ftp && profile.weight && profile.weight > 0)
    ? Math.round((profile.ftp / profile.weight) * 10) / 10
    : null;

  // Interpretación TSB
  const tsbLabel = (tsb: number | null) => {
    if (tsb == null) return '—';
    if (tsb > 25) return 'Muy descansado';
    if (tsb > 5)  return 'Descansado';
    if (tsb > -10) return 'En forma';
    if (tsb > -25) return 'Fatigado';
    return 'Muy fatigado';
  };

  const ctlLabel = (ctl: number | null) => {
    if (ctl == null) return '—';
    if (ctl < 20) return 'Principiante';
    if (ctl < 40) return 'Recreativo';
    if (ctl < 60) return 'Amateur';
    if (ctl < 80) return 'Avanzado';
    if (ctl < 100) return 'Competitivo';
    return 'Élite';
  };

  // Formatear horas y minutos
  const totalHours = currentWeek ? Math.floor(currentWeek.completed_hours) : 0;
  const totalMins = currentWeek ? Math.round((currentWeek.completed_hours - totalHours) * 60) : 0;

  // Zonas reales de la semana actual
  const ZONE_LABELS_POWER = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7'];
  const ZONE_LABELS_HR    = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5'];

  const powerZones = ZONE_LABELS_POWER.map((label, i) => {
    const key = `z${i + 1}`;
    const mins = currentWeek?.power_zones_minutes?.[key] ?? 0;
    const h = Math.floor(mins / 60);
    const m = Math.round(mins % 60);
    const hours = h > 0 ? `${h}h ${m}m` : `${m}m`;
    const maxMins = Math.max(...ZONE_LABELS_POWER.map((_, j) => currentWeek?.power_zones_minutes?.[`z${j + 1}`] ?? 0), 1);
    return { zone: label, hours, pct: Math.round((mins / maxMins) * 100) };
  });

  const hrZones = ZONE_LABELS_HR.map((label, i) => {
    const key = `z${i + 1}`;
    const mins = currentWeek?.hr_zones_minutes?.[key] ?? 0;
    const h = Math.floor(mins / 60);
    const m = Math.round(mins % 60);
    const hours = h > 0 ? `${h}h ${m}m` : `${m}m`;
    const maxMins = Math.max(...ZONE_LABELS_HR.map((_, j) => currentWeek?.hr_zones_minutes?.[`z${j + 1}`] ?? 0), 1);
    return { zone: label, hours, pct: Math.round((mins / maxMins) * 100) };
  });
  const weeklyKmChart = last9Weeks.map((w) => {
    const parts = w.week_start_date.split('-');
    return { week: `${parts[2]}/${parts[1]}`, km: Math.round(w.completed_distance_km) };
  });
  const maxKm = weeklyKmChart.length > 0 ? Math.max(...weeklyKmChart.map(w => w.km)) : 100;

  // Curva de potencia — delegada al componente PowerCurveChart

  return (
    <ProtectedRoute>
      <div className={styles.page}>
        <div className={styles.container}>
          <div className={styles.dashboardHeader}>
            <h1 className={styles.pageTitle}>Dashboard</h1>
            <div className={styles.dashboardHeaderRight}>
              <button
                type="button"
                className={styles.stravaSync}
                onClick={handleSync}
                disabled={syncing}
              >
                {syncing ? 'Sincronizando…' : 'Sincronizar entrenos'}
              </button>
              {syncMsg && <span className={styles.syncMsg}>{syncMsg}</span>}
            </div>
          </div>

          {/* BLOQUE 1: Estado actual */}
          <div className={styles.topRow}>
            {/* Card atleta */}
            <Link href="/metricas" className={styles.athleteCard} style={{ textDecoration: 'none', display: 'block', cursor: 'pointer' }}>
              <div className={styles.cardTitle}>Estado del atleta</div>
              <div className={styles.athleteContent}>
                <div className={styles.athleteRow}>
                  <div className={styles.athleteMetric}>
                    <span className={styles.athleteValue} style={{ color: '#f59e0b' }}>
                      {today.weight ?? profile.weight ?? '—'}
                      <span className={styles.athleteUnit}>kg</span>
                    </span>
                    <span className={styles.athleteLabel}>Peso · hoy</span>
                  </div>
                  <div className={styles.athleteDivider} />
                  <div className={styles.athleteMetric}>
                    <span className={styles.athleteValue} style={{ color: '#6366f1' }}>
                      {today.sleep_hours != null ? today.sleep_hours : '—'}
                      <span className={styles.athleteUnit}>{today.sleep_hours != null ? 'h' : ''}</span>
                    </span>
                    <span className={styles.athleteLabel}>Sueño · hoy</span>
                  </div>
                  <div className={styles.athleteDivider} />
                  <div className={styles.athleteMetric}>
                    <span className={styles.athleteValue} style={{ color: '#6366f1' }}>{wPerKg ?? '—'}<span className={styles.athleteUnit}>w/kg</span></span>
                    <span className={styles.athleteLabel}>W/kg</span>
                  </div>
                </div>
                <div className={styles.athleteRowBottom}>
                  <div className={styles.athleteMetricSm}>
                    <span className={styles.athleteValueSm} style={{ color: '#e05c5c' }}>{today.resting_hr ?? '—'}<span className={styles.athleteUnitSm}>{today.resting_hr ? 'bpm' : ''}</span></span>
                    <span className={styles.athleteLabelSm}>FC reposo · hoy</span>
                  </div>
                  <div className={styles.athleteDividerSm} />
                  <div className={styles.athleteMetricSm}>
                    <span className={styles.athleteValueSm} style={{ color: '#5cb85c' }}>{today.hrv ?? '—'}<span className={styles.athleteUnitSm}>{today.hrv ? 'ms' : ''}</span></span>
                    <span className={styles.athleteLabelSm}>HRV · hoy</span>
                  </div>
                </div>
              </div>
            </Link>

            {/* Card CTL/ATL/TSB */}
            <div className={styles.ctlCard}>
              <div className={styles.cardTitle}>Carga de entrenamiento</div>
              <div className={styles.ctlRow}>
                  <div className={styles.ctlMetric}>
                    <div className={styles.ctlValueRow}>
                      <span className={styles.ctlValue} style={{ color: '#4a90d9' }}>{today.ctl != null ? today.ctl.toFixed(1) : '—'}</span>
                      {arrow(today.ctl, yesterday.ctl) && <span style={{ color: '#4a90d9', fontSize: '1rem', marginLeft: 4 }}>{arrow(today.ctl, yesterday.ctl)}</span>}
                    </div>
                    <span className={styles.ctlKey}>CTL</span>
                    <span className={styles.ctlHint}>{ctlLabel(today.ctl)}</span>
                  </div>
                  <div className={styles.ctlDivider} />
                  <div className={styles.ctlMetric}>
                    <div className={styles.ctlValueRow}>
                      <span className={styles.ctlValue} style={{ color: '#e05c5c' }}>{today.atl != null ? today.atl.toFixed(1) : '—'}</span>
                      {arrow(today.atl, yesterday.atl) && <span style={{ color: '#e05c5c', fontSize: '1rem', marginLeft: 4 }}>{arrow(today.atl, yesterday.atl)}</span>}
                    </div>
                    <span className={styles.ctlKey}>ATL</span>
                    <span className={styles.ctlHint}>Fatiga reciente</span>
                  </div>
                  <div className={styles.ctlDivider} />
                  <div className={styles.ctlMetric}>
                    <div className={styles.ctlValueRow}>
                      <span className={styles.ctlValue} style={{ color: '#5cb85c' }}>{today.tsb != null ? (today.tsb > 0 ? '+' : '') + today.tsb.toFixed(1) : '—'}</span>
                      {arrow(today.tsb, yesterday.tsb) && <span style={{ color: '#5cb85c', fontSize: '1rem', marginLeft: 4 }}>{arrow(today.tsb, yesterday.tsb)}</span>}
                    </div>
                    <span className={styles.ctlKey}>TSB</span>
                    <span className={styles.ctlHint}>{tsbLabel(today.tsb)}</span>
                  </div>
                </div>
                <div className={styles.ctlDesc}>{today.tsb != null ? (today.tsb > 5 ? 'Forma óptima. Ideal para competir.' : today.tsb > -10 ? 'Balance equilibrado. Puedes entrenar con normalidad.' : 'Acumulando carga. Considera reducir intensidad.') : 'Sin datos de hoy'}</div>
            </div>
          </div>

          {/* BLOQUE 2: Progreso semanal */}
          <div className={styles.topRow}>
            {/* Card km + horas + TSS */}
            <div className={styles.weekSummaryCard}>
              <div className={styles.cardTitle}>Esta semana</div>
              <div className={styles.weekSummaryRow}>
                  <div className={styles.weekStat}>
                    <span className={styles.weekStatValue}>{loadingWeek ? '—' : Math.round(currentWeek?.completed_distance_km ?? 0)}</span>
                    <span className={styles.weekStatUnit}>km</span>
                  </div>
                  <div className={styles.weekDivider} />
                  <div className={styles.weekStat}>
                    <span className={styles.weekStatValue}>{loadingWeek ? '—' : `${totalHours}h`}</span>
                    <span className={styles.weekStatUnit}>{loadingWeek ? '' : `${totalMins}m`}</span>
                  </div>
                  <div className={styles.weekDivider} />
                  <div className={styles.weekStat}>
                    <span className={styles.weekStatValue}>{loadingWeek ? '—' : Math.round(currentWeek?.completed_tss ?? 0)}</span>
                    <span className={styles.weekStatLabel}>Total TSS</span>
                  </div>
                </div>
            </div>

            {/* Card gráfico km semanales */}
            <div className={styles.weekChartCard}>
              <div className={styles.cardTitle}>Distancia semanal</div>
              <ResponsiveContainer width="100%" height={110}>
                  <AreaChart data={weeklyKmChart} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
                    <defs>
                      <linearGradient id="kmGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#FC4C02" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#FC4C02" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
                    <XAxis dataKey="week" tick={{ fontSize: 10 }} stroke="rgba(0,0,0,0.25)" axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10 }} stroke="rgba(0,0,0,0.25)" axisLine={false} tickLine={false} unit=" km" domain={[0, maxKm]} />
                    <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} formatter={(v) => [`${v} km`, 'Distancia']} />
                    <Area
                      type="monotone" dataKey="km" stroke="#FC4C02" strokeWidth={2.5}
                      fill="url(#kmGrad)"
                      dot={(props) => <CustomDot {...props} dataLength={weeklyKmChart.length} />}
                      activeDot={{ r: 6, fill: '#FC4C02' }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
            </div>
          </div>

          {/* BLOQUE 3 + 4: Distribución y Tendencia */}
          <div className={styles.bottomGrid}>
            <section className={styles.zonesCard}>
              <div className={styles.cardTitle}>Distribución de zonas</div>
              <div className={styles.zonesGrid}>
                <div>
                  <h3 className={styles.zonesSubtitle}>Potencia</h3>
                  {powerZones.map((z, i) => <ZoneBar key={z.zone} {...z} color={ZONE_COLORS[i]} />)}
                </div>
                <div>
                  <h3 className={styles.zonesSubtitle}>Frecuencia cardíaca</h3>
                  {hrZones.map((z, i) => <ZoneBar key={z.zone} {...z} color={ZONE_COLORS_HR[i]} />)}
                </div>
              </div>
            </section>

            <Link href="/trendings" className={styles.trendCard} style={{ textDecoration: 'none', display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div className={styles.cardTitle} style={{ margin: 0 }}>Tendencia de carga</div>
                <span style={{ fontSize: 12, color: '#4a90d9', fontWeight: 600 }}>Ver detalle →</span>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="gCTL" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#4a90d9" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#4a90d9" stopOpacity={0.02} />
                    </linearGradient>
                    <linearGradient id="gATL" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#e05c5c" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#e05c5c" stopOpacity={0.02} />
                    </linearGradient>
                    <linearGradient id="gTSB" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#5cb85c" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#5cb85c" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="rgba(0,0,0,0.3)" interval={Math.floor(trendData.length / 6)} />
                  <YAxis tick={{ fontSize: 11 }} stroke="rgba(0,0,0,0.3)" width={30} />
                  <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }}
                    formatter={(v) => v === 'ctl' ? 'CTL — Fitness crónico' : v === 'atl' ? 'ATL — Fatiga aguda' : 'TSB — Balance de carga'} />
                  <Area type="monotone" dataKey="ctl" stroke="#4a90d9" strokeWidth={2} fill="url(#gCTL)" dot={false} />
                  <Area type="monotone" dataKey="atl" stroke="#e05c5c" strokeWidth={2} fill="url(#gATL)" dot={false} />
                  <Area type="monotone" dataKey="tsb" stroke="#5cb85c" strokeWidth={2} fill="url(#gTSB)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </Link>
          </div>

          {/* BLOQUE 5: Curva de potencia */}
          <PowerCurveChart userId={user?.id} bestMmp={profile.best_mmp_curve} />

        </div>
      </div>
    </ProtectedRoute>
  );
}
