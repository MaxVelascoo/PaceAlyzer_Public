'use client';
import React from 'react';
import Link from 'next/link';
import styles from '@/app/chat/chat.module.css';
import { PlannedWorkout } from '@/components/PlannedWorkoutCard';

export type WeekDay = { key: string; label: string; date: string };

export default function ChatSidebar({
  weekDays,
  selectedDate,
  onSelectDate,
  plannedWorkout,
  loading,
}: {
  weekDays: WeekDay[];
  selectedDate: string;
  onSelectDate: (date: string) => void;
  plannedWorkout: PlannedWorkout | null;
  loading: boolean;
}) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.sidebarHeader}>
        <div className={styles.sidebarTitle}>Chat</div>
      </div>

      <div className={styles.sidebarSection}>
        <div className={styles.sidebarSectionTitle}>Esta semana</div>
        <div className={styles.weekPills}>
          {weekDays.map((d) => {
            const active = d.date === selectedDate;
            return (
              <button
                key={d.key}
                type="button"
                className={active ? `${styles.dayPill} ${styles.dayPillActive}` : styles.dayPill}
                onClick={() => onSelectDate(d.date)}
                aria-pressed={active}
                title={d.date}
              >
                {d.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className={styles.sidebarDivider} />

      <div className={styles.workoutSummary}>
        {loading ? (
          <div className={styles.summaryLoading}>Cargando...</div>
        ) : plannedWorkout ? (
          <Link
            href={`/calendario/dia?date=${selectedDate}`}
            className={styles.summaryCard}
            title="Ver en el calendario"
          >
            <div className={styles.summaryTitle}>{plannedWorkout.title}</div>
            <div className={styles.summaryDuration}>
              {Math.floor(plannedWorkout.planned_duration_s / 60)} min
            </div>
            {plannedWorkout.description && (
              <div className={styles.summaryDescription}>{plannedWorkout.description}</div>
            )}
            <div className={styles.summaryLink}>Ver en calendario →</div>
          </Link>
        ) : (
          <div className={styles.summaryEmpty}>No hay entreno planificado</div>
        )}
      </div>
    </aside>
  );
}
