'use client';
import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceArea,
} from 'recharts';
import type { DoneTraining } from '@/components/DoneWorkoutCard';
import type { Lap } from '@/types/training';
import styles from './WorkoutAnalyzeModal.module.css';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

const SMOOTH = 10;

function buildChartData(
  powerStream: number[] | null | undefined,
  hrStream: number[] | null | undefined,
  timeStream: number[] | null | undefined,
): { time: number; watts: number | null; bpm: number | null }[] {
  const len = Math.max(powerStream?.length ?? 0, hrStream?.length ?? 0);
  if (len === 0) return [];
  const getTime = (i: number) => timeStream?.[i] ?? i;
  const result: { time: number; watts: number | null; bpm: number | null }[] = [];
  for (let i = 0; i < len; i += SMOOTH) {
    const pSlice = powerStream?.slice(i, i + SMOOTH) ?? [];
    const hSlice = hrStream?.slice(i, i + SMOOTH) ?? [];
    result.push({
      time: getTime(i),
      watts: pSlice.length > 0 ? Math.round(pSlice.reduce((a, b) => a + b, 0) / pSlice.length) : null,
      bpm:   hSlice.length > 0 ? Math.round(hSlice.reduce((a, b) => a + b, 0) / hSlice.length) : null,
    });
  }
  return result;
}

function calculateXTicks(dataLength: number): number[] {
  const totalMinutes = dataLength / 60;
  let intervalMinutes: number;
  if (totalMinutes <= 15)       intervalMinutes = 5;
  else if (totalMinutes <= 30)  intervalMinutes = 10;
  else if (totalMinutes <= 60)  intervalMinutes = 15;
  else if (totalMinutes <= 120) intervalMinutes = 30;
  else                          intervalMinutes = 60;
  const ticks: number[] = [0];
  let current = intervalMinutes * 60;
  while (current < dataLength) { ticks.push(current); current += intervalMinutes * 60; }
  return ticks;
}

function streamAvg(
  stream: number[] | null | undefined,
  timeStream: number[] | null | undefined,
  fromSec: number,
  toSec: number,
): number | null {
  if (!stream || stream.length === 0) return null;
  const s = Math.min(fromSec, toSec);
  const e = Math.max(fromSec, toSec);
  let slice: number[];
  if (timeStream && timeStream.length === stream.length) {
    slice = stream.filter((_, i) => timeStream[i] >= s && timeStream[i] <= e && stream[i] > 0);
  } else {
    slice = stream.slice(s, e + 1).filter(v => v != null && v > 0);
  }
  if (slice.length === 0) return null;
  return Math.round(slice.reduce((a, b) => a + b, 0) / slice.length);
}

type LapRange = { lap: Lap; start: number; end: number };

function buildLapRanges(laps: Lap[]): LapRange[] {
  const ranges: LapRange[] = [];
  let cursor = 0;
  for (const lap of laps) {
    ranges.push({ lap, start: cursor, end: cursor + lap.elapsed_time });
    cursor += lap.elapsed_time;
  }
  return ranges;
}

// ─── Lap overlay (CSS, no SVG internals) ─────────────────────────────────────
// Los márgenes del ComposedChart: left=8+56=64, right=24+60=84 (aprox)
// Los pasamos como props para que el overlay se alinee con el área del plot.
const CHART_MARGIN = { top: 12, right: 84, bottom: 28, left: 64 };

function LapOverlay({
  lapRanges,
  totalDuration,
}: {
  lapRanges: LapRange[];
  hoveredLapIndex: number | null;
  totalDuration: number;
}) {
  if (!lapRanges.length || totalDuration <= 0) return null;

  return (
    <div style={{
      position: 'absolute',
      top: CHART_MARGIN.top,
      bottom: CHART_MARGIN.bottom,
      left: CHART_MARGIN.left,
      right: CHART_MARGIN.right,
      pointerEvents: 'none',
      overflow: 'hidden',
    }}>
      {/* Solo las líneas divisorias entre laps, sin relleno */}
      {lapRanges.slice(1).map((r, i) => {
        const leftPct = (r.start / totalDuration) * 100;
        return (
          <div
            key={`lap-line-${i}`}
            style={{
              position: 'absolute',
              top: 0,
              bottom: 0,
              left: `${leftPct}%`,
              width: '1px',
              background: 'rgba(99,102,241,0.25)',
            }}
          />
        );
      })}
    </div>
  );
}

// ─── Custom tooltip ───────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { color: string; name: string; value: number }[];
  label?: number;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className={styles.tooltip}>
      <p className={styles.tooltipTime}>{formatTime(label ?? 0)}</p>
      {payload.map((p, i) => (
        <p key={i} className={styles.tooltipRow} style={{ color: p.color }}>
          {p.name}: <strong>{p.value}{p.name === 'Potencia' ? ' W' : ' ppm'}</strong>
        </p>
      ))}
    </div>
  );
}

// ─── Modal ────────────────────────────────────────────────────────────────────

