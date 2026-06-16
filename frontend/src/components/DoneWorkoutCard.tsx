'use client';
import React, { useState } from 'react';
import Image from 'next/image';
import styles from '@/app/calendario/calendario.module.css';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import WorkoutAnalyzeModal from '@/components/WorkoutAnalyzeModal';
import type { Lap } from '@/types/training';

// ─── Sport classification ────────────────────────────────────────────────────

type SportKind = 'cycling' | 'running' | 'gym' | 'other';

const CYCLING_TYPES = ['Ride', 'VirtualRide', 'EBikeRide', 'eBikeRide', 'MountainBikeRide', 'GravelRide'];
const RUNNING_TYPES = ['Run', 'VirtualRun', 'TrailRun'];
const GYM_TYPES    = ['WeightTraining', 'Workout', 'Crossfit', 'Yoga', 'Pilates', 'Stretching', 'StairStepper', 'Elliptical'];

function getSportKind(type: string | null | undefined): SportKind {
  if (!type) return 'other';
  if (CYCLING_TYPES.includes(type)) return 'cycling';
  if (RUNNING_TYPES.includes(type)) return 'running';
  if (GYM_TYPES.includes(type))    return 'gym';
  return 'other';
}

// ─── Formatters ──────────────────────────────────────────────────────────────

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h${m}min`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatDuration(totalSec: number | null | undefined) {
  if (totalSec == null) return '—';
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  if (h > 0) return `${h}h ${m}min`;
  return `${m}min`;
}

function formatKm(distanceMeters: number | null | undefined, digits = 1) {
  if (distanceMeters == null || distanceMeters === 0) return '—';
  return `${(distanceMeters / 1000).toFixed(digits)} km`;
}

function formatBpm(bpm: number | null | undefined) {
  if (bpm == null) return '—';
  return `${Math.round(bpm)} ppm`;
}

function formatWatts(w: number | null | undefined) {
  if (w == null) return '—';
  return `${Math.round(w)} W`;
}

function formatElevation(m: number | null | undefined) {
  if (m == null || m === 0) return '—';
  return `${Math.round(m)} m`;
}

function formatSpeed(distanceMeters: number | null | undefined, durationSec: number | null | undefined) {
  if (!distanceMeters || !durationSec || durationSec === 0) return '—';
  const kmh = (distanceMeters / 1000) / (durationSec / 3600);
  return `${kmh.toFixed(1)} km/h`;
}

function formatPace(distanceMeters: number | null | undefined, durationSec: number | null | undefined) {
  if (!distanceMeters || !durationSec || distanceMeters === 0) return '—';
  const secPerKm = durationSec / (distanceMeters / 1000);
  const m = Math.floor(secPerKm / 60);
  const s = Math.round(secPerKm % 60);
  return `${m}:${s.toString().padStart(2, '0')} /km`;
}

function formatTSS(tss: number | null): string {
  return tss == null ? '—' : String(tss);
}

function calculateTSS(
  duration_sec: number | null | undefined,
  np: number | null | undefined,
  ftp: number | null | undefined,
): number | null {
  if (!duration_sec || !np || !ftp || ftp === 0) return null;
  const IF = np / ftp;
  return Math.round((duration_sec * np * IF) / (ftp * 3600) * 100);
}

// ─── Stream helpers ──────────────────────────────────────────────────────────

function smoothStream(
  stream: number[],
  timeStream: number[] | null | undefined,
  windowSec = 10,
): { time: number; watts: number }[] {
  const result: { time: number; watts: number }[] = [];
  for (let i = 0; i < stream.length; i += windowSec) {
    const slice = stream.slice(i, i + windowSec);
    const avg = slice.reduce((a, b) => a + b, 0) / slice.length;
    // Tiempo real del primer punto del bloque, o fallback a índice
    const t = timeStream?.[i] ?? i;
    result.push({ time: t, watts: Math.round(avg) });
  }
  return result;
}

function calculateXTicks(durationSec: number): number[] {
  const totalMinutes = durationSec / 60;
  let intervalMinutes: number;
  if (totalMinutes <= 15)       intervalMinutes = 5;
  else if (totalMinutes <= 30)  intervalMinutes = 10;
  else if (totalMinutes <= 60)  intervalMinutes = 15;
  else if (totalMinutes <= 120) intervalMinutes = 30;
  else                          intervalMinutes = 60;

  const ticks: number[] = [0];
  let current = intervalMinutes * 60;
  while (current < durationSec) { ticks.push(current); current += intervalMinutes * 60; }
  return ticks;
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function HrChart({ hrStream, timeStream, avgHr }: {
  hrStream: number[];
  timeStream: number[] | null | undefined;
  avgHr: number | null | undefined;
}) {
  const data = smoothStream(hrStream, timeStream).map(p => ({ time: p.time, bpm: p.watts }));
  const maxHr = hrStream.length > 0 ? Math.max(...hrStream) : null;
  const realDuration = timeStream?.length ? timeStream[timeStream.length - 1] : hrStream.length;
  return (
    <div className={styles.chartCard}>
      <div className={styles.chartHeader}>
        <h5 className={styles.chartTitle}>Frecuencia cardíaca</h5>
        <span className={styles.chartMeta}>
          FC media <strong>{formatBpm(avgHr)}</strong>
          {maxHr != null && <> · FC máx <strong>{formatBpm(maxHr)}</strong></>}
        </span>
      </div>
      {hrStream.length > 0 ? (
        <div className={styles.chartContainer}>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="hrGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity={0.8} />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="time" stroke="#999" tick={{ fontSize: 11 }}
                ticks={calculateXTicks(realDuration)} tickFormatter={(v) => formatTime(Number(v))} />
              <YAxis stroke="#999" tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
              <Tooltip contentStyle={{ background: '#fff', border: '1px solid #ddd', borderRadius: '8px' }}
                labelFormatter={(v) => formatTime(Number(v))}
                formatter={(value: number | undefined) => [`${value ?? 0} ppm`, 'FC']} />
              <Area type="monotone" dataKey="bpm" stroke="#dc2626" strokeWidth={2} fill="url(#hrGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className={styles.chartHint}>No hay datos de frecuencia cardíaca disponibles.</p>
      )}
    </div>
  );
}

function PowerChart({ powerStream, timeStream, np }: {
  powerStream: number[];
  timeStream: number[] | null | undefined;
  np: number | null | undefined;
}) {
  const data = smoothStream(powerStream, timeStream);
  const maxPower = powerStream.length > 0 ? Math.max(...powerStream) : null;
  const realDuration = timeStream?.length ? timeStream[timeStream.length - 1] : powerStream.length;
  return (
    <div className={styles.chartCard}>
      <div className={styles.chartHeader}>
        <h5 className={styles.chartTitle}>Potencia</h5>
        <span className={styles.chartMeta}>
          Pot. Norm. <strong>{formatWatts(np)}</strong>
          {maxPower != null && <> · Pot. máx <strong>{formatWatts(maxPower)}</strong></>}
        </span>
      </div>
      {powerStream.length > 0 ? (
        <div className={styles.chartContainer}>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="powerGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#a78bfa" stopOpacity={0.8} />
                  <stop offset="100%" stopColor="#a78bfa" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="time" stroke="#999" tick={{ fontSize: 11 }}
                ticks={calculateXTicks(realDuration)} tickFormatter={(v) => formatTime(Number(v))} />
              <YAxis stroke="#999" tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
              <Tooltip contentStyle={{ background: '#fff', border: '1px solid #ddd', borderRadius: '8px' }}
                labelFormatter={(v) => formatTime(Number(v))}
                formatter={(value: number | undefined) => [`${value ?? 0} W`, 'Potencia']} />
              <Area type="monotone" dataKey="watts" stroke="#8b5cf6" strokeWidth={2} fill="url(#powerGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className={styles.chartHint}>No hay datos de potencia disponibles.</p>
      )}
    </div>
  );
}

// ─── Laps table ───────────────────────────────────────────────────────────────

function LapsTable({ laps }: { laps: Lap[] }) {
  if (laps.length === 0) return null;

  const hasPower = laps.some(l => l.avg_watts != null);
  const hasHr    = laps.some(l => l.avg_hr != null);

  return (
    <div className={styles.chartCard}>
      <div className={styles.chartHeader}>
        <h5 className={styles.chartTitle}>Vueltas</h5>
        <span className={styles.chartMeta}>{laps.length} laps</span>
      </div>
      <div className={styles.lapsTableWrapper}>
        <table className={styles.lapsTable}>
          <thead>
            <tr>
              <th>#</th>
              <th>Tiempo</th>
              <th>Dist.</th>
              {hasPower && <th>Pot.</th>}
              {hasHr    && <th>FC</th>}
            </tr>
          </thead>
          <tbody>
            {laps.map((lap) => (
              <tr key={lap.index}>
                <td className={styles.lapsIndex}>{lap.index}</td>
                <td>{formatTime(lap.elapsed_time)}</td>
                <td>{formatKm(lap.distance)}</td>
                {hasPower && <td>{lap.avg_watts != null ? `${Math.round(lap.avg_watts)} W` : '—'}</td>}
                {hasHr    && <td>{lap.avg_hr != null ? `${Math.round(lap.avg_hr)} ppm` : '—'}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatItem({ value, label }: { value: string; label: string }) {
  return (
    <div className={styles.doneStatItem}>
      <span className={styles.doneStatValue}>{value}</span>
      <span className={styles.doneStatLabel}>{label}</span>
    </div>
  );
}

function Divider() {
  return <div className={styles.doneStatDivider} />;
}

// ─── Types ───────────────────────────────────────────────────────────────────

export type DoneTraining = {
  activity_id: number;
  name?: string | null;
  type?: string | null;
  duration?: number | null;
  distance?: number | null;
  weighted_average_watts?: number | null;
  avgheartrate?: number | null;
  altitude?: number | null;
  TSS?: number | null;
  power_stream?: number[] | null;
  hr_stream?: number[] | null;
  time_stream?: number[] | null;
  laps?: Lap[] | null;
};

// ─── Sport-specific layouts ───────────────────────────────────────────────────

function CyclingCard({ training, ftp }: { training: DoneTraining; ftp?: number | null }) {
  const tss = training.TSS ?? calculateTSS(training.duration, training.weighted_average_watts, ftp);
  const hasLaps = (training.laps?.length ?? 0) > 0;

  return (
    <>
      <div className={styles.doneStatsCard}>
        <StatItem value={formatDuration(training.duration)} label="Duración" />
        <Divider />
        <StatItem value={formatKm(training.distance)} label="Distancia" />
        <Divider />
        <StatItem value={formatSpeed(training.distance, training.duration)} label="Vel. Media" />
        <Divider />
        <StatItem value={formatElevation(training.altitude)} label="Desnivel" />
        {tss != null && (
          <>
            <Divider />
            <StatItem value={String(tss)} label="TSS" />
          </>
        )}
      </div>

      <PowerChart
        powerStream={training.power_stream ?? []}
        timeStream={training.time_stream}
        np={training.weighted_average_watts}
      />

      <HrChart
        hrStream={training.hr_stream ?? []}
        timeStream={training.time_stream}
        avgHr={training.avgheartrate}
      />

      {hasLaps && <LapsTable laps={training.laps!} />}
    </>
  );
}

function RunningCard({ training }: { training: DoneTraining }) {
  return (
    <>
      <div className={styles.doneStatsCard}>
        <StatItem value={formatDuration(training.duration)} label="Duración" />
        <Divider />
        <StatItem value={formatKm(training.distance)} label="Distancia" />
        <Divider />
        <StatItem value={formatPace(training.distance, training.duration)} label="Ritmo" />
        <Divider />
        <StatItem value={formatElevation(training.altitude)} label="Desnivel" />
      </div>

      <HrChart hrStream={training.hr_stream ?? []} avgHr={training.avgheartrate} />
    </>
  );
}

function GymCard({ training }: { training: DoneTraining }) {
  return (
    <>
      <div className={styles.doneStatsCard}>
        <StatItem value={formatDuration(training.duration)} label="Duración" />
        {training.avgheartrate != null && (
          <>
            <Divider />
            <StatItem value={formatBpm(training.avgheartrate)} label="FC Media" />
          </>
        )}
      </div>

      <HrChart hrStream={training.hr_stream ?? []} avgHr={training.avgheartrate} />
    </>
  );
}

function OtherCard({ training }: { training: DoneTraining }) {
  return (
    <div className={styles.doneStatsCard}>
      <StatItem value={formatDuration(training.duration)} label="Duración" />
      {(training.distance ?? 0) > 0 && (
        <>
          <Divider />
          <StatItem value={formatKm(training.distance)} label="Distancia" />
        </>
      )}
      {training.avgheartrate != null && (
        <>
          <Divider />
          <StatItem value={formatBpm(training.avgheartrate)} label="FC Media" />
        </>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function DoneWorkoutCard({
  training,
  className,
  ftp,
}: {
  training: DoneTraining;
  className?: string;
  ftp?: number | null;
}) {
  const kind = getSportKind(training.type);
  const [showAnalyze, setShowAnalyze] = useState(false);
  const hasPowerOrHr = (training.power_stream?.length ?? 0) > 0 || (training.hr_stream?.length ?? 0) > 0;

  return (
    <div className={`${styles.doneNew} ${className ?? ''}`}>
      {/* Header */}
      <div className={styles.doneNewHeader}>
        <h4 className={styles.doneNewTitle}>{training.name || 'Entreno'}</h4>
        {hasPowerOrHr && (
          <button
            className={styles.analyzeBtn}
            onClick={() => setShowAnalyze(true)}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            Analizar entreno
          </button>
        )}
      </div>

      {/* Sport-specific content */}
      {kind === 'cycling' && <CyclingCard training={training} ftp={ftp} />}
      {kind === 'running' && <RunningCard training={training} />}
      {kind === 'gym'     && <GymCard training={training} />}
      {kind === 'other'   && <OtherCard training={training} />}

      {/* Botón View on Strava — al final */}
      <div className={styles.doneStravaFooter}>
        <a
          href={`https://www.strava.com/activities/${training.activity_id}`}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.stravaButton}
          title="Ver en Strava"
        >
          <Image src="/view_on_strava_Button.png" alt="Ver en Strava" width={120} height={32} className={styles.stravaButtonImg} />
        </a>
      </div>

      {/* Modal de análisis */}
      {showAnalyze && (
        <WorkoutAnalyzeModal
          training={training}
          onClose={() => setShowAnalyze(false)}
        />
      )}
    </div>
  );
}
