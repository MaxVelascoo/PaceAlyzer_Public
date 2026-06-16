'use client';

import { useEffect, useMemo, useState } from 'react';
import { useUser } from '@/context/userContext';
import { supabase } from '@/lib/supabaseClient';
import { useRouter } from 'next/navigation';
import { Syne } from 'next/font/google';
import ProtectedRoute from '@/components/ProtectedRoute';
import UserAvatar from '@/components/UserAvatar';
import styles from './profile.module.css';
import { useToast } from '@/components/toastProvider/ToastProvider';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });

type PerfilData = {
  firstname: string;
  lastname: string;
  email: string;
  telef: string;
  weight: number;
  ftp: number;
  avatar_url: string | null;
  birthdate: string;
  max_heartrate: number;
  goal: string;
  available_days: number;
};

type MetricCardProps = {
  label: string;
  value: string;
  accent: 'orange' | 'blue' | 'mint' | 'ink';
  helper?: string;
};

function MetricCard({ label, value, accent, helper }: MetricCardProps) {
  return (
    <article className={`${styles.metricCard} ${styles[`accent_${accent}`]}`}>
      <span className={styles.metricLabel}>{label}</span>
      <strong className={styles.metricValue}>{value}</strong>
      {helper ? <span className={styles.metricHelper}>{helper}</span> : null}
    </article>
  );
}

