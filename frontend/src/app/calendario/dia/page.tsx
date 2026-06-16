'use client';
import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Syne } from 'next/font/google';
import { useUser } from '@/context/userContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import WeekHeader from '@/components/WeekHeader';
import { useCalendarioData } from '@/hooks/useCalendarioData';
import PlannedWorkoutCard from '@/components/PlannedWorkoutCard';
import { usePlannedWorkout } from '@/hooks/usePlannedWorkout';
import DoneWorkoutCard from '@/components/DoneWorkoutCard';
import NutritionPanel from '@/components/NutritionPanel';
import WorkoutAnalysis from '@/components/WorkoutAnalysis';
import type { DoneTraining } from '@/components/DoneWorkoutCard';
import type { PlannedWorkout } from '@/components/PlannedWorkoutCard';

import styles from '../calendario.module.css';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });
const dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

// ─── helpers ────────────────────────────────────────────────────────────────

function fmtDuration(s: number | null | undefined) {
  if (!s) return null;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function fmtKm(meters: number | null | undefined) {
  if (!meters) return null;
  return `${(meters / 1000).toFixed(1)} km`;
}

/** Empareja planificados con realizados: 1-a-1 por orden, el resto queda sin pareja */
function buildSessions(
  planned: PlannedWorkout[],
  done: DoneTraining[],
): Array<{ planned: PlannedWorkout | null; done: DoneTraining | null }> {
  const len = Math.max(planned.length, done.length);
  return Array.from({ length: len }, (_, i) => ({
    planned: planned[i] ?? null,
    done: done[i] ?? null,
  }));
}

// ─── DaySummaryStrip ─────────────────────────────────────────────────────────

function DaySummaryStrip({ done }: { done: DoneTraining[] }) {
  if (done.length === 0) return null;
  const totalKm = done.reduce((acc, t) => acc + (t.distance ?? 0), 0);
  const totalSec = done.reduce((acc, t) => acc + (t.duration ?? 0), 0);
  const sessions = done.length;

  return (
    <div className={styles.daySummaryStrip}>
      <div className={styles.daySummaryStat}>
        <span className={styles.daySummaryVal}>{sessions}</span>
        <span className={styles.daySummaryLbl}>{sessions === 1 ? 'sesión' : 'sesiones'}</span>
      </div>
      {totalKm > 0 && (
        <>
          <div className={styles.daySummaryDivider} />
          <div className={styles.daySummaryStat}>
            <span className={styles.daySummaryVal}>{fmtKm(totalKm)}</span>
            <span className={styles.daySummaryLbl}>distancia</span>
          </div>
        </>
      )}
      {totalSec > 0 && (
        <>
          <div className={styles.daySummaryDivider} />
          <div className={styles.daySummaryStat}>
            <span className={styles.daySummaryVal}>{fmtDuration(totalSec)}</span>
            <span className={styles.daySummaryLbl}>tiempo</span>
          </div>
        </>
      )}
    </div>
  );
}

// ─── SessionBlock ─────────────────────────────────────────────────────────────

function SessionBlock({
  index,
  total,
  planned,
  done,
  ftp,
  userWeight,
  onDeletePlanned,
}: {
  index: number;
  total: number;
  planned: PlannedWorkout | null;
  done: DoneTraining | null;
  ftp: number | null;
  userWeight: number | null;
  onDeletePlanned?: (id: string) => void;
}) {
  const [nutritionOpen, setNutritionOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const hasNutrition = !!(
    planned?.nutrition?.pre?.targets?.length ||
    planned?.nutrition?.during?.targets?.length ||
    planned?.nutrition?.post?.targets?.length
  );

  const handleDelete = async () => {
    if (!planned || deleting) return;
    setDeleting(true);
    onDeletePlanned?.(planned.id);
  };

  return (
    <div className={styles.sessionBlock}>
      {/* Session label — only show if multiple sessions */}
      {total > 1 && (
        <div className={styles.sessionLabel}>
          <span className={styles.sessionIndex}>Sesión {index + 1}</span>
        </div>
      )}

      <div className={styles.sessionGrid}>
        {/* ── Planificado ── */}
        <div className={styles.sessionCol}>
          <div className={styles.sessionColHeader}>
            <span className={styles.sessionColDot} style={{ background: '#6366f1' }} />
            <span className={`${styles.sessionColTitle} ${syne.className}`}>Planificado</span>
            {planned && (
              <span className={styles.sessionColMeta}>
                {fmtDuration(planned.planned_duration_s)}
              </span>
            )}
            {planned && (
              <button
                className={styles.deletePlannedBtn}
                onClick={handleDelete}
                disabled={deleting}
                title="Borrar entreno planificado"
                aria-label="Borrar entreno planificado"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                  <path d="M10 11v6M14 11v6" />
                  <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                </svg>
              </button>
            )}
          </div>
          <div className={styles.sessionColBody}>
            {planned ? (
              <PlannedWorkoutCard workout={planned} />
            ) : (
              <div className={styles.sessionEmpty}>
                <p>Sin entreno planificado</p>
                <div className={styles.plannedPazeyCta}>
                  <Link href="/chat" className={styles.chatButtonSm}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    Hablar con Pazey
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── Realizado ── */}
        <div className={styles.sessionCol}>
          <div className={styles.sessionColHeader}>
            <span className={styles.sessionColDot} style={{ background: '#FC4C02' }} />
            <span className={`${styles.sessionColTitle} ${syne.className}`}>Realizado</span>
            {done && (
              <span className={styles.sessionColMeta}>
                {[fmtDuration(done.duration), fmtKm(done.distance)].filter(Boolean).join(' · ')}
              </span>
            )}
          </div>
          <div className={styles.sessionColBody}>
            {done ? (
              <DoneWorkoutCard training={done} ftp={ftp} />
            ) : (
              <div className={styles.sessionEmpty}>
                <p>Sin entreno registrado</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Nutrición de sesión (colapsable) ── */}
      {planned && (
        <div className={styles.nutritionAccordion}>
          <button
            className={styles.nutritionAccordionToggle}
            onClick={() => setNutritionOpen(o => !o)}
            aria-expanded={nutritionOpen}
          >
            <span className={styles.sessionColDot} style={{ background: '#22c55e' }} />
            <span className={`${styles.nutritionAccordionTitle} ${syne.className}`}>
              Nutrición de sesión
            </span>
            {!hasNutrition && (
              <span className={styles.nutritionAccordionBadge}>Sin datos</span>
            )}
            <span className={styles.nutritionAccordionChevron}>
              {nutritionOpen ? '▲' : '▼'}
            </span>
          </button>
          {nutritionOpen && (
            <div className={styles.nutritionAccordionBody}>
              <NutritionPanel nutrition={planned.nutrition ?? null} loading={false} />
            </div>
          )}
        </div>
      )}

      {/* ── Análisis del entreno (colapsable) ── */}
      <WorkoutAnalysis planned={planned} done={done} userWeight={userWeight} />
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

function CalendarioContent() {
  const hoy = new Date();
  const hoyDia = hoy.getDay() === 0 ? 6 : hoy.getDay() - 1;
  const searchParams = useSearchParams();

  const [semanaOffset, setSemanaOffset] = useState(() => {
    const dateParam = searchParams?.get('date');
    if (dateParam) {
      const target = new Date(dateParam + 'T00:00:00');
      const todayMon = new Date(hoy);
      todayMon.setDate(hoy.getDate() - hoyDia);
      todayMon.setHours(0, 0, 0, 0);
      const targetMon = new Date(target);
      const targetDow = target.getDay() === 0 ? 6 : target.getDay() - 1;
      targetMon.setDate(target.getDate() - targetDow);
      targetMon.setHours(0, 0, 0, 0);
      const diffMs = targetMon.getTime() - todayMon.getTime();
      return Math.round(diffMs / (7 * 24 * 60 * 60 * 1000));
    }
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('calendarioSemanaOffset');
      return saved ? parseInt(saved, 10) : 0;
    }
    return 0;
  });

  const [diaSeleccionado, setDiaSeleccionado] = useState(() => {
    const dateParam = searchParams?.get('date');
    if (dateParam) {
      const d = new Date(dateParam + 'T00:00:00');
      return d.getDay() === 0 ? 6 : d.getDay() - 1;
    }
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('calendarioDiaSeleccionado');
      return saved ? parseInt(saved, 10) : hoyDia;
    }
    return hoyDia;
  });

  useEffect(() => {
    localStorage.setItem('calendarioSemanaOffset', semanaOffset.toString());
  }, [semanaOffset]);

  useEffect(() => {
    localStorage.setItem('calendarioDiaSeleccionado', diaSeleccionado.toString());
  }, [diaSeleccionado]);

  const user = useUser()?.user;
  const { hasStrava, loading, trainingsByDate, startOfWeek, refetch, userFtp, userWeight } =
    useCalendarioData(user?.id, semanaOffset);

  const mes = startOfWeek.toLocaleString('es-ES', { month: 'long' });

  const diasConFechas = useMemo(() => {
    return dias.map((dia, i) => {
      const d = new Date(startOfWeek);
      d.setDate(startOfWeek.getDate() + i);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
      return { nombre: dia, numero: d.getDate(), esHoy: semanaOffset === 0 && i === hoyDia, key };
    });
  }, [startOfWeek, semanaOffset, hoyDia]);

  const selectedKey = diasConFechas[diaSeleccionado]?.key;
  const { loading: loadingPlanned, workouts: plannedWorkouts, refetch: refetchPlanned } = usePlannedWorkout(user?.id, selectedKey);
  const doneTrainings: DoneTraining[] = useMemo(
    () => (selectedKey ? (trainingsByDate[selectedKey] ?? []) : []),
    [selectedKey, trainingsByDate],
  );

  const sessions = useMemo(
    () => buildSessions(plannedWorkouts, doneTrainings),
    [plannedWorkouts, doneTrainings],
  );

  // Borrar entreno planificado
  const handleDeletePlanned = async (workoutId: string) => {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';
    await fetch(`${backendUrl}/api/planned-workouts/${workoutId}?user_id=${user?.id}`, {
      method: 'DELETE',
    });
    refetchPlanned();
  };

  // Sync
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  const handleSync = async () => {
    if (!user?.id || syncing) return;
    setSyncError(null);
    try {
      setSyncing(true);
      const startStr = `${startOfWeek.getFullYear()}-${String(startOfWeek.getMonth() + 1).padStart(2, '0')}-${String(startOfWeek.getDate()).padStart(2, '0')}`;
      const endDate = new Date(startOfWeek);
      endDate.setDate(startOfWeek.getDate() + 6);
      const endStr = `${endDate.getFullYear()}-${String(endDate.getMonth() + 1).padStart(2, '0')}-${String(endDate.getDate()).padStart(2, '0')}`;
      const res = await fetch('/api/strava/sync-trainings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: user.id, startDate: startStr, endDate: endStr }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error || 'Error sincronizando entrenos');
      refetch();
    } catch (e) {
      setSyncError((e as Error)?.message ?? 'Error sincronizando entrenos');
    } finally {
      setSyncing(false);
    }
  };

  const isLoading = loading || loadingPlanned;
  const isEmpty = !isLoading && sessions.length === 0;

  return (
    <div className={styles.calendario}>
      <div className={styles.container}>

        {/* Back nav */}
        <div className={styles.diaBackNav}>
          <Link href="/calendario" className={styles.diaBackLink}>
            ← Volver al calendario
          </Link>
          <button
            type="button"
            className={styles.syncSmall}
            onClick={handleSync}
            disabled={syncing || !user?.id || hasStrava === false}
            title={hasStrava === false ? 'Conecta Strava para sincronizar' : 'Sincronizar entrenos'}
          >
            {syncing ? '↻ Sincronizando…' : '↻ Sincronizar'}
          </button>
        </div>

        {syncError && <div className={styles.syncError}>{syncError}</div>}

        {/* Month label */}
        <div className={`${styles.mes} ${syne.className}`}>
          {mes.charAt(0).toUpperCase() + mes.slice(1)}
        </div>

        {/* Week nav */}
        <WeekHeader
          diasConFechas={diasConFechas}
          diaSeleccionado={diaSeleccionado}
          semanaOffset={semanaOffset}
          onDiaClick={setDiaSeleccionado}
          onPrev={() => setSemanaOffset(o => o - 1)}
          onNext={() => setSemanaOffset(o => o + 1)}
        />

        {/* Day summary strip */}
        {!isLoading && <DaySummaryStrip done={doneTrainings} />}

        {/* Sessions */}
        <div className={styles.sessionsContainer}>
          {isLoading ? (
            <div className={styles.sessionEmpty} style={{ padding: '48px 0', textAlign: 'center' }}>
              <p>Cargando…</p>
            </div>
          ) : isEmpty ? (
            <div className={styles.diaEmptyDay}>
              <p className={styles.diaEmptyText}>No hay actividad registrada este día</p>
              <div className={styles.plannedPazeyCta}>
                <Link href="/chat" className={styles.chatButtonSm}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                  Planificar con Pazey
                </Link>
              </div>
            </div>
          ) : (
            sessions.map((s, i) => (
              <SessionBlock
                key={i}
                index={i}
                total={sessions.length}
                planned={s.planned}
                done={s.done}
                ftp={userFtp}
                userWeight={userWeight}
                onDeletePlanned={handleDeletePlanned}
              />
            ))
          )}
        </div>

      </div>
    </div>
  );
}

export default function Calendario() {
  return (
    <ProtectedRoute>
      <CalendarioContent />
    </ProtectedRoute>
  );
}
