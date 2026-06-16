'use client';

import React from 'react';
import styles from '@/app/calendario/calendario.module.css';

type NutritionTarget = {
  key: string;
  label: string;
  unit: string;
  ui?: 'progress' | 'range';
  value?: number | null;
  range?: { min: number; max: number } | null;
  ui_meta?: { max?: number; min?: number };
};

type NutritionBlock = {
  window_min?: { min: number; max: number };
  targets?: NutritionTarget[];
  notes?: string[];
  examples?: string[];
};

export type NutritionData = {
  version: number;
  pre?: NutritionBlock;
  during?: NutritionBlock;
  post?: NutritionBlock;
};

function clamp(n: number, a = 0, b = 100) {
  return Math.max(a, Math.min(b, n));
}

function ProgressBar({ valuePct }: { valuePct: number }) {
  return (
    <div className={styles.nBarTrack}>
      <div className={styles.nBarFill} style={{ width: `${clamp(valuePct)}%` }} />
    </div>
  );
}

function RangeBar({ minPct, maxPct }: { minPct: number; maxPct: number }) {
  const left = clamp(Math.min(minPct, maxPct));
  const width = clamp(Math.abs(maxPct - minPct));
  return (
    <div className={styles.nBarTrack}>
      <div
        className={styles.nBarRange}
        style={{ left: `${left}%`, width: `${width}%` }}
      />
    </div>
  );
}

function TargetRow({ t }: { t: NutritionTarget }) {
  // Heurística de máximos si no hay ui_meta:
  // - g/kg: max 6
  // - g/h: max 120
  // - ml/h: max 1000
  // - g: max 120
  // - %: max 200
  const inferMax = () => {
    const u = (t.unit || '').toLowerCase();
    if (t.ui_meta?.max) return t.ui_meta.max;
    if (u.includes('g/kg')) return 6;
    if (u.includes('g/h')) return 120;
    if (u.includes('ml/h')) return 1000;
    if (u.includes('%')) return 200;
    if (u === 'g') return 120;
    return 100;
  };

  const max = inferMax();

  const isRange = t.ui === 'range' || (!!t.range && t.value == null);

  return (
    <div className={styles.nTarget}>
      <div className={styles.nTargetTop}>
        <div className={styles.nTargetLabel}>{t.label}</div>

        {/* valor a la derecha */}
        <div className={styles.nTargetValue}>
          {isRange && t.range
            ? `${t.range.min}–${t.range.max} ${t.unit}`
            : t.value != null
              ? `${t.value} ${t.unit}`
              : `— ${t.unit}`}
        </div>
      </div>

      {/* barra */}
      {isRange && t.range ? (
        <RangeBar
          minPct={(t.range.min / max) * 100}
          maxPct={(t.range.max / max) * 100}
        />
      ) : (
        <ProgressBar valuePct={t.value != null ? (t.value / max) * 100 : 0} />
      )}
    </div>
  );
}

function MiniCard({
  title,
  subtitle,
  accentClass,
  block,
}: {
  title: string;
  subtitle?: string;
  accentClass: string; // pre/during/post
  block?: NutritionBlock;
}) {
  const targets = block?.targets ?? [];
  const examples = block?.examples ?? [];
  const notes = block?.notes ?? [];

  return (
    <article className={`${styles.nMiniCard} ${accentClass}`}>
      <div className={styles.nMiniHeader}>
        <div className={styles.nMiniTitleRow}>
          <div className={styles.nMiniTitle}>{title}</div>
        </div>
        {subtitle ? <div className={styles.nMiniSubtitle}>{subtitle}</div> : null}
      </div>

      <div className={styles.nMiniBody}>
        {targets.length ? (
          <div className={styles.nTargets}>
            {targets.map((t) => (
              <TargetRow key={t.key} t={t} />
            ))}
          </div>
        ) : (
          <div className={styles.nMiniEmpty}>Sin targets definidos</div>
        )}

        {(notes.length || examples.length) ? (
          <div className={styles.nChips}>
            {examples.slice(0, 2).map((e, idx) => (
              <span key={`ex-${idx}`} className={styles.nChip}>
                {e}
              </span>
            ))}
            {notes.slice(0, 1).map((n, idx) => (
              <span key={`note-${idx}`} className={`${styles.nChip} ${styles.nChipSoft}`}>
                {n}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}

export default function NutritionPanel({
  nutrition,
  loading,
}: {
  nutrition?: NutritionData | null;
  loading?: boolean;
}) {
  if (loading) {
    return (
      <div className={styles.nutritionPanel}>
        <div className={styles.nutritionEmpty}>
          Cargando…
        </div>
      </div>
    );
  }

  const hasData =
    nutrition?.pre?.targets?.length ||
    nutrition?.during?.targets?.length ||
    nutrition?.post?.targets?.length;

  return (
    <div className={styles.nutritionPanel}>
      {!hasData ? (
        <div className={styles.nutritionEmpty}>
          No hay nutrición definida para este entreno
        </div>
      ) : (
        <div className={styles.nutritionGrid}>
          <MiniCard
            title="PRE-ENTRENO"
            subtitle={
              nutrition?.pre?.window_min
                ? `${nutrition.pre.window_min.min}–${nutrition.pre.window_min.max} min antes`
                : undefined
            }
            accentClass={styles.nPre}
            block={nutrition?.pre}
          />

          <MiniCard
            title="DURANTE"
            accentClass={styles.nDuring}
            block={nutrition?.during}
          />

          <MiniCard
            title="DESPUÉS"
            accentClass={styles.nPost}
            block={nutrition?.post}
          />
        </div>
      )}
    </div>
  );
}