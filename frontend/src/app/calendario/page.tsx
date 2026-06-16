'use client';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';
import { useUser } from '@/context/userContext';
import { supabase } from '@/lib/supabaseClient';
import CalendarFAB from '@/components/CalendarFAB';
import styles from './calendario.module.css';

type PlannedDay = { id: string; date: string; title: string; duration_s: number };
type DoneDay = { date: string; name: string; distance: number | null; duration: number | null };
type EventDay = { id: string; date: string; name: string };
type MetricDay = { date: string; weight: number | null; resting_hr: number | null; hrv: number | null; sleep_hours: number | null };
type BlockedDay = { id: string; date: string; reason: string | null };
type WeekSummary = {
  iso_year: number; iso_week: number;
  completed_distance_km: number; completed_hours: number; completed_tss: number;
  ctl_end: number | null; atl_end: number | null; tsb_end: number | null;
};

type DragItem =
  | { type: 'planned'; id: string; date: string }
  | { type: 'event'; id: string; date: string }
  | { type: 'metric'; date: string }
  | { type: 'blocked'; id: string; date: string };

const DAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

function isoToday() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function fmtDuration(s: number) {
  const h = Math.floor(s / 3600); const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}
function fmtKm(m: number | null) { return m ? `${(m / 1000).toFixed(0)}km` : ''; }
function fmtHours(h: number) {
  const hh = Math.floor(h); const mm = Math.round((h - hh) * 60);
  return hh > 0 ? `${hh}h ${mm}m` : `${mm}m`;
}

