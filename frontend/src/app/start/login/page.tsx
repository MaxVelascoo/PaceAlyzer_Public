'use client';
import React, { useState } from 'react';
import { Syne, Inter } from 'next/font/google';
import { supabase } from '@/lib/supabaseClient';
import { useRouter } from 'next/navigation';
import { useToast } from '@/components/toastProvider/ToastProvider';
import Link from 'next/link';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });
const inter = Inter({ subsets: ['latin'], weight: ['400'] });


export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: '', password: '' });
  const isReady = form.email.trim() !== '' && form.password.trim() !== '';
  const toast = useToast();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleLogin = async () => {
    console.log('Intentando login con:', form.email);
    
    const { data, error } = await supabase.auth.signInWithPassword({
      email: form.email,
      password: form.password,
    });

    console.log('Respuesta de Supabase:', { data, error });

    if (error) {
      console.error('Error de login:', error);
      return toast('Error al iniciar sesión: ' + error.message,'error');
    }

    // Forzar recarga del usuario
    const sessionRes = await supabase.auth.getUser();
    if (sessionRes.error || !sessionRes.data?.user) {
      console.error('Error obteniendo usuario:', sessionRes.error);
      return toast('No se pudo obtener el usuario','error');
    }

    console.log('Login exitoso, redirigiendo...');
    toast('Inicio de sesión correcto')
    router.push('/calendario');
  };


  return (
    <div className={`form-container ${syne.className}`}>
      <h2>Iniciar sesión</h2>
      <form className="form">
        <input
          name="email"
          type="email"
          placeholder="Email"
          onChange={handleChange}
          className={inter.className}
        />
        <input
          name="password"
          type="password"
          placeholder="Contraseña"
          onChange={handleChange}
          className={inter.className}
        />
        <button
          type="button"
          disabled={!isReady}
          onClick={handleLogin}
          className="form-button"
        >
          Iniciar sesión
        </button>
      </form>
      <p className={`${syne.className} login-register-hint`}>
        ¿No tienes cuenta?{' '}
        <Link href="/start/register" className="register-link">
          Regístrate
        </Link>
      </p>
    </div>
  );
}
