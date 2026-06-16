import { useEffect, useRef } from 'react';

const SYNC_TTL_MS = 30 * 60 * 1000; // 30 minutos
const STORAGE_KEY = (userId: string) => `lastAutoSync_${userId}`;

/**
 * Dispara un sync silencioso de Strava (últimos 7 días) si han pasado
 * más de 30 minutos desde el último auto-sync del usuario.
 * No bloquea la UI ni muestra errores al usuario.
 */
export function useAutoSync(userId: string | undefined) {
  const syncedRef = useRef(false);

  useEffect(() => {
    if (!userId || syncedRef.current) return;

    const key = STORAGE_KEY(userId);
    const lastSync = localStorage.getItem(key);
    const now = Date.now();

    if (lastSync && now - parseInt(lastSync, 10) < SYNC_TTL_MS) {
      // Sync reciente, no hace falta
      return;
    }

    syncedRef.current = true;

    // Calcular rango: últimos 7 días
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 7);
    const fmt = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

    fetch('/api/strava/sync-trainings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        userId,
        startDate: fmt(start),
        endDate: fmt(end),
      }),
    })
      .then((res) => {
        if (res.ok) {
          localStorage.setItem(key, String(now));
        }
      })
      .catch(() => {
        // Silencioso — no interrumpir la UX
        syncedRef.current = false;
      });
  }, [userId]);
}
