'use client';
import React, { useState } from 'react';
import { Syne } from 'next/font/google';
import Image from 'next/image';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });

const StartPage: React.FC = () => {
  const [formData, setFormData] = useState({
    nombre: '',
    apellidos: '',
    email: '',
    telefono: '',
    peso: '',
    ftp: '',
  });

  const isFormComplete = Object.values(formData).every((value) => value.trim() !== '');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // authUrl dinámico
  const STRAVA_CLIENT_ID = process.env.NEXT_PUBLIC_STRAVA_CLIENT_ID!;
  const REDIRECT_URI = process.env.NEXT_PUBLIC_STRAVA_REDIRECT_URI!;
  const authUrl = [
    `https://www.strava.com/oauth/authorize`,
    `?client_id=${STRAVA_CLIENT_ID}`,
    `&response_type=code`,
    `&redirect_uri=${encodeURIComponent(REDIRECT_URI)}`,
    `&approval_prompt=auto`,
    `&scope=read,activity:read_all`,
  ].join('');

  const handleStravaConnect = () => {
    if (isFormComplete) {
      window.location.href = authUrl;
    }
  };

  return (
    <div className={`form-container ${syne.className}`}>
      <h2>Completa tus datos</h2>
      <form className="form">
        <input name="nombre" placeholder="Nombre" onChange={handleChange} />
        <input name="apellidos" placeholder="Apellidos" onChange={handleChange} />
        <input type="email" name="email" placeholder="Email" onChange={handleChange} />
        <input name="telefono" placeholder="Teléfono" onChange={handleChange} />
        <input name="peso" placeholder="Peso (kg)" type="number" onChange={handleChange} />
        <input name="ftp" placeholder="FTP (w)" type="number" onChange={handleChange} />

        <button
          type="button"
          disabled={!isFormComplete}
          className="strava-button"
          onClick={handleStravaConnect}
        >
          <Image
            src="/strava-connect-button-orange.svg"
            alt="Conectar con Strava"
            width={250}
            height={50}
            style={{ opacity: isFormComplete ? 1 : 0.5 }}
          />
        </button>
      </form>
    </div>
  );
};

export default StartPage;
