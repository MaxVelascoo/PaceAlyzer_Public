'use client';
import { useEffect } from 'react';
import { useUser } from '@/context/userContext';
import { useRouter } from 'next/navigation';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const userContext = useUser();
  const router = useRouter();

  // Si aún no se ha cargado el contexto, devolvemos null *después* del hook
  const user = userContext?.user;

  useEffect(() => {
    if (user === null) {
      router.replace('/start');
    }
  }, [user, router]);

  // Esperar a que se cargue el contexto (user === undefined)
  if (user === undefined || user === null) return null;

  return <>{children}</>;
}
