'use client';
import React from 'react';
import Link from 'next/link';
import styles from '../terms/terms.module.css';

export default function PrivacyPage() {
  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <Link href="/" className={styles.back}>← Volver</Link>

        <h1 className={styles.title}>Política de Privacidad</h1>
        <p className={styles.updated}>Última actualización: 6 de abril de 2026</p>

        <p className={styles.lead}>
          PaceAlyzer es una plataforma de planificación y análisis de entrenamiento deportivo orientada a ciclismo. La aplicación se integra con Strava bajo autorización expresa del usuario.
        </p>

        <section className={styles.section}>
          <h2 className={styles.h2}>1. Datos que recopilamos</h2>
          <p>Cuando conectas tu cuenta de Strava podemos acceder a:</p>
          <ul className={styles.list}>
            <li>Nombre y foto de perfil.</li>
            <li>Actividades deportivas (tiempo, distancia, potencia, frecuencia cardíaca, etc.).</li>
            <li>Métricas agregadas de entrenamiento.</li>
          </ul>
          <p>También almacenamos datos introducidos manualmente como peso, FTP, fecha de nacimiento y frecuencia cardíaca máxima.</p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.h2}>2. Finalidad del tratamiento</h2>
          <p>Utilizamos estos datos exclusivamente para:</p>
          <ul className={styles.list}>
            <li>Generar análisis personalizados de rendimiento.</li>
            <li>Adaptar dinámicamente planes de entrenamiento.</li>
            <li>Optimizar la carga en función de la recuperación.</li>
          </ul>
          <p>No vendemos ni redistribuimos tus datos a terceros.</p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.h2}>3. Integraciones con terceros</h2>
          <p>PaceAlyzer utiliza la API oficial de Strava. El acceso se realiza únicamente mediante autorización OAuth proporcionada por el usuario. Los datos obtenidos se usan solo dentro de la aplicación y no se comparten con otras plataformas.</p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.h2}>4. Almacenamiento y seguridad</h2>
          <p>Los datos se almacenan en infraestructura segura (Supabase) con autenticación y Row Level Security. No almacenamos contraseñas de servicios externos, solo tokens de acceso necesarios para las APIs.</p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.h2}>5. Uso de Inteligencia Artificial</h2>
          <p>PaceAlyzer utiliza modelos de IA para generar recomendaciones y adaptar entrenamientos. Estos modelos no toman decisiones médicas ni sustituyen asesoramiento profesional.</p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.h2}>6. Derechos del usuario</h2>
          <p>Puedes solicitar en cualquier momento acceso, corrección o eliminación completa de tu cuenta y datos. Escríbenos a <a href="mailto:max.velasco.rajo@gmail.com" className={styles.link}>max.velasco.rajo@gmail.com</a>.</p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.h2}>7. Conservación de datos</h2>
          <p>Conservamos tus datos mientras tu cuenta permanezca activa. Si eliminas tu cuenta, los datos serán borrados permanentemente.</p>
        </section>
      </div>
    </main>
  );
}
