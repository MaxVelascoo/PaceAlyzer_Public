'use client';
import React, { useState } from 'react';
import { Syne } from 'next/font/google';
import { supabase } from '@/lib/supabaseClient';
import styles from './CalendarFAB.module.css';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });

type Mode = null | 'menu' | 'event' | 'metrics' | 'block';
type Props = { userId: string; onSaved?: () => void };

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// ── SVG icons ────────────────────────────────────────────────────────────────

function IconFlag() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>
    </svg>
  );
}

function IconActivity() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  );
}

function IconPlus() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
    </svg>
  );
}

function IconClose() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  );
}

function IconLock() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

export default function CalendarFAB({ userId, onSaved }: Props) {
  const [mode, setMode] = useState<Mode>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [eventDate, setEventDate] = useState(today());
  const [eventName, setEventName] = useState('');

  const [metDate, setMetDate] = useState(today());
  const [metWeight, setMetWeight] = useState('');
  const [metHR, setMetHR] = useState('');
  const [metHRV, setMetHRV] = useState('');
  const [metSleep, setMetSleep] = useState('');

  const [blockDate, setBlockDate] = useState(today());
  const [blockReason, setBlockReason] = useState('');

  const close = () => { setMode(null); setError(null); };

  const saveBlock = async () => {
    if (!blockDate) return;
    setSaving(true); setError(null);
    const { error: err } = await supabase
      .from('blocked_days')
      .upsert({ user_id: userId, date: blockDate, reason: blockReason.trim() || null }, { onConflict: 'user_id,date' });
    setSaving(false);
    if (err) { setError(err.message); return; }
    setBlockDate(today()); setBlockReason('');
    close(); onSaved?.();
  };

  const saveEvent = async () => {
    if (!eventName.trim() || !eventDate) return;
    setSaving(true); setError(null);
    const { error: err } = await supabase.from('events').insert({
      user_id: userId, date: eventDate, name: eventName.trim(),
    });
    setSaving(false);
    if (err) { setError(err.message); return; }
    setEventName(''); setEventDate(today());
    close(); onSaved?.();
  };

  const saveMetrics = async () => {
    if (!metDate) return;
    const payload: Record<string, unknown> = { user_id: userId, date: metDate };
    if (metWeight) payload.weight = parseFloat(metWeight);
    if (metHR)     payload.resting_hr = parseInt(metHR);
    if (metHRV)    payload.hrv = parseFloat(metHRV);
    if (metSleep)  payload.sleep_hours = parseFloat(metSleep);
    if (Object.keys(payload).length === 2) return;
    setSaving(true); setError(null);
    const { error: err } = await supabase
      .from('daily_metrics')
      .upsert(payload, { onConflict: 'user_id,date' });
    setSaving(false);
    if (err) { setError(err.message); return; }
    setMetWeight(''); setMetHR(''); setMetHRV(''); setMetSleep(''); setMetDate(today());
    close(); onSaved?.();
  };

  return (
    <>
      {mode && <div className={styles.backdrop} onClick={close} />}

      {/* ── Modal evento ── */}
      {mode === 'event' && (
        <div className={styles.modal}>
          <div className={styles.modalHeader}>
            <span className={`${styles.modalTitle} ${syne.className}`}>Nuevo evento</span>
            <button className={styles.modalClose} onClick={close} aria-label="Cerrar"><IconClose /></button>
          </div>
          <div className={styles.modalBody}>
            <label className={styles.field}>
              <span className={styles.fieldLabel}>Fecha</span>
              <input type="date" value={eventDate} onChange={e => setEventDate(e.target.value)} className={styles.input} />
            </label>
            <label className={styles.field}>
              <span className={styles.fieldLabel}>Nombre del evento</span>
              <input
                type="text"
                placeholder="Gran Fondo Mallorca"
                value={eventName}
                onChange={e => setEventName(e.target.value)}
                className={styles.input}
                onKeyDown={e => e.key === 'Enter' && saveEvent()}
                autoFocus
              />
            </label>
            {error && <p className={styles.error}>{error}</p>}
          </div>
          <div className={styles.modalFooter}>
            <button className={styles.btnGhost} onClick={close}>Cancelar</button>
            <button className={`${styles.btnPrimary} ${syne.className}`} onClick={saveEvent} disabled={saving || !eventName.trim()}>
              {saving ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </div>
      )}

      {/* ── Modal métricas ── */}
      {mode === 'metrics' && (
        <div className={styles.modal}>
          <div className={styles.modalHeader}>
            <span className={`${styles.modalTitle} ${syne.className}`}>Registrar métricas</span>
            <button className={styles.modalClose} onClick={close} aria-label="Cerrar"><IconClose /></button>
          </div>
          <div className={styles.modalBody}>
            <label className={styles.field}>
              <span className={styles.fieldLabel}>Fecha</span>
              <input type="date" value={metDate} onChange={e => setMetDate(e.target.value)} className={styles.input} />
            </label>
            <div className={styles.metricsGrid}>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Peso (kg)</span>
                <input type="number" step="0.1" placeholder="70.5" value={metWeight} onChange={e => setMetWeight(e.target.value)} className={styles.input} />
              </label>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>FC reposo (ppm)</span>
                <input type="number" placeholder="52" value={metHR} onChange={e => setMetHR(e.target.value)} className={styles.input} />
              </label>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>HRV (ms)</span>
                <input type="number" step="0.1" placeholder="68" value={metHRV} onChange={e => setMetHRV(e.target.value)} className={styles.input} />
              </label>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Horas de sueño</span>
                <input type="number" step="0.5" placeholder="7.5" value={metSleep} onChange={e => setMetSleep(e.target.value)} className={styles.input} />
              </label>
            </div>
            {error && <p className={styles.error}>{error}</p>}
          </div>
          <div className={styles.modalFooter}>
            <button className={styles.btnGhost} onClick={close}>Cancelar</button>
            <button className={`${styles.btnPrimary} ${syne.className}`} onClick={saveMetrics} disabled={saving}>
              {saving ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </div>
      )}

      {/* ── Modal bloquear día ── */}
      {mode === 'block' && (
        <div className={styles.modal}>
          <div className={styles.modalHeader}>
            <span className={`${styles.modalTitle} ${syne.className}`}>Bloquear día</span>
            <button className={styles.modalClose} onClick={close} aria-label="Cerrar"><IconClose /></button>
          </div>
          <div className={styles.modalBody}>
            <label className={styles.field}>
              <span className={styles.fieldLabel}>Fecha</span>
              <input type="date" value={blockDate} onChange={e => setBlockDate(e.target.value)} className={styles.input} />
            </label>
            <label className={styles.field}>
              <span className={styles.fieldLabel}>Motivo (opcional)</span>
              <input
                type="text"
                placeholder="Viaje, descanso obligatorio…"
                value={blockReason}
                onChange={e => setBlockReason(e.target.value)}
                className={styles.input}
                onKeyDown={e => e.key === 'Enter' && saveBlock()}
                autoFocus
              />
            </label>
            <p className={styles.blockHint}>
              Este día no se usará al planificar entrenamientos automáticamente.
            </p>
            {error && <p className={styles.error}>{error}</p>}
          </div>
          <div className={styles.modalFooter}>
            <button className={styles.btnGhost} onClick={close}>Cancelar</button>
            <button className={`${styles.btnPrimary} ${syne.className}`} onClick={saveBlock} disabled={saving || !blockDate}>
              {saving ? 'Guardando…' : 'Bloquear'}
            </button>
          </div>
        </div>
      )}

      {/* ── Menú ── */}
      {mode === 'menu' && (
        <div className={styles.menu}>
          <button className={styles.menuItem} onClick={() => setMode('event')}>
            <span className={styles.menuItemIcon} style={{ color: '#f59e0b' }}><IconFlag /></span>
            <span className={styles.menuItemLabel}>Añadir evento</span>
          </button>
          <button className={styles.menuItem} onClick={() => setMode('metrics')}>
            <span className={styles.menuItemIcon} style={{ color: '#22c55e' }}><IconActivity /></span>
            <span className={styles.menuItemLabel}>Registrar métricas</span>
          </button>
          <button className={styles.menuItem} onClick={() => setMode('block')}>
            <span className={styles.menuItemIcon} style={{ color: '#8b5cf6' }}><IconLock /></span>
            <span className={styles.menuItemLabel}>Bloquear día</span>
          </button>
        </div>
      )}

      {/* ── FAB ── */}
      <button
        className={`${styles.fab} ${mode === 'menu' ? styles.fabOpen : ''}`}
        onClick={() => setMode(m => m === 'menu' ? null : 'menu')}
        aria-label="Añadir"
      >
        <span className={styles.fabIcon}><IconPlus /></span>
      </button>
    </>
  );
}
