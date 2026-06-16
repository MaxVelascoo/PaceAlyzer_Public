'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';
import styles from './chat.module.css';
import { useUser } from '@/context/userContext';
import { usePlannedWorkout } from '@/hooks/usePlannedWorkout';
import { supabase } from '@/lib/supabaseClient';

import ChatSidebar, { WeekDay } from '@/components/chat/ChatSideBar';
import ChatThread, { ChatMessage } from '@/components/chat/ChatThread';
import MessageComposer, { AttachedWorkout } from '@/components/chat/MessageComposer';
import { useAutoSync } from '@/hooks/useAutoSync';


function isoTodayLocal() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export default function ChatPage() {
  const user = useUser()?.user;
  const searchParams = useSearchParams();
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    return searchParams?.get('date') ?? isoTodayLocal();
  });
  const [userAvatarUrl, setUserAvatarUrl] = useState<string | null>(null);
  const [userInitials, setUserInitials] = useState<string>('');

  // Auto-sync silencioso al abrir el chat (TTL 30 min)
  useAutoSync(user?.id);

  // Obtener entreno planificado del día seleccionado
  const { loading: loadingPlanned, workout: plannedWorkout } = usePlannedWorkout(user?.id, selectedDate);

  // Workout adjunto — se inicializa desde URL params si vienen de PlannedWorkoutCard
  const [attachedWorkout, setAttachedWorkout] = useState<AttachedWorkout | null>(null);

  // Cuando carga el workout referenciado en la URL, lo adjunta automáticamente
  const urlWorkoutId = searchParams?.get('workout_id');
  useEffect(() => {
    if (!urlWorkoutId || !plannedWorkout) return;
    if (plannedWorkout.id === urlWorkoutId) {
      setAttachedWorkout({
        id: plannedWorkout.id,
        title: plannedWorkout.title,
        date: plannedWorkout.date,
      });
      // Cambiar la fecha seleccionada al día del workout
      setSelectedDate(plannedWorkout.date);
    }
  }, [urlWorkoutId, plannedWorkout]);

  // Obtener avatar del usuario
  useEffect(() => {
    const fetchUserAvatar = async () => {
      if (!user) return;

      try {
        const { data, error } = await supabase
          .from('users')
          .select('avatar_url, firstname, lastname')
          .eq('id', user.id)
          .single();

        if (error) {
          console.error('Error fetching user avatar:', error);
          return;
        }

        // Iniciales como fallback
        const first = (data?.firstname?.[0] ?? '').toUpperCase();
        const last = (data?.lastname?.[0] ?? '').toUpperCase();
        setUserInitials(`${first}${last}` || '?');

        if (data?.avatar_url) {
          const { data: signedData, error: signedError } = await supabase.storage
            .from('avatars')
            .createSignedUrl(data.avatar_url, 60 * 60);

          if (signedError) {
            console.error('Error generating signed URL:', signedError);
            return;
          }

          setUserAvatarUrl(signedData?.signedUrl ?? null);
        }
      } catch (err) {
        console.error('Exception fetching user avatar:', err);
      }
    };

    fetchUserAvatar();
  }, [user]);

  const weekDays: WeekDay[] = useMemo(() => {
    const today = new Date();
    const dayOfWeek = today.getDay(); // 0=dom, 1=lun...
    const monday = new Date(today);
    monday.setDate(today.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));

    const labels = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
    return labels.map((label, i) => {
      const d = new Date(monday);
      d.setDate(monday.getDate() + i);
      const date = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
      return { key: label, label, date };
    });
  }, []);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);

  // Cargar historial de la sesión activa al montar
  useEffect(() => {
    if (!user?.id) return;
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';
    fetch(`${backendUrl}/api/chat/history?user_id=${user.id}`)
      .then(r => r.json())
      .then(data => {
        if (data.messages?.length) {
          setMessages(data.messages.map((m: {
            role: string;
            content: string;
            created_at: string;
            metadata?: {
              workout_preview?: { date: string; title: string };
              week_plan_preview?: { days: { date: string; title: string; duration_min: number }[]; total_hours: number };
            };
          }) => {
            // Extraer el prefijo [Entreno adjunto: "título" del fecha] si existe
            let content = m.content;
            let attachedWorkout: { id: string; title: string; date: string } | undefined;
            const attachedMatch = content.match(/^\[Entreno adjunto: "(.+)" del (\d{4}-\d{2}-\d{2})\]\n?/);
            if (attachedMatch) {
              attachedWorkout = { id: '', title: attachedMatch[1], date: attachedMatch[2] };
              content = content.replace(attachedMatch[0], '').trim();
            }
            return {
              id: `hist_${crypto.randomUUID()}`,
              role: m.role as 'user' | 'assistant',
              content,
              createdAt: m.created_at,
              attachedWorkout,
              workoutPreview: m.metadata?.workout_preview ?? null,
              weekPlanPreview: m.metadata?.week_plan_preview ?? null,
            };
          }));
        }
      })
      .catch(() => {});
  }, [user?.id]);

  const handleSend = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || !user?.id) return;

    // Si hay workout adjunto, añadir contexto explícito al mensaje
    const messageWithContext = attachedWorkout
      ? `[Entreno adjunto: "${attachedWorkout.title}" del ${attachedWorkout.date}]\n${trimmed}`
      : trimmed;

    setMessages((prev) => [
      ...prev,
      {
        id: `u_${crypto.randomUUID()}`,
        role: 'user',
        content: trimmed, // mostramos el texto limpio en el chat
        createdAt: new Date().toISOString(),
        attachedWorkout: attachedWorkout ?? undefined,
      },
    ]);

    // Limpiar el adjunto tras enviar
    setAttachedWorkout(null);

    setIsThinking(true);
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';

    try {
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          message: messageWithContext, // enviamos el mensaje con contexto al backend
          date: attachedWorkout?.date ?? selectedDate,
        }),
      });

      const data = await res.json();
      const reply: string = res.ok
        ? data.reply
        : `Error del servidor: ${data.detail ?? res.statusText}`;

      const workoutPreview =
        res.ok && data.action_taken === 'workout_modified' && data.workout_date && data.workout_title
          ? { date: data.workout_date, title: data.workout_title }
          : null;

      const weekPlanPreview = (() => {
        if (!res.ok || data.action_taken !== 'week_plan_created' || !data.week_plan?.length) return null;
        const days = data.week_plan as { date: string; title: string; duration_min: number }[];
        const total_min = days.reduce((acc: number, d: { duration_min: number }) => acc + d.duration_min, 0);
        const total_hours = Math.round(total_min / 60 * 10) / 10;
        return { days, total_hours };
      })();

      setMessages((prev) => [
        ...prev,
        {
          id: `a_${crypto.randomUUID()}`,
          role: 'assistant',
          content: reply,
          createdAt: new Date().toISOString(),
          workoutPreview,
          weekPlanPreview,
        },
      ]);
    } catch (err) {
      console.error('Backend connection error:', err);
      setMessages((prev) => [
        ...prev,
        { id: `a_${crypto.randomUUID()}`, role: 'assistant', content: 'No pude conectar con el servidor.', createdAt: new Date().toISOString() },
      ]);
    } finally {
      setIsThinking(false);
    }
  };

  const handleAction = async (actionId: string) => {
    if (actionId.startsWith('apply')) {
      setMessages((prev) => [
        ...prev,
        {
          id: `a_ok_${crypto.randomUUID()}`,
          role: 'assistant',
          content: 'Cambios aplicados. Ya lo verás reflejado en el calendario.',
          createdAt: new Date().toISOString(),
        },
      ]);
      return;
    }
    if (actionId.startsWith('undo')) {
      setMessages((prev) => [
        ...prev,
        {
          id: `a_undo_${crypto.randomUUID()}`,
          role: 'assistant',
          content: '↩️ He deshecho la propuesta. Dime qué prefieres hacer.',
          createdAt: new Date().toISOString(),
        },
      ]);
    }
  };

  return (
    <ProtectedRoute>
      <div className={styles.page}>
        <div className={styles.shell}>
          <ChatSidebar
            selectedDate={selectedDate}
            onSelectDate={setSelectedDate}
            weekDays={weekDays}
            plannedWorkout={plannedWorkout}
            loading={loadingPlanned}
          />

          <div className={styles.threadCol}>
            <ChatThread messages={messages} onAction={handleAction} userAvatarUrl={userAvatarUrl} userInitials={userInitials} isThinking={isThinking} />
            <MessageComposer
              onSend={handleSend}
              placeholder="Escribe tu petición…"
              attachedWorkout={attachedWorkout}
              onClearAttached={() => setAttachedWorkout(null)}
            />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
