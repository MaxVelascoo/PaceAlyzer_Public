'use client';
import React, { useMemo } from 'react';
import { Syne } from 'next/font/google';
import styles from '@/app/calendario/calendario.module.css';
import type { PlannedWorkout } from '@/components/PlannedWorkoutCard';
import type { DoneTraining } from '@/components/DoneWorkoutCard';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });

// ─── SVG Icons ────────────────────────────────────────────────────────────────

function IconChart() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

// ─── Types ────────────────────────────────────────────────────────────────────

type AnalysisMetrics = {
  durationDeviation: { planned: number; actual: number; diffPercent: number } | null;
  distanceDeviation: { planned: number; actual: number; diffPercent: number } | null;
  variabilityIndex: number | null;
  wPerKg: number | null;
  decoupling: number | null;
  avgPower: number | null;
  avgHr: number | null;
};

// ─── Formatters ───────────────────────────────────────────────────────────────

function fmtDuration(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (h > 0) return `${h}h ${m}min`;
  return `${m}min`;
}

function fmtKm(meters: number): string {
  return `${(meters / 1000).toFixed(1)} km`;
}

// ─── Calculations ─────────────────────────────────────────────────────────────

function calculateMetrics(
  planned: PlannedWorkout | null,
  done: DoneTraining | null,
  userWeight: number | null,
): AnalysisMetrics {
  const m: AnalysisMetrics = {
    durationDeviation: null,
    distanceDeviation: null,
    variabilityIndex: null,
    wPerKg: null,
    decoupling: null,
    avgPower: done?.weighted_average_watts ?? null,
    avgHr: done?.avgheartrate ?? null,
  };

  if (!done) return m;

  // Duración planificada vs realizada
  if (planned && done.duration) {
    const diff = done.duration - planned.planned_duration_s;
    m.durationDeviation = {
      planned: planned.planned_duration_s,
      actual: done.duration,
      diffPercent: (diff / planned.planned_duration_s) * 100,
    };
  }

  // Distancia planificada vs realizada
  if (planned?.planned_distance_m && done.distance) {
    const diff = done.distance - planned.planned_distance_m;
    m.distanceDeviation = {
      planned: planned.planned_distance_m,
      actual: done.distance,
      diffPercent: (diff / planned.planned_distance_m) * 100,
    };
  }

  // Variability Index: NP / AP
  if (done.power_stream && done.power_stream.length > 0) {
    const validWatts = done.power_stream.filter(w => w != null && w > 0);
    if (validWatts.length > 0) {
      const ap = validWatts.reduce((a, b) => a + b, 0) / validWatts.length;
      const np = done.weighted_average_watts ?? ap;
      if (ap > 0) m.variabilityIndex = np / ap;
    }
  }

  // W/kg
  if (done.weighted_average_watts && userWeight && userWeight > 0) {
    m.wPerKg = done.weighted_average_watts / userWeight;
  }

  // Decoupling cardíaco (Pw:HR ratio primera mitad vs segunda mitad)
  if (
    done.power_stream && done.hr_stream &&
    done.power_stream.length > 100 && done.hr_stream.length > 100
  ) {
    const mid = Math.floor(done.power_stream.length / 2);
    const avg = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length;

    const ap1 = avg(done.power_stream.slice(0, mid));
    const hr1 = avg(done.hr_stream.slice(0, mid));
    const ap2 = avg(done.power_stream.slice(mid));
    const hr2 = avg(done.hr_stream.slice(mid));

    if (ap1 > 0 && hr1 > 0 && ap2 > 0 && hr2 > 0) {
      const ratio1 = ap1 / hr1;
      const ratio2 = ap2 / hr2;
      m.decoupling = ((ratio1 - ratio2) / ratio1) * 100;
    }
  }

  return m;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className={styles.analysisSection}>{children}</p>
  );
}

function MetricRow({
  label,
  value,
  sub,
  badge,
}: {
  label: string;
  value: string;
  sub?: string;
  badge?: { text: string; level: 'ok' | 'warn' | 'bad' };
}) {
  return (
    <div className={styles.analysisRow}>
      <span className={styles.analysisLabel}>{label}</span>
      <div className={styles.analysisRight}>
        {badge && (
          <span className={`${styles.analysisBadge} ${styles[`analysisBadge_${badge.level}`]}`}>
            {badge.text}
          </span>
        )}
        <span className={styles.analysisValue}>{value}</span>
        {sub && <span className={styles.analysisSub}>{sub}</span>}
      </div>
    </div>
  );
}

