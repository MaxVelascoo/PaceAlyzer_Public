'use client';
import React from 'react';
import { Syne, Inter } from 'next/font/google';
import Image from 'next/image';
import { useUser } from '@/context/userContext';
import ProtectedRoute from '@/components/ProtectedRoute';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });
const inter = Inter({ subsets: ['latin'], weight: ['400'] });

function ConnectStravaPageContent() {
  const userContext = useUser(); // Accedemos al usuario actual
  const user = userContext?.user;

  const STRAVA_CLIENT_ID = process.env.NEXT_PUBLIC_STRAVA_CLIENT_ID!;
  const REDIRECT_URI = process.env.NEXT_PUBLIC_STRAVA_REDIRECT_URI!;

  const authUrl = [
    `https://www.strava.com/oauth/authorize`,
    `?client_id=${STRAVA_CLIENT_ID}`,
    `&response_type=code`,
    `&redirect_uri=${encodeURIComponent(REDIRECT_URI)}`,
    `&approval_prompt=auto`,
    `&scope=read,activity:read_all`,
    `&state=${user?.id}` // Aquí se añade el user.id como estado
  ].join('');

  return (
    <div className={`form-container ${syne.className}`}>
      <h2 className={syne.className}>Conectar con Strava</h2>
      <p className={inter.className} style={{ maxWidth: '500px', textAlign: 'center', marginBottom: '30px' }}>
        ¡Ya casi está! Solo tienes que conectar tu cuenta de Strava para que podamos importar tus entrenamientos automáticamente.
      </p>
      <a
        href={authUrl}
        className="strava-button"
        style={{ border: 'none', background: 'none' }}
      >
        <Image
          src="/strava-connect-button-orange.svg"
          alt="Conectar con Strava"
          width={250}
          height={50}
        />
      </a>
    </div>
  );
}

export default function ConnectStravaPage() {
  return (
    <ProtectedRoute>
      <ConnectStravaPageContent />
    </ProtectedRoute>
  );
}
