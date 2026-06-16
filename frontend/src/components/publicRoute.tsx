'use client';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useUser } from '@/context/userContext';

export default function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user } = useUser() || {};
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.replace('/calendario');
    }
  }, [user, router]);

  if (user) return null;

  return <>{children}</>;
}