export default function WorkoutAnalyzeModal({
  training,
  onClose,
}: {
  training: DoneTraining;
  onClose: () => void;
}) {
  const hasPower = (training.power_stream?.length ?? 0) > 0;
  const hasHr    = (training.hr_stream?.length ?? 0) > 0;
  const streamLen = Math.max(training.power_stream?.length ?? 0, training.hr_stream?.length ?? 0);
  const hasLaps  = (training.laps?.length ?? 0) > 0;

  const realDuration = training.time_stream?.length
    ? training.time_stream[training.time_stream.length - 1]
    : streamLen;

  const data = useMemo(
    () => buildChartData(training.power_stream, training.hr_stream, training.time_stream),
    [training],
  );
  const xTicks = useMemo(() => calculateXTicks(realDuration), [realDuration]);
  const lapRanges = useMemo(
    () => hasLaps ? buildLapRanges(training.laps!) : [],
    [training.laps, hasLaps],
  );

  // ── Selección manual ──────────────────────────────────────────────────────
  const [selStart, setSelStart] = useState<number | null>(null);
  const [selEnd,   setSelEnd]   = useState<number | null>(null);
  const [hoverTime, setHoverTime] = useState<number | null>(null);

  // ── Lap hover ─────────────────────────────────────────────────────────────
  const [hoveredLap, setHoveredLap] = useState<LapRange | null>(null);

  useEffect(() => {
    if (!hasLaps || hoverTime === null) { setHoveredLap(null); return; }
    setHoveredLap(lapRanges.find(r => hoverTime >= r.start && hoverTime < r.end) ?? null);
  }, [hoverTime, lapRanges, hasLaps]);

  const handleChartClick = (e: {
    activeLabel?: string | number;
    activePayload?: { payload: { time: number } }[];
  } | null) => {
    const raw = e?.activeLabel ?? e?.activePayload?.[0]?.payload?.time;
    const t = raw != null ? Number(raw) : null;
    if (t == null || isNaN(t)) return;
    if (selStart === null || selEnd !== null) { setSelStart(t); setSelEnd(null); }
    else setSelEnd(t);
  };

  const handleChartMouseMove = (e: { activeLabel?: string | number } | null) => {
    const raw = e?.activeLabel;
    setHoverTime(raw != null ? Number(raw) : null);
  };

  const clearSelection = () => { setSelStart(null); setSelEnd(null); };

  // ── Stats panel ───────────────────────────────────────────────────────────
  const intervalStats = useMemo(() => {
    if (selStart !== null && selEnd !== null) {
      const from = Math.min(selStart, selEnd);
      const to   = Math.max(selStart, selEnd);
      return {
        label: `${formatTime(from)} → ${formatTime(to)}`,
        duration: to - from,
        avgPower: streamAvg(training.power_stream, training.time_stream, from, to),
        avgHr:    streamAvg(training.hr_stream,    training.time_stream, from, to),
        lapName: null as string | null,
        distance: null as number | null,
      };
    }
    if (hoveredLap) {
      const { lap, start, end } = hoveredLap;
      return {
        label: `${formatTime(start)} → ${formatTime(end)}`,
        duration: lap.elapsed_time,
        avgPower: lap.avg_watts ?? streamAvg(training.power_stream, training.time_stream, start, end),
        avgHr:    lap.avg_hr    ?? streamAvg(training.hr_stream,    training.time_stream, start, end),
        lapName: lap.name || `Lap ${lap.index}`,
        distance: lap.distance > 0 ? lap.distance : null,
      };
    }
    return null;
  }, [selStart, selEnd, hoveredLap, training]);

  const selMin = selStart !== null && selEnd !== null ? Math.min(selStart, selEnd) : selStart;
  const selMax = selStart !== null && selEnd !== null ? Math.max(selStart, selEnd) : null;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  return createPortal(
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <h2 className={styles.title}>{training.name || 'Análisis del entreno'}</h2>
            <span className={styles.subtitle}>
              {hasLaps ? `${training.laps!.length} laps · Análisis 360` : 'Análisis 360'}
            </span>
          </div>
          <div className={styles.headerRight}>
            {selStart !== null && (
              <button className={styles.clearBtn} onClick={clearSelection}>Limpiar selección</button>
            )}
            <button className={styles.closeBtn} onClick={onClose} aria-label="Cerrar">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        {/* Hint */}
        <div className={styles.hint}>
          {selStart === null
            ? hasLaps
              ? 'Pasa el cursor sobre la gráfica para ver los laps · Haz clic para seleccionar un intervalo'
              : 'Haz clic en la gráfica para marcar el inicio del intervalo'
            : selEnd === null
              ? `Inicio: ${formatTime(selStart)} — Haz clic para marcar el final`
              : null}
        </div>

        {/* Stats panel */}
        <div className={`${styles.intervalStats} ${!intervalStats ? styles.intervalStatsEmpty : ''}`}>
          {intervalStats ? (
            <>
              <div className={styles.intervalStat}>
                <span className={styles.intervalStatLabel}>{intervalStats.lapName ?? 'Intervalo'}</span>
                <span className={styles.intervalStatValue}>{intervalStats.label}</span>
                <span className={styles.intervalStatSub}>{formatTime(intervalStats.duration)}</span>
              </div>
              {intervalStats.distance !== null && (
                <div className={styles.intervalStat}>
                  <span className={styles.intervalStatLabel}>Distancia</span>
                  <span className={styles.intervalStatValue}>{(intervalStats.distance / 1000).toFixed(2)} km</span>
                </div>
              )}
              {intervalStats.avgPower !== null && (
                <div className={styles.intervalStat}>
                  <span className={styles.intervalStatLabel}>Potencia media</span>
                  <span className={styles.intervalStatValue} style={{ color: '#8b5cf6' }}>{intervalStats.avgPower} W</span>
                </div>
              )}
              {intervalStats.avgHr !== null && (
                <div className={styles.intervalStat}>
                  <span className={styles.intervalStatLabel}>FC media</span>
                  <span className={styles.intervalStatValue} style={{ color: '#ef4444' }}>{intervalStats.avgHr} ppm</span>
                </div>
              )}
            </>
          ) : (
            <span className={styles.intervalStatsPlaceholder}>
              {hasLaps ? 'Pasa el cursor sobre un lap para ver sus métricas' : 'Selecciona un intervalo en la gráfica para ver las métricas'}
            </span>
          )}
        </div>

        {/* Chart */}
        <div className={styles.chartArea}>
          {!hasPower && !hasHr ? (
            <div className={styles.empty}>No hay datos de stream disponibles para este entreno.</div>
          ) : (
            <div style={{ position: 'relative', width: '100%', height: '100%' }}>
              {/* Lap overlay — CSS puro, sin depender de internals de Recharts */}
              {hasLaps && (
                <LapOverlay
                  lapRanges={lapRanges}
                  hoveredLapIndex={hoveredLap?.lap.index ?? null}
                  totalDuration={realDuration}
                />
              )}

              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={data}
                  margin={{ top: CHART_MARGIN.top, right: 24, bottom: 8, left: 8 }}
                  onClick={handleChartClick}
                  onMouseMove={handleChartMouseMove}
                  onMouseLeave={() => setHoverTime(null)}
                  style={{ cursor: 'crosshair' }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                  <XAxis
                    dataKey="time"
                    tick={{ fontSize: 12, fontFamily: "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Helvetica, Arial, sans-serif" }}
                    stroke="rgba(0,0,0,0.25)"
                    axisLine={false}
                    tickLine={false}
                    ticks={xTicks}
                    tickFormatter={v => formatTime(Number(v))}
                  />
                  <YAxis
                    yAxisId="power"
                    orientation="left"
                    tick={{ fontSize: 12, fontFamily: "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Helvetica, Arial, sans-serif" }}
                    stroke="#8b5cf6"
                    axisLine={false}
                    tickLine={false}
                    unit=" W"
                    width={56}
                    domain={['auto', 'auto']}
                  />
                  <YAxis
                    yAxisId="hr"
                    orientation="right"
                    tick={{ fontSize: 12, fontFamily: "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Helvetica, Arial, sans-serif" }}
                    stroke="#ef4444"
                    axisLine={false}
                    tickLine={false}
                    unit=" ppm"
                    width={60}
                    domain={['auto', 'auto']}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend iconType="circle" iconSize={9} wrapperStyle={{ fontSize: 13, paddingTop: 8 }} />

                  {/* Selección manual */}
                  {selMin !== null && selMax !== null && (
                    <ReferenceArea
                      yAxisId="power"
                      x1={selMin} x2={selMax}
                      fill="rgba(99,102,241,0.14)"
                      stroke="rgba(99,102,241,0.45)"
                      strokeWidth={1}
                    />
                  )}
                  {selStart !== null && selEnd === null && hoverTime !== null && hoverTime !== selStart && (
                    <ReferenceArea
                      yAxisId="power"
                      x1={Math.min(selStart, hoverTime)} x2={Math.max(selStart, hoverTime)}
                      fill="rgba(99,102,241,0.07)"
                      stroke="rgba(99,102,241,0.25)"
                      strokeWidth={1}
                      strokeDasharray="4 2"
                    />
                  )}
                  {selStart !== null && selEnd === null && (
                    <ReferenceArea yAxisId="power" x1={selStart} x2={selStart} stroke="#6366f1" strokeWidth={2} />
                  )}

                  {hasPower && (
                    <Line yAxisId="power" type="monotone" dataKey="watts" name="Potencia"
                      stroke="#8b5cf6" strokeWidth={2} dot={false} connectNulls />
                  )}
                  {hasHr && (
                    <Line yAxisId="hr" type="monotone" dataKey="bpm" name="FC"
                      stroke="#ef4444" strokeWidth={2} dot={false} connectNulls />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