function calculateAge(value: string) {
  if (!value) return null;

  const birth = new Date(`${value.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(birth.getTime())) return null;

  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const hasHadBirthday =
    today.getMonth() > birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() >= birth.getDate());

  if (!hasHadBirthday) age -= 1;
  return age >= 0 ? age : null;
}

function getInitials(firstname: string, lastname: string) {
  return `${firstname?.[0] ?? ''}${lastname?.[0] ?? ''}`.trim().toUpperCase() || 'PA';
}

export default function PerfilPage() {
  const user = useUser()?.user;
  const router = useRouter();
  const toast = useToast();

  const [perfil, setPerfil] = useState<PerfilData | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);
  const [recalcMmp, setRecalcMmp] = useState(false);
  const [recalcMmpResult, setRecalcMmpResult] = useState<string | null>(null);

  const [form, setForm] = useState({
    telef: '',
    weight: '',
    ftp: '',
    birthdate: '',
    max_heartrate: '',
    goal: '',
    available_days: '5',
  });

  const getSignedAvatarUrl = async (filePath: string) => {
    const { data, error } = await supabase.storage
      .from('avatars')
      .createSignedUrl(filePath, 60 * 60);

    if (error) throw error;
    return data?.signedUrl ?? null;
  };

  useEffect(() => {
    const fetchPerfil = async () => {
      if (!user) {
        setLoading(false);
        return;
      }

      setLoading(true);

      try {
        const { data, error } = await supabase
          .from('users')
          .select('firstname, lastname, email, telef, ftp, weight, birthdate, max_heartrate, avatar_url, goal, available_days')
          .eq('id', user.id)
          .single();

        if (error) {
          console.error('Error fetching profile:', error);
          toast('Error al cargar el perfil: ' + (error.message || 'Error desconocido'), 'error');
          setLoading(false);
          return;
        }

        if (data) {
          let signedAvatar: string | null = null;

          if (data.avatar_url) {
            try {
              signedAvatar = await getSignedAvatarUrl(data.avatar_url);
            } catch (e) {
              console.warn('No se pudo generar signed URL del avatar:', e);
            }
          }

          setPerfil({
            firstname: data.firstname,
            lastname: data.lastname,
            email: data.email,
            telef: data.telef || '',
            weight: data.weight ?? 0,
            ftp: data.ftp ?? 0,
            birthdate: data.birthdate || '',
            max_heartrate: data.max_heartrate ?? 0,
            avatar_url: signedAvatar,
            goal: data.goal || '',
            available_days: data.available_days ?? 5,
          });

          setForm({
            telef: data.telef || '',
            weight: data.weight?.toString() || '',
            ftp: data.ftp?.toString() || '',
            birthdate: data.birthdate?.slice(0, 10) || '',
            max_heartrate: data.max_heartrate?.toString() || '',
            goal: data.goal || '',
            available_days: (data.available_days ?? 5).toString(),
          });
        }
      } catch (err) {
        console.error('Exception fetching profile:', err);
        toast('Error inesperado al cargar el perfil', 'error');
      } finally {
        setLoading(false);
      }
    };

    fetchPerfil();
  }, [user, toast]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleUpdate = async () => {
    if (!user) return;

    const { error } = await supabase
      .from('users')
      .update({
        telef: form.telef,
        weight: Number(form.weight),
        ftp: Number(form.ftp),
        birthdate: form.birthdate,
        max_heartrate: Number(form.max_heartrate),
        goal: form.goal || null,
        available_days: Number(form.available_days) || 5,
      })
      .eq('id', user.id);

    if (error) {
      toast('Error al guardar los cambios', 'error');
      return;
    }

    setPerfil((prev) =>
      prev
        ? {
            ...prev,
            telef: form.telef,
            weight: Number(form.weight),
            ftp: Number(form.ftp),
            birthdate: form.birthdate,
            max_heartrate: Number(form.max_heartrate),
            goal: form.goal,
            available_days: Number(form.available_days) || 5,
          }
        : prev
    );

    setEditing(false);
    toast('Datos actualizados correctamente');
  };

  const uploadAvatar = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0] || !user) return;

    setUploading(true);

    try {
      const file = e.target.files[0];
      const fileExt = file.name.split('.').pop() || 'jpg';
      const fileName = `${Date.now()}.${fileExt}`;
      const filePath = `${user.id}/${fileName}`;

      const { error: uploadError } = await supabase.storage
        .from('avatars')
        .upload(filePath, file, { upsert: true });

      if (uploadError) throw uploadError;

      const { error: dbError } = await supabase
        .from('users')
        .update({ avatar_url: filePath })
        .eq('id', user.id);

      if (dbError) throw dbError;

      const signedUrl = await getSignedAvatarUrl(filePath);
      setPerfil((prev) => (prev ? { ...prev, avatar_url: signedUrl } : prev));
      toast('Foto subida correctamente');
    } catch (err) {
      console.error('Upload failed:', err);
      toast('Error al subir la imagen', 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.replace('/');
  };

  const handleFullImport = async () => {
    if (!user || importing) return;

    const confirmed = window.confirm(
      'Esto importará todo tu historial de Strava. Puede tardar unos segundos. ¿Continuar?'
    );
    if (!confirmed) return;

    setImporting(true);
    setImportResult(null);

    try {
      const res = await fetch('/api/strava/sync-trainings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: user.id, lookbackDays: 3650, fullImport: true }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error ?? 'Error importando');
      setImportResult(`✓ ${json.insertedOrUpdated} actividades importadas correctamente`);
      toast('Historial importado correctamente');
    } catch (e) {
      setImportResult(`Error: ${(e as Error).message}`);
      toast('Error al importar el historial', 'error');
    } finally {
      setImporting(false);
    }
  };

  const handleRecalcMmp = async () => {
    if (!user || recalcMmp) return;
    setRecalcMmp(true);
    setRecalcMmpResult(null);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';
      const res = await fetch(`${backendUrl}/api/metrics/recalculate-mmp?user_id=${user.id}`, { method: 'POST' });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.detail ?? 'Error recalculando');
      setRecalcMmpResult(`✓ ${json.trainings_processed} entrenos procesados`);
    } catch (e) {
      setRecalcMmpResult(`Error: ${(e as Error).message}`);
    } finally {
      setRecalcMmp(false);
    }
  };

  const age = useMemo(() => calculateAge(perfil?.birthdate ?? ''), [perfil?.birthdate]);
  const initials = useMemo(
    () => getInitials(perfil?.firstname ?? '', perfil?.lastname ?? ''),
    [perfil?.firstname, perfil?.lastname]
  );

  return (
    <ProtectedRoute>
      <div className={styles.page}>
        <div className={styles.shell}>
          <section className={styles.hero}>
            <div className={styles.heroCopy}>
              <p className={styles.eyebrow}>Perfil del atleta</p>
              <h1 className={`${styles.title} ${syne.className}`}>Tu centro de control personal</h1>
              <p className={styles.subtitle}>
                Ajusta tus datos clave, mantén tu identidad al día y prepara la base que usa Pazey
                para interpretar mejor tu rendimiento.
              </p>
            </div>
            <div className={styles.heroGlow} aria-hidden="true" />
          </section>

          {loading ? (
            <section className={styles.loadingCard}>
              <p>Cargando datos del perfil...</p>
            </section>
          ) : perfil ? (
            <div className={styles.contentCol}>
              <section className={styles.profileCard}>
                <div className={styles.profileTop}>
                  <div className={styles.identityTop}>
                    <div className={styles.avatarWrap}>
                    <UserAvatar
                      avatarUrl={perfil.avatar_url}
                      initials={initials}
                      size={88}
                    />
                  </div>

                    <div className={styles.identityCopy}>
                      <p className={styles.memberLabel}>Cuenta activa</p>
                      <h2 className={`${styles.name} ${syne.className}`}>
                        {perfil.firstname} {perfil.lastname}
                      </h2>
                      <p className={styles.email}>{perfil.email}</p>
                    </div>
                  </div>

                  <div className={styles.profileActions}>
                    <label className={`${styles.primaryAction} ${syne.className}`}>
                      {uploading ? 'Subiendo foto...' : 'Cambiar foto'}
                      <input type="file" accept="image/*" onChange={uploadAvatar} hidden />
                    </label>

                    {!editing ? (
                      <button onClick={() => setEditing(true)} className={`${styles.secondaryAction} ${syne.className}`}>
                        Editar perfil
                      </button>
                    ) : null}
                  </div>
                </div>

                <div className={styles.metricGrid}>
                  <MetricCard
                    label="FTP"
                    value={perfil.ftp ? `${perfil.ftp} W` : '—'}
                    accent="orange"
                    helper="Potencia umbral"
                  />
                  <MetricCard
                    label="Peso"
                    value={perfil.weight ? `${perfil.weight} kg` : '—'}
                    accent="blue"
                    helper="Para calcular W/kg"
                  />
                  <MetricCard
                    label="FC máxima"
                    value={perfil.max_heartrate ? `${perfil.max_heartrate} ppm` : '—'}
                    accent="mint"
                    helper="Zonas cardiacas"
                  />
                  <MetricCard
                    label="Edad"
                    value={age != null ? `${age}` : '—'}
                    accent="ink"
                    helper="Años"
                  />
                  <MetricCard
                    label="Objetivo"
                    value={perfil.goal || '—'}
                    accent="orange"
                    helper="Meta de entrenamiento"
                  />
                  <MetricCard
                    label="Días disponibles"
                    value={perfil.available_days ? `${perfil.available_days}` : '—'}
                    accent="ink"
                    helper="Días por semana"
                  />
                </div>

                {editing ? (
                  <div className={styles.editorOverlay}>
                    <div className={styles.editorCard}>
                      <div className={styles.panelHeader}>
                        <div>
                          <p className={styles.panelEyebrow}>Datos personales</p>
                          <h3 className={`${styles.panelTitle} ${syne.className}`}>Editar perfil</h3>
                        </div>
                      </div>

                      <div className={styles.formGrid}>
                        <label className={styles.field}>
                          <span className={styles.fieldLabel}>Teléfono</span>
                          <input name="telef" value={form.telef} onChange={handleChange} />
                        </label>
                        <label className={styles.field}>
                          <span className={styles.fieldLabel}>Peso (kg)</span>
                          <input name="weight" value={form.weight} onChange={handleChange} type="number" />
                        </label>
                        <label className={styles.field}>
                          <span className={styles.fieldLabel}>FTP (W)</span>
                          <input name="ftp" value={form.ftp} onChange={handleChange} type="number" />
                        </label>
                        <label className={styles.field}>
                          <span className={styles.fieldLabel}>Fecha de nacimiento</span>
                          <input name="birthdate" value={form.birthdate} onChange={handleChange} type="date" />
                        </label>
                        <label className={styles.field}>
                          <span className={styles.fieldLabel}>FC máxima</span>
                          <input
                            name="max_heartrate"
                            value={form.max_heartrate}
                            onChange={handleChange}
                            type="number"
                          />
                        </label>
                        <label className={styles.field}>
                          <span className={styles.fieldLabel}>Objetivo</span>
                          <select name="goal" value={form.goal} onChange={handleChange}>
                            <option value="">Sin especificar</option>
                            <option value="Competir">Competir</option>
                            <option value="Mejorar rendimiento">Mejorar rendimiento</option>
                            <option value="Perder peso">Perder peso</option>
                            <option value="Salud y bienestar">Salud y bienestar</option>
                            <option value="Resistencia">Resistencia</option>
                          </select>
                        </label>
                        <label className={styles.field}>
                          <span className={styles.fieldLabel}>Días disponibles/semana</span>
                          <input
                            name="available_days"
                            value={form.available_days}
                            onChange={handleChange}
                            type="number"
                            min="1"
                            max="7"
                          />
                        </label>
                      </div>

                      <div className={styles.buttonRow}>
                        <button onClick={handleUpdate} className={`${styles.primaryDark} ${syne.className}`}>
                          Guardar cambios
                        </button>
                        <button onClick={() => setEditing(false)} className={`${styles.ghostAction} ${syne.className}`}>
                          Cancelar
                        </button>
                      </div>
                    </div>
                  </div>
                ) : null}
              </section>

              <section className={styles.dualPanels}>
                <article className={styles.panel}>
                  <p className={styles.panelEyebrow}>Datos e historial</p>
                  <h3 className={`${styles.panelTitle} ${syne.className}`}>Importación completa de Strava</h3>
                  <p className={styles.panelText}>
                    Importa todo tu historial para calcular mejor CTL, ATL y TSB, y darle a Pazey
                    más contexto real para futuras recomendaciones.
                  </p>

                  <button
                    onClick={handleFullImport}
                    disabled={importing}
                    className={`${styles.importButton} ${syne.className}`}
                  >
                    {importing ? 'Importando historial...' : 'Importar historial completo'}
                  </button>

                  {importResult ? <p className={styles.importResult}>{importResult}</p> : null}

                  <button
                    onClick={handleRecalcMmp}
                    disabled={recalcMmp}
                    className={`${styles.importButton} ${syne.className}`}
                    style={{ marginTop: 8, background: 'rgba(99,102,241,0.9)' }}
                  >
                    {recalcMmp ? 'Calculando curva de potencia...' : 'Recalcular curva de potencia histórica'}
                  </button>

                  {recalcMmpResult ? <p className={styles.importResult}>{recalcMmpResult}</p> : null}
                </article>

                <article className={`${styles.panel} ${styles.sessionPanel}`}>
                  <p className={styles.panelEyebrow}>Cuenta</p>
                  <h3 className={`${styles.panelTitle} ${syne.className}`}>Sesión y acceso</h3>
                  <p className={styles.panelText}>
                    Cierra la sesión actual si vas a cambiar de dispositivo o simplemente quieres
                    salir de PaceAlyzer.
                  </p>

                  <button onClick={handleLogout} className={`${styles.logoutButton} ${syne.className}`}>
                    Cerrar sesión
                  </button>
                </article>
              </section>
            </div>
          ) : (
            <section className={styles.loadingCard}>
              <p>No se pudieron cargar los datos del perfil.</p>
            </section>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}
