'use client';
import React, { useEffect, useRef } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import UserAvatar from '@/components/UserAvatar';
import styles from '@/app/chat/chat.module.css';

type ActionVariant = 'primary' | 'ghost';

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  attachedWorkout?: { id: string; title: string; date: string };
  workoutPreview?: { date: string; title: string } | null;
  weekPlanPreview?: { days: { date: string; title: string; duration_min: number }[]; total_hours: number } | null;
  actionCard?: {
    title: string;
    workoutTitle: string;
    zone?: string;
    duration?: string;
    bullets: { label: string; detail?: string; sub?: string }[];
    actions?: { id: string; label: string; variant: ActionVariant }[];
  };
};

export default function ChatThread({
  messages,
  onAction,
  userAvatarUrl,
  userInitials,
  isThinking,
}: {
  messages: ChatMessage[];
  onAction: (actionId: string) => void;
  userAvatarUrl?: string | null;
  userInitials?: string;
  isThinking?: boolean;
}) {
  const messagesRef = useRef<HTMLDivElement>(null);
  const prevMessageCountRef = useRef(messages.length);

  const scrollToBottom = () => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    if (messages.length > prevMessageCountRef.current) {
      scrollToBottom();
    }
    prevMessageCountRef.current = messages.length;
  }, [messages.length]);

  useEffect(() => {
    if (isThinking) {
      scrollToBottom();
    }
  }, [isThinking]);

  return (
    <div className={styles.thread}>
      <div className={styles.threadHeader}>
        <div className={styles.brandInline} aria-hidden>
          <Image 
            src="/pazey-logo.png" 
            alt="Pazey" 
            width={40} 
            height={40}
            className={styles.brandLogo}
          />
        </div>
        <div className={styles.threadTitle}>Pazey</div>
      </div>

      <div className={styles.messages} ref={messagesRef}>
        {messages.map((m) => (
          <div key={m.id} className={m.role === 'user' ? styles.msgRowRight : styles.msgRowLeft}>
            {m.role === 'assistant' && (
              <div className={styles.avatar} aria-hidden>
                <Image 
                  src="/pazey-logo.png" 
                  alt="" 
                  width={38} 
                  height={38}
                  className={styles.avatarLogo}
                />
              </div>
            )}

            <div className={m.role === 'user' ? styles.bubbleUser : styles.bubbleAssistant}>
              {m.attachedWorkout && (
                <div className={styles.msgAttachedChip}>
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                    <line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>
                    <line x1="3" y1="10" x2="21" y2="10"/>
                  </svg>
                  <span>{m.attachedWorkout.title}</span>
                  <span style={{ opacity: 0.6 }}>· {m.attachedWorkout.date}</span>
                </div>
              )}
              <div className={styles.msgText} dangerouslySetInnerHTML={{ __html: markdownLite(m.content) }} />

              {m.workoutPreview && (
                <Link
                  href={`/calendario/dia?date=${m.workoutPreview.date}`}
                  className={styles.workoutPreviewCard}
                >
                  <div className={styles.workoutPreviewDot} />
                  <div className={styles.workoutPreviewBody}>
                    <span className={styles.workoutPreviewTitle}>{m.workoutPreview.title}</span>
                    <span className={styles.workoutPreviewDate}>{m.workoutPreview.date} · Ver en calendario →</span>
                  </div>
                </Link>
              )}

              {m.weekPlanPreview && (
                <div className={styles.weekPlanCard}>
                  <div className={styles.weekPlanHeader}>
                    <span className={styles.weekPlanTitle}>Plan semanal</span>
                    <span className={styles.weekPlanTotal}>{m.weekPlanPreview.total_hours}h totales</span>
                  </div>
                  <div className={styles.weekPlanRows}>
                    {m.weekPlanPreview.days.map((d) => (
                      <Link
                        key={d.date}
                        href={`/calendario/dia?date=${d.date}`}
                        className={styles.weekPlanRow}
                      >
                        <div className={styles.weekPlanRowLeft}>
                          <span className={styles.weekPlanDot} />
                          <span className={styles.weekPlanDayLabel}>{formatWeekDay(d.date)}</span>
                        </div>
                        <span className={styles.weekPlanRowTitle}>{d.title}</span>
                        <span className={styles.weekPlanRowDur}>{formatDur(d.duration_min)}</span>
                      </Link>
                    ))}
                  </div>
                  <Link href="/calendario" className={styles.weekPlanFooter}>
                    Ver en calendario →
                  </Link>
                </div>
              )}

              {m.actionCard && (
                <div className={styles.actionCard}>
                  <div className={styles.actionCardTop}>
                    <div className={styles.actionCardTitle}>{m.actionCard.title}</div>
                    {m.actionCard.duration ? <div className={styles.actionCardChip}>{m.actionCard.duration}</div> : null}
                  </div>

                  <div className={styles.actionCardWorkout}>{m.actionCard.workoutTitle}</div>
                  {m.actionCard.zone ? <div className={styles.actionCardZone}>{m.actionCard.zone}</div> : null}

                  <div className={styles.actionCardBullets}>
                    {m.actionCard.bullets.map((b, i) => (
                      <div key={i} className={styles.bulletRow}>
                        <span className={styles.bulletDot} aria-hidden>•</span>
                        <div className={styles.bulletText}>
                          <div className={styles.bulletMain}>
                            <span className={styles.bulletLabel}>{b.label}</span>
                            {b.detail ? <span className={styles.bulletDetail}>{b.detail}</span> : null}
                          </div>
                          {b.sub ? <div className={styles.bulletSub}>{b.sub}</div> : null}
                        </div>
                      </div>
                    ))}
                  </div>

                  {m.actionCard.actions?.length ? (
                    <div className={styles.actionRow}>
                      {m.actionCard.actions.map((a) => (
                        <button
                          key={a.id}
                          type="button"
                          onClick={() => onAction(a.id)}
                          className={a.variant === 'primary' ? styles.actionPrimary : styles.actionGhost}
                        >
                          {a.label}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              )}
            </div>

            {m.role === 'user' && (
              <div className={styles.avatarUser} aria-hidden>
                <UserAvatar
                  avatarUrl={userAvatarUrl}
                  initials={userInitials || '?'}
                  size={38}
                />
              </div>
            )}
          </div>
        ))}
        {isThinking && (
          <div className={styles.msgRowLeft}>
            <div className={styles.avatar} aria-hidden>
              <Image src="/pazey-logo.png" alt="" width={38} height={38} className={styles.avatarLogo} />
            </div>
            <div className={styles.typingBubble}>
              <div className={styles.typingDot} />
              <div className={styles.typingDot} />
              <div className={styles.typingDot} />
            </div>
          </div>
        )}
        <div style={{ display: 'none' }} />
      </div>
    </div>
  );
}

/** markdown ultra simple: **bold** + saltos de línea */
function markdownLite(text: string) {
  const safe = escapeHtml(text);
  return safe
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>');
}

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (c) => {
    switch (c) {
      case '&': return '&amp;';
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '"': return '&quot;';
      case "'": return '&#39;';
      default: return c;
    }
  });
}

const DAY_NAMES: Record<number, string> = { 1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue', 5: 'Vie', 6: 'Sáb', 0: 'Dom' };

function formatWeekDay(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return DAY_NAMES[d.getDay()] ?? iso;
}

function formatDur(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h > 0 && m > 0) return `${h}h ${m}min`;
  if (h > 0) return `${h}h`;
  return `${m}min`;
}
