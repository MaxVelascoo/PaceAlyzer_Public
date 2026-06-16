'use client';
import React from 'react';
import { useRouter } from 'next/navigation';
import { Syne } from 'next/font/google';
import PublicRoute from '@/components/publicRoute'; // asegúrate de que la ruta es correcta

const syne = Syne({ subsets: ['latin'], weight: ['700'] });

function StartPageContent() {
  const router = useRouter();

  return (
    <div className={`form-container ${syne.className}`}>
      <h2 style={{ marginBottom: '30px', fontSize: '28px' }}>¿Qué deseas hacer?</h2>
      <div className="start-buttons">
        <button onClick={() => router.push('/start/login')} className="choice-button spaced-button">
          Iniciar sesión
        </button>
        <button onClick={() => router.push('/start/register')} className="choice-button spaced-button">
          Registrarse
        </button>
      </div>
    </div>
  );
}

export default function StartPage() {
  return (
    <PublicRoute>
      <StartPageContent />
    </PublicRoute>
  );
}