function deviationBadge(pct: number): { text: string; level: 'ok' | 'warn' | 'bad' } {
  const abs = Math.abs(pct);
  const sign = pct >= 0 ? '+' : '';
  const text = `${sign}${pct.toFixed(1)}%`;
  if (abs <= 10) return { text, level: 'ok' };
  if (abs <= 20) return { text, level: 'warn' };
  return { text, level: 'bad' };
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function WorkoutAnalysis({
  planned,
  done,
  userWeight,
}: {
  planned: PlannedWorkout | null;
  done: DoneTraining | null;
  userWeight?: number | null;
}) {
  const [isOpen, setIsOpen] = React.useState(false);

  const metrics = useMemo(
    () => calculateMetrics(planned, done, userWeight ?? null),
    [planned, done, userWeight],
  );

  // Solo mostrar si hay entreno realizado
  if (!done) return null;

  const hasComparison = !!(metrics.durationDeviation || metrics.distanceDeviation);
  const hasAdvanced = !!(
    metrics.variabilityIndex !== null ||
    metrics.wPerKg !== null ||
    metrics.decoupling !== null ||
    metrics.avgPower !== null ||
    metrics.avgHr !== null
  );

  return (
    <div className={styles.nutritionAccordion}>
      <button
        className={styles.nutritionAccordionToggle}
        onClick={() => setIsOpen(o => !o)}
        aria-expanded={isOpen}
      >
        <span className={styles.analysisToggleIcon}>
          <IconChart />
        </span>
        <span className={`${styles.nutritionAccordionTitle} ${syne.className}`}>
          Análisis del entreno
        </span>
        {!hasComparison && !hasAdvanced && (
          <span className={styles.nutritionAccordionBadge}>Sin datos</span>
        )}
        <span className={styles.nutritionAccordionChevron}>
          {isOpen ? '▲' : '▼'}
        </span>
      </button>

      {isOpen && (
        <div className={styles.nutritionAccordionBody}>
          <div className={styles.analysisBody}>

            {/* Comparativa con el plan */}
            {hasComparison && (
              <div className={styles.analysisBlock}>
                <SectionTitle>Planificado vs realizado</SectionTitle>
                <div className={styles.analysisRows}>
                  {metrics.durationDeviation && (
                    <MetricRow
                      label="Duración"
                      value={fmtDuration(metrics.durationDeviation.actual)}
                      sub={`vs ${fmtDuration(metrics.durationDeviation.planned)}`}
                      badge={deviationBadge(metrics.durationDeviation.diffPercent)}
                    />
                  )}
                  {metrics.distanceDeviation && (
                    <MetricRow
                      label="Distancia"
                      value={fmtKm(metrics.distanceDeviation.actual)}
                      sub={`vs ${fmtKm(metrics.distanceDeviation.planned)}`}
                      badge={deviationBadge(metrics.distanceDeviation.diffPercent)}
                    />
                  )}
                </div>
              </div>
            )}

            {/* Separador */}
            {hasComparison && hasAdvanced && (
              <div className={styles.analysisDivider} />
            )}

            {/* Métricas avanzadas */}
            {hasAdvanced && (
              <div className={styles.analysisBlock}>
                <SectionTitle>Métricas avanzadas</SectionTitle>
                <div className={styles.analysisRows}>
                  {metrics.variabilityIndex !== null && (
                    <MetricRow
                      label="Variabilidad (VI)"
                      value={metrics.variabilityIndex.toFixed(2)}
                      sub={metrics.variabilityIndex > 1.05 ? 'Variable' : 'Constante'}
                    />
                  )}
                  {metrics.wPerKg !== null && (
                    <MetricRow
                      label="Eficiencia"
                      value={`${metrics.wPerKg.toFixed(1)} W/kg`}
                    />
                  )}
                  {metrics.decoupling !== null && (
                    <MetricRow
                      label="Decoupling cardíaco"
                      value={`${Math.abs(metrics.decoupling).toFixed(1)}%`}
                      sub={Math.abs(metrics.decoupling) > 5 ? 'Alto' : 'Bajo'}
                    />
                  )}
                  {metrics.avgPower !== null && (
                    <MetricRow
                      label="Potencia media"
                      value={`${Math.round(metrics.avgPower)} W`}
                    />
                  )}
                  {metrics.avgHr !== null && (
                    <MetricRow
                      label="FC media"
                      value={`${Math.round(metrics.avgHr)} ppm`}
                    />
                  )}
                </div>
              </div>
            )}

            {/* Estado vacío */}
            {!hasComparison && !hasAdvanced && (
              <div className={styles.analysisEmpty}>
                <span className={styles.analysisEmptyIcon}><IconChart /></span>
                <p>No hay suficientes datos para el análisis.</p>
              </div>
            )}

          </div>
        </div>
      )}
    </div>
  );
}
