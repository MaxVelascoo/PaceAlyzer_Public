'use client';

import React, { useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { Syne } from 'next/font/google';
import { useUser } from '@/context/userContext';
import { supabase } from '@/lib/supabaseClient';
import './styles.css';

const syne = Syne({ subsets: ['latin'], weight: ['700', '800'] });

function useInView(threshold = 0.12) {
  const ref = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setVisible(true); }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, visible };
}

const FEATURES = [
  {
    accent: '#FC4C02',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
    title: 'Métricas reales',
    desc: 'CTL, ATL, TSB, potencia normalizada y zonas de FC calculadas a partir de tus actividades de Strava. Sin estimaciones, solo datos.',
  },
  {
    accent: '#6366f1',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
    title: 'Pazey, tu entrenador IA',
    desc: 'Habla con Pazey en lenguaje natural. Pídele que planifique tu semana, modifique un entreno o ajuste la nutrición. Él lo hace.',
  },
  {
    accent: '#22c55e',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
      </svg>
    ),
    title: 'Calendario inteligente',
    desc: 'Visualiza entrenamientos planificados y realizados en un mismo calendario. Arrastra y reorganiza sesiones con un simple drag & drop.',
  },
  {
    accent: '#f59e0b',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 8h1a4 4 0 0 1 0 8h-1" /><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z" /><line x1="6" y1="1" x2="6" y2="4" /><line x1="10" y1="1" x2="10" y2="4" /><line x1="14" y1="1" x2="14" y2="4" />
      </svg>
    ),
    title: 'Nutrición por sesión',
    desc: 'Cada entreno lleva su plan nutricional: qué comer antes, durante y después. Adaptado a la intensidad y duración de la sesión.',
  },
];

const STEPS = [
  { n: '01', title: 'Conecta Strava', desc: 'Un clic y tus actividades, potencia y frecuencia cardíaca están dentro de PaceAlyzer.' },
  { n: '02', title: 'Analiza tu forma', desc: 'El dashboard calcula tu fitness crónico, fatiga aguda y balance de carga en tiempo real.' },
  { n: '03', title: 'Habla con Pazey', desc: 'Dile qué quieres conseguir. Pazey planifica, ajusta y explica cada decisión.' },
  { n: '04', title: 'Entrena mejor', desc: 'Sigue el plan, registra tus sesiones y observa cómo tu rendimiento sube semana a semana.' },
];

