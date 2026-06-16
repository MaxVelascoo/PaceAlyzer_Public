'use client';
import React, { useState } from 'react';
import { Syne, Inter } from 'next/font/google';
import { supabase } from '@/lib/supabaseClient';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });
const inter = Inter({ subsets: ['latin'], weight: ['400'] });

export default function RegisterPage() {
  const [form, setForm] = useState({
    firstname: '', lastname: '', email: '', telef: '', weight: '', ftp: '', password: '', birthdate: '', max_heartrate: '',
  });
  const router = useRouter();
  const isValid = Object.values(form).every(v => v.trim());

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleRegister = async () => {
    const { data, error: signError } = await supabase.auth.signUp({
      email: form.email,
      password: form.password,
    });
    if (signError) return alert('Error al registrar: ' + signError.message);

    if (!data.user || !data.user.id) {
      return alert('Error: No se pudo obtener el ID del usuario');
    }
    const userId = data.user.id;

    const { error: insertError } = await supabase.from('users').insert({
      id: userId,
      email: form.email,
      firstname: form.firstname,
      lastname: form.lastname,
      telef: form.telef,
      weight: form.weight,
      ftp: form.ftp,
      birthdate: form.birthdate,
      max_heartrate: form.max_heartrate,
    });
    if (insertError) return alert('Fallo al guardar datos: ' + insertError.message);

    router.push('/connect-strava');
  };

  return (
    <div className={`form-container ${syne.className}`}>
      <h2>Regístrate</h2>
      <form className="form">
        {[
          { name: 'firstname', label: 'Nombre' },
          { name: 'lastname', label: 'Apellidos' },
          { name: 'email', label: 'Email', type: 'email' },
          { name: 'telef', label: 'Teléfono' },
          { name: 'weight', label: 'Peso (kg)', type: 'number' },
          { name: 'ftp', label: 'FTP (W)', type: 'number' },
          { name: 'birthdate', label: 'Fecha de nacimiento', type: 'date' },
          { name: 'max_heartrate', label: 'FC máxima (ppm)', type: 'number' },
          { name: 'password', label: 'Contraseña', type: 'password' },
        ].map(({ name, label, type }) => (
          <input
            key={name}
            name={name}
            type={type || 'text'}
            placeholder={label}
            onChange={handleChange}
            className={inter.className}
          />
        ))}
        <button 
          type="button" 
          disabled={!isValid} 
          onClick={handleRegister} 
          className="form-button"
        >
          Registrarse
        </button>
      </form>
      <p className={`${syne.className} login-register-hint`}>
        ¿Ya tienes cuenta?{' '}
        <Link href="/start/login" className="register-link">
          Inicia sesión
        </Link>
      </p>
    </div>
  );
}
