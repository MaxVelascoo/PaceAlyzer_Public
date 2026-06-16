'use client';
import React, { useMemo } from 'react';
import Link from 'next/link';
import { createPortal } from 'react-dom';
import styles from '@/app/calendario/calendario.module.css';
import { Space_Grotesk } from 'next/font/google';
import type { NutritionData } from '@/components/NutritionPanel';
const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  weight: ['500', '600', '700'],
});

type Zone = 'Z1'|'Z2'|'Z3'|'Z4'|'Z5'|'Z6'|'Z7';

type IntervalStep = {
  type: 'interval';
  label?: string;
  duration_s: number;
  target: { zone?: Zone; zone_min?: Zone; zone_max?: Zone };
  instructions?: string;
};

type RepeatStep = {
  type: 'repeat';
  label?: string;
  repeat: number;
  steps: Step[];
};

type Step = IntervalStep | RepeatStep;

export type PlannedWorkout = {
  id: string;
  user_id: string;
  date: string; // YYYY-MM-DD
  title: string;
  description: string | null;
  planned_duration_s: number;
  planned_distance_m: number | null;
  estimated_tss: number | null;
  structure: {
    schema_version: number;
    intensity_model?: string;
    zone_system?: string;
    session?: {
      goal?: string;
      description?: string;
      execution_notes?: string[];
      warnings?: string[];
    };
    steps: Step[];
  };
  nutrition?: NutritionData | null;
  status: 'planned' | 'modified' | 'completed' | 'skipped';
  source: 'system' | 'user_modified' | 'template' | 'regenerated';
};

function formatStepDuration(sec: number) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (m <= 0) return `${s}s`;
  if (s === 0) return `${m} min`;
  return `${m} min ${s}s`;
}

function targetToZoneText(target: IntervalStep['target']) {
  if (target.zone) return `Zona ${target.zone.replace('Z', '')}`;
  if (target.zone_min && target.zone_max) {
    return `Zona ${target.zone_min.replace('Z', '')}-${target.zone_max.replace('Z', '')}`;
  }
  return 'Zona —';
}

function targetToZoneKey(target: IntervalStep['target']): Zone {
  // Si es rango, usamos el máximo como “intensidad” para la altura/color.
  return (target.zone ?? target.zone_max ?? target.zone_min ?? 'Z2') as Zone;
}

type FlatInterval = {
  zone: Zone;
  duration_s: number;
};

function flattenSteps(steps: Step[]): FlatInterval[] {
  const out: FlatInterval[] = [];
  const walk = (arr: Step[]) => {
    for (const st of arr) {
      if (st.type === 'interval') {
        out.push({ zone: targetToZoneKey(st.target), duration_s: st.duration_s });
      } else {
        for (let i = 0; i < st.repeat; i++) walk(st.steps);
      }
    }
  };
  walk(steps);
  return out;
}

function zoneHeightPx(zone: Zone) {
  switch (zone) {
    case 'Z1': return 18;
    case 'Z2': return 28;
    case 'Z3': return 40;
    case 'Z4': return 52;
    case 'Z5': return 60;
    case 'Z6': return 68;
    case 'Z7': return 72;
    default: return 28;
  }
}