export default function HomePage() {
  const router = useRouter();
  const user = useUser()?.user;
  const [hasStrava, setHasStrava] = useState<boolean | null>(null);

  const hero    = useInView(0.05);
  const features = useInView(0.08);
  const steps   = useInView(0.08);
  const cta     = useInView(0.1);

  useEffect(() => {
    if (!user) return;
    supabase.from('strava_accounts').select('strava_id').eq('user_id', user.id).maybeSingle()
      .then(({ data }) => setHasStrava(!!data?.strava_id));
  }, [user]);

  const handleCTA = () => {
    if (!user) return router.push('/start');
    if (hasStrava === false) return router.push('/connect-strava');
    return router.push('/calendario');
  };

  const ctaLabel = !user ? 'Empezar gratis' : hasStrava === false ? 'Conectar Strava' : 'Ir al calendario';

  return (
    <div className="lp-root">

      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <section className="lp-hero" ref={hero.ref as React.RefObject<HTMLElement>}>
        <div className={`lp-hero-inner fade-in-section ${hero.visible ? 'visible' : ''}`}>

          <div className="lp-hero-copy">
            <div className="lp-badge">
              <span className="lp-badge-dot" />
              Powered by Multi-Agent AI System
            </div>

            <h1 className={`lp-h1 ${syne.className}`}>
              Entrena con datos.<br />
              <span className="lp-h1-accent">Mejora de verdad.</span>
            </h1>

            <p className="lp-hero-sub">
              PaceAlyzer sincroniza con Strava, analiza tu carga de entrenamiento y te da acceso a Pazey,
              tu entrenador personal con IA que planifica, ajusta y explica cada sesión.
            </p>

            <div className="lp-hero-actions">
              <button className={`lp-btn-primary ${syne.className}`} onClick={handleCTA}>
                {ctaLabel}
              </button>
              <a href="#como-funciona" className="lp-btn-ghost">
                Cómo funciona ↓
              </a>
            </div>

            <div className="lp-hero-social">
              <Image src="/api_logo_pwrdBy_strava_stack_white.png" alt="Powered by Strava" width={120} height={32} style={{ objectFit: 'contain', opacity: 0.7 }} />
            </div>
          </div>

          <div className="lp-hero-visual">
            <div className="lp-mockup-glow" aria-hidden />
            <Image
              src="/mockup-DayPagee.png"
              alt="PaceAlyzer dashboard"
              width={1200}
              height={800}
              className="lp-hero-img"
              priority
            />
          </div>

        </div>
      </section>

      {/* ── FEATURES ─────────────────────────────────────────────────────── */}
      <section className="lp-features" ref={features.ref as React.RefObject<HTMLElement>}>
        <div className={`lp-section-inner fade-in-section ${features.visible ? 'visible' : ''}`}>

          <div className="lp-section-header">
            <p className="lp-eyebrow">Qué incluye</p>
            <h2 className={`lp-h2 ${syne.className}`}>Todo lo que necesitas para rendir más</h2>
          </div>

          <div className="lp-features-grid">
            {FEATURES.map((f) => (
              <article key={f.title} className="lp-feature-card">
                <div className="lp-feature-icon" style={{ background: `${f.accent}18`, color: f.accent }}>
                  {f.icon}
                </div>
                <h3 className={`lp-feature-title ${syne.className}`}>{f.title}</h3>
                <p className="lp-feature-desc">{f.desc}</p>
              </article>
            ))}
          </div>

        </div>
      </section>

      {/* ── MOCKUP FULL ──────────────────────────────────────────────────── */}
      <section className="lp-showcase">
        <div className="lp-section-inner">
          <div className="lp-showcase-copy">
            <p className="lp-eyebrow lp-eyebrow-dark">Pazey en acción</p>
            <h2 className={`lp-h2 ${syne.className}`}>Tu entrenador siempre disponible</h2>
            <p className="lp-showcase-sub">
              Escríbele en lenguaje natural. &ldquo;Hazme un rodaje suave para mañana&rdquo; o &ldquo;Cambia el martes por un descanso activo&rdquo;.
              Pazey entiende el contexto, consulta tus métricas y actúa.
            </p>
            <button className={`lp-btn-dark ${syne.className}`} onClick={handleCTA}>
              Probar Pazey
            </button>
          </div>
          <div className="lp-showcase-img-wrap">
            <Image
              src="/mockup-ChatPage.png"
              alt="Chat con Pazey"
              width={700}
              height={480}
              className="lp-showcase-img"
            />
          </div>
        </div>
      </section>

      {/* ── CÓMO FUNCIONA ────────────────────────────────────────────────── */}
      <section className="lp-steps" id="como-funciona" ref={steps.ref as React.RefObject<HTMLElement>}>
        <div className={`lp-section-inner fade-in-section ${steps.visible ? 'visible' : ''}`}>

          <div className="lp-section-header">
            <p className="lp-eyebrow">El proceso</p>
            <h2 className={`lp-h2 ${syne.className}`}>De cero a entrenar con IA en 4 pasos</h2>
          </div>

          <div className="lp-steps-grid">
            {STEPS.map((s) => (
              <div key={s.n} className="lp-step">
                <span className={`lp-step-n ${syne.className}`}>{s.n}</span>
                <h3 className={`lp-step-title ${syne.className}`}>{s.title}</h3>
                <p className="lp-step-desc">{s.desc}</p>
              </div>
            ))}
          </div>

        </div>
      </section>

      {/* ── CTA FINAL ────────────────────────────────────────────────────── */}
      <section className="lp-cta" ref={cta.ref as React.RefObject<HTMLElement>}>
        <div className={`lp-cta-inner fade-in-section ${cta.visible ? 'visible' : ''}`}>
          <h2 className={`lp-cta-title ${syne.className}`}>
            ¿Listo para entrenar<br />con inteligencia?
          </h2>
          <p className="lp-cta-sub">
            Conecta Strava, habla con Pazey y empieza a ver la diferencia en tu rendimiento.
          </p>
          <button className={`lp-btn-primary lp-btn-lg ${syne.className}`} onClick={handleCTA}>
            {ctaLabel}
          </button>
          <p className="lp-cta-hint">Gratis. Sin tarjeta de crédito.</p>
        </div>
      </section>

    </div>
  );
}