export default function CalendarioPage() {
  const user = useUser()?.user;
  const router = useRouter();
  const today = isoToday();

  const [year, setYear] = useState(() => new Date().getFullYear());
  const [month, setMonth] = useState(() => new Date().getMonth());
  const [planned, setPlanned] = useState<PlannedDay[]>([]);
  const [done, setDone] = useState<DoneDay[]>([]);
  const [events, setEvents] = useState<EventDay[]>([]);
  const [metrics, setMetrics] = useState<MetricDay[]>([]);
  const [blockedDays, setBlockedDays] = useState<BlockedDay[]>([]);
  const [weekSummaries, setWeekSummaries] = useState<WeekSummary[]>([]);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  // ── DnD state ─────────────────────────────────────────────────────────────
  const [dragItem, setDragItem] = useState<DragItem | null>(null);
  const [dragOver, setDragOver] = useState<string | null>(null);
  const [trashActive, setTrashActive] = useState(false);
  const dragCounter = useRef<Record<string, number>>({});
  const trashCounter = useRef(0);

  const { totalDays, startOffset } = useMemo(() => {
    const first = new Date(year, month, 1);
    const total = new Date(year, month + 1, 0).getDate();
    const dow = first.getDay();
    return { totalDays: total, startOffset: dow === 0 ? 6 : dow - 1 };
  }, [year, month]);

  const monthStart = `${year}-${String(month + 1).padStart(2, '0')}-01`;
  const monthEnd = `${year}-${String(month + 1).padStart(2, '0')}-${String(totalDays).padStart(2, '0')}`;

  useEffect(() => {
    if (!user?.id) return;
    const load = async () => {
      const weekQueryStart = new Date(year, month, 1);
      weekQueryStart.setDate(weekQueryStart.getDate() - 6);
      const weekQueryStartStr = `${weekQueryStart.getFullYear()}-${String(weekQueryStart.getMonth() + 1).padStart(2, '0')}-${String(weekQueryStart.getDate()).padStart(2, '0')}`;

      const [plannedRes, doneRes, weekRes, eventsRes, metricsRes, blockedRes] = await Promise.all([
        supabase.from('planned_workouts').select('id, date, title, planned_duration_s')
          .eq('user_id', user.id).gte('date', monthStart).lte('date', monthEnd),
        supabase.from('trainings').select('date, name, distance, duration')
          .eq('user_id', user.id).gte('date', monthStart).lte('date', monthEnd),
        supabase.from('weekly_summaries')
          .select('iso_year, iso_week, completed_distance_km, completed_hours, completed_tss, ctl_end, atl_end, tsb_end')
          .eq('user_id', user.id)
          .gte('week_start_date', weekQueryStartStr).lte('week_start_date', monthEnd),
        supabase.from('events').select('id, date, name')
          .eq('user_id', user.id).gte('date', monthStart).lte('date', monthEnd),
        supabase.from('daily_metrics').select('date, weight, resting_hr, hrv, sleep_hours')
          .eq('user_id', user.id).gte('date', monthStart).lte('date', monthEnd),
        supabase.from('blocked_days').select('id, date, reason')
          .eq('user_id', user.id).gte('date', monthStart).lte('date', monthEnd),
      ]);
      setPlanned((plannedRes.data ?? []).map(r => ({ id: r.id, date: r.date, title: r.title, duration_s: r.planned_duration_s })));
      setDone((doneRes.data ?? []).map(r => ({ date: r.date, name: r.name ?? '', distance: r.distance, duration: r.duration })));
      setWeekSummaries(weekRes.data ?? []);
      setEvents((eventsRes.data ?? []).map(r => ({ id: r.id, date: r.date, name: r.name })));
      setMetrics((metricsRes.data ?? []).map(r => ({
        date: r.date,
        weight: r.weight ?? null,
        resting_hr: r.resting_hr ?? null,
        hrv: r.hrv ?? null,
        sleep_hours: r.sleep_hours ?? null,
      })));
      setBlockedDays((blockedRes.data ?? []).map(r => ({ id: r.id, date: r.date, reason: r.reason ?? null })));
    };
    load();
  }, [user?.id, monthStart, monthEnd, month, year, refetchTrigger]);

  // ── DnD handlers ──────────────────────────────────────────────────────────

  const handleDragStart = useCallback((e: React.DragEvent, item: DragItem) => {
    e.stopPropagation();
    setDragItem(item);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', JSON.stringify(item));
  }, []);

  const handleDragEnd = useCallback(() => {
    setDragItem(null);
    setDragOver(null);
    setTrashActive(false);
    trashCounter.current = 0;
    dragCounter.current = {};
  }, []);

  const handleDragEnter = useCallback((e: React.DragEvent, iso: string) => {
    e.preventDefault();
    dragCounter.current[iso] = (dragCounter.current[iso] ?? 0) + 1;
    setDragOver(iso);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent, iso: string) => {
    e.preventDefault();
    dragCounter.current[iso] = (dragCounter.current[iso] ?? 1) - 1;
    if (dragCounter.current[iso] <= 0) {
      dragCounter.current[iso] = 0;
      setDragOver(prev => prev === iso ? null : prev);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent, targetIso: string) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(null);
    dragCounter.current = {};

    let item: DragItem | null = dragItem;
    try { item = JSON.parse(e.dataTransfer.getData('text/plain')); } catch { /* use state */ }
    if (!item || item.date === targetIso) return;

    setDragItem(null);

    if (item.type === 'planned') {
      setPlanned(prev => prev.map(p => p.id === item.id ? { ...p, date: targetIso } : p));
      const { error } = await supabase.from('planned_workouts').update({ date: targetIso }).eq('id', item.id);
      if (error) { setRefetchTrigger(t => t + 1); console.error(error.message); }

    } else if (item.type === 'event') {
      setEvents(prev => prev.map(ev => ev.id === item.id ? { ...ev, date: targetIso } : ev));
      const { error } = await supabase.from('events').update({ date: targetIso }).eq('id', item.id);
      if (error) { setRefetchTrigger(t => t + 1); console.error(error.message); }

    } else if (item.type === 'metric') {
      // Las métricas usan date como PK compuesta (user_id, date) — hay que mover los datos
      const met = metricsByDateRef.current[item.date];
      if (!met || !user?.id) return;
      setMetrics(prev => prev.map(m => m.date === item.date ? { ...m, date: targetIso } : m));
      // Upsert en la nueva fecha y borrar la antigua
      await supabase.from('daily_metrics').upsert(
        { user_id: user.id, date: targetIso, weight: met.weight, resting_hr: met.resting_hr, hrv: met.hrv, sleep_hours: met.sleep_hours },
        { onConflict: 'user_id,date' }
      );
      await supabase.from('daily_metrics').delete().eq('user_id', user.id).eq('date', item.date);

    } else if (item.type === 'blocked') {
      setBlockedDays(prev => prev.map(b => b.id === item.id ? { ...b, date: targetIso } : b));
      const { error } = await supabase.from('blocked_days').update({ date: targetIso }).eq('id', item.id);
      if (error) { setRefetchTrigger(t => t + 1); console.error(error.message); }
    }
  }, [dragItem, user?.id]);

  const handleDropTrash = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setTrashActive(false);
    trashCounter.current = 0;
    setDragOver(null);
    dragCounter.current = {};

    let item: DragItem | null = dragItem;
    try { item = JSON.parse(e.dataTransfer.getData('text/plain')); } catch { /* use state */ }
    if (!item || !user?.id) return;
    setDragItem(null);

    if (item.type === 'planned') {
      setPlanned(prev => prev.filter(p => p.id !== item.id));
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';
      const res = await fetch(`${backendUrl}/api/planned-workouts/${item.id}?user_id=${user.id}`, { method: 'DELETE' });
      if (!res.ok) setRefetchTrigger(t => t + 1);

    } else if (item.type === 'event') {
      setEvents(prev => prev.filter(ev => ev.id !== item.id));
      const { error } = await supabase.from('events').delete().eq('id', item.id).eq('user_id', user.id);
      if (error) setRefetchTrigger(t => t + 1);

    } else if (item.type === 'metric') {
      setMetrics(prev => prev.filter(m => m.date !== item.date));
      await supabase.from('daily_metrics').delete().eq('user_id', user.id).eq('date', item.date);

    } else if (item.type === 'blocked') {
      setBlockedDays(prev => prev.filter(b => b.id !== item.id));
      const { error } = await supabase.from('blocked_days').delete().eq('id', item.id).eq('user_id', user.id);
      if (error) setRefetchTrigger(t => t + 1);
    }
  }, [dragItem, user?.id]);

  // ── Derived maps ──────────────────────────────────────────────────────────

  const plannedByDate = useMemo(() => {
    const m: Record<string, PlannedDay[]> = {};
    planned.forEach(p => { (m[p.date] ||= []).push(p); });
    return m;
  }, [planned]);

  const doneByDate = useMemo(() => {
    const m: Record<string, DoneDay[]> = {};
    done.forEach(d => { (m[d.date] ||= []).push(d); });
    return m;
  }, [done]);

  const eventsByDate = useMemo(() => {
    const m: Record<string, EventDay[]> = {};
    events.forEach(e => { (m[e.date] ||= []).push(e); });
    return m;
  }, [events]);

  const metricsByDate = useMemo(() => {
    const m: Record<string, MetricDay> = {};
    metrics.forEach(met => { m[met.date] = met; });
    return m;
  }, [metrics]);

  const metricsByDateRef = useRef<Record<string, MetricDay>>({});
  useEffect(() => { metricsByDateRef.current = metricsByDate; }, [metricsByDate]);

  const blockedByDate = useMemo(() => {
    const m: Record<string, BlockedDay> = {};
    blockedDays.forEach(b => { m[b.date] = b; });
    return m;
  }, [blockedDays]);

  const summaryByWeek = useMemo(() => {
    const m: Record<string, WeekSummary> = {};
    weekSummaries.forEach(w => { m[`${w.iso_year}-${w.iso_week}`] = w; });
    return m;
  }, [weekSummaries]);

  const monthName = new Date(year, month, 1).toLocaleString('es-ES', { month: 'long', year: 'numeric' });
  const prevMonth = () => { if (month === 0) { setMonth(11); setYear(y => y - 1); } else setMonth(m => m - 1); };
  const nextMonth = () => { if (month === 11) { setMonth(0); setYear(y => y + 1); } else setMonth(m => m + 1); };

  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  const handleSync = async () => {
    if (!user?.id || syncing) return;
    setSyncError(null);
    setSyncing(true);
    try {
      const pad = (n: number) => String(n).padStart(2, '0');
      const startDate = `${year}-${pad(month + 1)}-01`;
      const endDate = `${year}-${pad(month + 1)}-${pad(totalDays)}`;
      const res = await fetch('/api/strava/sync-trainings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: user.id, startDate, endDate }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error || 'Error sincronizando');
      // Refetch data
      setRefetchTrigger(t => t + 1);
    } catch (e) {
      setSyncError((e as Error).message);
    } finally {
      setSyncing(false);
    }
  };

  const weeks = useMemo(() => {
    const cells: (number | null)[] = Array(startOffset).fill(null);
    for (let d = 1; d <= totalDays; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);
    const rows: (number | null)[][] = [];
    for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7));
    return rows;
  }, [startOffset, totalDays]);

  const handleDayClick = (day: number) => {
    if (dragItem) return;
    const iso = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    router.push(`/calendario/dia?date=${iso}`);
  };

  const getIsoWeek = (day: number) => {
    const d = new Date(year, month, day);
    const jan4 = new Date(d.getFullYear(), 0, 4);
    const startOfWeek1 = new Date(jan4);
    startOfWeek1.setDate(jan4.getDate() - (jan4.getDay() || 7) + 1);
    const weekNum = Math.floor((d.getTime() - startOfWeek1.getTime()) / (7 * 86400000)) + 1;
    return `${d.getFullYear()}-${weekNum}`;
  };

  return (
    <ProtectedRoute>
      <div className={styles.calPage}>
        <div className={styles.calContainer}>

          <div className={styles.calHeader}>
            <div />
            <div className={styles.calHeaderCenter}>
              <button className={styles.calNavBtn} onClick={prevMonth}>‹</button>
              <h1 className={styles.calTitle}>{monthName.charAt(0).toUpperCase() + monthName.slice(1)}</h1>
              <button className={styles.calNavBtn} onClick={nextMonth}>›</button>
            </div>
            <div className={styles.calHeaderRight}>
              <button
                type="button"
                className={styles.syncSmall}
                onClick={handleSync}
                disabled={syncing || !user?.id}
              >
                {syncing ? '↻ Sincronizando…' : '↻ Sincronizar'}
              </button>
            </div>
          </div>
          {syncError && <div className={styles.syncError}>{syncError}</div>}

          <div className={styles.calWeekRow}>
            {DAYS.map(d => <div key={d} className={styles.calWeekLabel}>{d}</div>)}
            <div className={styles.calWeekLabel} style={{ textAlign: 'center' }}>Resumen</div>
          </div>

          {weeks.map((row, rowIdx) => {
            const lastReal = [...row].reverse().find(d => d !== null);
            const weekKey = lastReal ? getIsoWeek(lastReal) : null;
            const summary = weekKey ? summaryByWeek[weekKey] : null;

            return (
              <div key={rowIdx} className={styles.calRow}>
                {row.map((day, colIdx) => {
                  if (!day) return <div key={`e-${rowIdx}-${colIdx}`} className={styles.calCellEmpty} />;
                  const iso = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                  const isToday = iso === today;
                  const isDropTarget = dragOver === iso;
                  const pList = plannedByDate[iso] ?? [];
                  const dList = doneByDate[iso] ?? [];
                  const eList = eventsByDate[iso] ?? [];
                  const met = metricsByDate[iso] ?? null;
                  const blocked = blockedByDate[iso] ?? null;

                  return (
                    <div
                      key={iso}
                      className={`${styles.calCell} ${isToday ? styles.calCellToday : ''} ${isDropTarget ? styles.calCellDropTarget : ''} ${blocked ? styles.calCellBlocked : ''}`}
                      onClick={() => handleDayClick(day)}
                      onDragEnter={(e) => handleDragEnter(e, iso)}
                      onDragLeave={(e) => handleDragLeave(e, iso)}
                      onDragOver={handleDragOver}
                      onDrop={(e) => handleDrop(e, iso)}
                    >
                      <span className={styles.calDayNum}>{day}</span>

                      {pList.map((p) => (
                        <div
                          key={p.id}
                          className={`${styles.calPill} ${dragItem?.type === 'planned' && dragItem.id === p.id ? styles.calPillDragging : ''}`}
                          title={p.title}
                          draggable
                          onDragStart={(e) => handleDragStart(e, { type: 'planned', id: p.id, date: p.date })}
                          onDragEnd={handleDragEnd}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4, width: '100%' }}>
                            <span className={styles.calPillDot} style={{ background: '#6366f1', flexShrink: 0 }} />
                            <span className={styles.calPillText}>{p.title}</span>
                          </div>
                          <span className={styles.calPillMeta}>{fmtDuration(p.duration_s)}</span>
                        </div>
                      ))}

                      {dList.map((d, j) => (
                        <div key={`d-${j}`} className={`${styles.calPill} ${styles.calPillDone}`} title={d.name}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4, width: '100%' }}>
                            <span className={styles.calPillDot} style={{ background: '#FC4C02', flexShrink: 0 }} />
                            <span className={styles.calPillText}>{d.name || 'Entreno'}</span>
                          </div>
                          <span className={styles.calPillMeta}>{fmtKm(d.distance)}{d.duration ? ` · ${fmtDuration(d.duration)}` : ''}</span>
                        </div>
                      ))}

                      {eList.map((ev) => (
                        <div
                          key={ev.id}
                          className={`${styles.calPill} ${styles.calPillEvent} ${dragItem?.type === 'event' && dragItem.id === ev.id ? styles.calPillDragging : ''}`}
                          title={ev.name}
                          draggable
                          onDragStart={(e) => handleDragStart(e, { type: 'event', id: ev.id, date: ev.date })}
                          onDragEnd={handleDragEnd}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4, width: '100%' }}>
                            <span className={styles.calPillDot} style={{ background: '#f59e0b', flexShrink: 0 }} />
                            <span className={styles.calPillText}>{ev.name}</span>
                          </div>
                        </div>
                      ))}

                      {met && (met.weight || met.resting_hr || met.hrv || met.sleep_hours) && (
                        <div
                          className={`${styles.calPill} ${styles.calPillMetric} ${dragItem?.type === 'metric' && dragItem.date === iso ? styles.calPillDragging : ''}`}
                          title="Métricas del día"
                          draggable
                          onDragStart={(e) => handleDragStart(e, { type: 'metric', date: iso })}
                          onDragEnd={handleDragEnd}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4, width: '100%' }}>
                            <span className={styles.calPillDot} style={{ background: '#22c55e', flexShrink: 0 }} />
                            <span className={styles.calPillText}>
                              {[
                                met.weight ? `${met.weight}kg` : null,
                                met.resting_hr ? `${met.resting_hr}bpm` : null,
                                met.sleep_hours ? `${met.sleep_hours}h` : null,
                              ].filter(Boolean).join(' · ')}
                            </span>
                          </div>
                        </div>
                      )}

                      {blocked && (
                        <div
                          className={`${styles.calPill} ${styles.calPillBlocked} ${dragItem?.type === 'blocked' && dragItem.id === blocked.id ? styles.calPillDragging : ''}`}
                          title={blocked.reason ?? 'Día bloqueado'}
                          draggable
                          onDragStart={(e) => handleDragStart(e, { type: 'blocked', id: blocked.id, date: blocked.date })}
                          onDragEnd={handleDragEnd}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4, width: '100%' }}>
                            <span className={styles.calPillDot} style={{ background: '#ef4444', flexShrink: 0 }} />
                            <span className={styles.calPillText}>{blocked.reason ?? 'Bloqueado'}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Columna resumen semanal */}
                {(() => {
                  const lastRealDay = [...row].reverse().find(d => d !== null);
                  if (!lastRealDay) return <div className={styles.calWeekSummary} />;
                  const weekEndIso = `${year}-${String(month + 1).padStart(2, '0')}-${String(lastRealDay).padStart(2, '0')}`;
                  const weekHasStarted = weekEndIso <= today;
                  return (
                    <div className={styles.calWeekSummary}>
                      {summary && weekHasStarted ? (
                        <>
                          <div className={styles.calWeekRow1}>
                            <div className={styles.calWeekStat}>
                              <span className={styles.calWeekStatVal}>{Math.round(summary.completed_distance_km)}</span>
                              <span className={styles.calWeekStatLbl}>km</span>
                            </div>
                            <div className={styles.calWeekStat}>
                              <span className={styles.calWeekStatVal}>{fmtHours(summary.completed_hours)}</span>
                            </div>
                            <div className={styles.calWeekStat}>
                              <span className={styles.calWeekStatVal}>{Math.round(summary.completed_tss)}</span>
                              <span className={styles.calWeekStatLbl}>TSS</span>
                            </div>
                          </div>
                          <div className={styles.calWeekDivider} />
                          <div className={styles.calWeekRow2}>
                            <div className={styles.calWeekStat}>
                              <span className={styles.calWeekStatVal} style={{ color: '#4a90d9' }}>{summary.ctl_end?.toFixed(0) ?? '—'}</span>
                              <span className={styles.calWeekStatLbl}>CTL</span>
                            </div>
                            <div className={styles.calWeekStat}>
                              <span className={styles.calWeekStatVal} style={{ color: '#e05c5c' }}>{summary.atl_end?.toFixed(0) ?? '—'}</span>
                              <span className={styles.calWeekStatLbl}>ATL</span>
                            </div>
                            <div className={styles.calWeekStat}>
                              <span className={styles.calWeekStatVal} style={{ color: '#5cb85c' }}>{summary.tsb_end != null ? (summary.tsb_end > 0 ? '+' : '') + summary.tsb_end.toFixed(0) : '—'}</span>
                              <span className={styles.calWeekStatLbl}>TSB</span>
                            </div>
                          </div>
                        </>
                      ) : (
                        <span className={styles.calWeekEmpty}>—</span>
                      )}
                    </div>
                  );
                })()}
              </div>
            );
          })}

        </div>
      </div>
      {user?.id && (
        <CalendarFAB
          userId={user.id}
          onSaved={() => setRefetchTrigger(t => t + 1)}
        />
      )}

      {/* Papelera — aparece al arrastrar cualquier pastilla */}
      {dragItem && (
        <div
          className={`${styles.trashZone} ${trashActive ? styles.trashZoneActive : ''}`}
          onDragEnter={(e) => { e.preventDefault(); trashCounter.current += 1; setTrashActive(true); }}
          onDragLeave={() => { trashCounter.current -= 1; if (trashCounter.current <= 0) { trashCounter.current = 0; setTrashActive(false); } }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDropTrash}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
            <path d="M10 11v6M14 11v6" />
            <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
          </svg>
          <span>{trashActive ? 'Suelta para borrar' : 'Arrastra aquí para borrar'}</span>
        </div>
      )}
    </ProtectedRoute>
  );
}