function renderStep(step: Step, level: number): React.ReactNode {
  if (step.type === 'interval') {
    return (
      <div className={styles.stepBlock} style={{ paddingLeft: `${level * 18}px` }}>
        <div className={styles.stepLine}>
          <span className={styles.stepName}>{step.label ?? 'Intervalo'}</span>
          <span className={`${styles.stepDur} ${spaceGrotesk.className}`}>{formatStepDuration(step.duration_s)}</span>
        </div>
        <div className={styles.stepZone}>{targetToZoneText(step.target)}</div>
        {step.instructions ? <div className={styles.stepHint}>{step.instructions}</div> : null}
      </div>
    );
  }

  // repeat
  return (
    <div className={styles.stepBlock} style={{ paddingLeft: `${level * 18}px` }}>
      <div className={styles.stepRepeat}>
        <span className={styles.stepRepeatTitle}>Repeat <span className={spaceGrotesk.className}>{step.repeat}</span> times</span>
        {step.label ? <span className={styles.stepRepeatLabel}>— {step.label}</span> : null}
      </div>

      <div className={styles.repeatChildren}>
        {step.steps.map((child, idx) => (
          <div key={idx} className={styles.repeatChildRow}>
            <span className={styles.bullet} aria-hidden>•</span>
            <div className={styles.repeatChildContent}>
              {renderStep(child, level + 1)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PlannedWorkoutCard({ workout }: { workout: PlannedWorkout }) {
  const [hoveredZone, setHoveredZone] = React.useState<{ zone: Zone; x: number; y: number } | null>(null);
  const [mounted, setMounted] = React.useState(false);
  
  React.useEffect(() => {
    setMounted(true);
  }, []);
  
  const steps = useMemo(() => workout?.structure?.steps ?? [], [workout?.structure?.steps]);
  const flat = useMemo(() => flattenSteps(steps), [steps]);
  const total = useMemo(() => flat.reduce((acc, it) => acc + (it.duration_s || 0), 0), [flat]);

  const segments = useMemo(() => {
    const denom = Math.max(total, 1);
    return flat.map((it, i) => ({
      key: `${i}-${it.zone}`,
      zone: it.zone,
      widthPct: (it.duration_s / denom) * 100,
      heightPx: zoneHeightPx(it.zone),
      duration_s: it.duration_s,
    }));
  }, [flat, total]);

  const subtitle =
    workout.description?.trim() ||
    workout.structure.session?.goal?.trim() ||
    'Entrenamiento planificado para hoy.';

  return (
    <div className={styles.plannedInner}>
      {/* Header */}
      <header className={styles.plannedTop}>
        <h4 className={styles.plannedTitle}>{workout.title}</h4>
        <p className={styles.plannedSubtitle}>{subtitle}</p>
      </header>

      {/* Chart */}
      <section className={styles.zoneChart}>
        <div className={styles.zoneChartGrid} />
        <div className={styles.zoneBars}>
          {segments.map(seg => (
            <div
              key={seg.key}
              className={`${styles.zoneSeg} ${styles[`zone_${seg.zone}`]}`}
              style={{
                width: `${seg.widthPct}%`,
                height: `${seg.heightPx}px`,
              }}
              onMouseEnter={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                setHoveredZone({
                  zone: seg.zone,
                  x: rect.left + rect.width / 2,
                  y: rect.top - 10,
                });
              }}
              onMouseLeave={() => setHoveredZone(null)}
            />
          ))}
        </div>
      </section>
      
      {/* Tooltip usando portal */}
      {mounted && hoveredZone && createPortal(
        <div
          className={styles.zoneTooltip}
          style={{
            position: 'fixed',
            left: `${hoveredZone.x}px`,
            top: `${hoveredZone.y}px`,
            transform: 'translate(-50%, calc(-100% - 8px))',
            pointerEvents: 'none',
            zIndex: 9999,
          }}
        >
          <div className={styles.zoneTooltipContent}>
            <div style={{ marginBottom: '4px', fontSize: '12px', color: '#999' }}>
              Zona de intensidad
            </div>
            <div style={{ fontSize: '14px', fontWeight: '600', color: '#333' }}>
              {hoveredZone.zone}
            </div>
          </div>
        </div>,
        document.body
      )}

      <section className={styles.stepsSection}>
        <ol className={styles.stepsListTop}>
          {steps.map((st, idx) => (
            <li key={idx} className={styles.stepRowTop}>
              {renderStep(st, 0)}
            </li>
          ))}
        </ol>
      </section>

      {/* Footer */}
      <footer className={styles.plannedFooter}>
        <span className={styles.totalLabel}>Duración total</span>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '16px' }}>
          {workout.estimated_tss != null && (
            <span className={styles.totalLabel}>
              TSS est. <span className={styles.totalValue}>{workout.estimated_tss}</span>
            </span>
          )}
          <span className={styles.totalValue}>{formatStepDuration(total)}</span>
        </div>
      </footer>

      {/* Botón Hablar con Pazey — dentro del card, debajo del footer */}
      <div className={styles.plannedPazeyCta}>
        <Link
          href={`/chat?workout_id=${workout.id}&date=${workout.date}`}
          className={styles.chatButtonSm}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          Hablar con Pazey
        </Link>
      </div>
    </div>
  );
}
