'use client';
import React, { useState } from 'react';
import styles from '@/app/chat/chat.module.css';

export type AttachedWorkout = {
  id: string;
  title: string;
  date: string;
};

export default function MessageComposer({
  onSend,
  placeholder,
  attachedWorkout,
  onClearAttached,
}: {
  onSend: (text: string) => void | Promise<void>;
  placeholder?: string;
  attachedWorkout?: AttachedWorkout | null;
  onClearAttached?: () => void;
}) {
  const [text, setText] = useState('');

  const submit = async () => {
    const t = text.trim();
    if (!t) return;
    setText('');
    await onSend(t);
  };

  return (
    <div className={styles.composerWrapper}>
      {/* Chip del entreno adjunto */}
      {attachedWorkout && (
        <div className={styles.attachedChip}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <span className={styles.attachedChipText}>{attachedWorkout.title}</span>
          <span className={styles.attachedChipDate}>{attachedWorkout.date}</span>
          {onClearAttached && (
            <button
              className={styles.attachedChipClose}
              onClick={onClearAttached}
              aria-label="Quitar entreno adjunto"
            >
              ×
            </button>
          )}
        </div>
      )}

      <div className={styles.composer}>
        <input
          className={styles.input}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={attachedWorkout ? `Dile a Pazey qué cambiar en "${attachedWorkout.title}"…` : (placeholder || 'Escribe…')}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <button type="button" className={styles.sendBtn} onClick={submit} aria-label="Enviar">
          ➤
        </button>
      </div>
    </div>
  );
}
