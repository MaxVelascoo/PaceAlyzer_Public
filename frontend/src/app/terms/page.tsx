'use client';
import React from 'react';
import Link from 'next/link';
import styles from './terms.module.css';

export default function TermsPage() {
  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <Link href="/" className={styles.back}>← Volver</Link>

        <h1 className={styles.title}>Términos y Condiciones</h1>
        <p className={styles.updated}>Última actualización: 6 de abril de 2026</p>

        <p className={styles.lead}>
          Bienvenido a PaceAlyzer. Al acceder o usar nuestra aplicación aceptas estos Términos y nuestra Política de Privacidad.
        </p>

        <section className={styles.section}>
          <h2 className={styles.h2}>1. Servicios</h2>
          <p>PaceAlyzer proporciona análisis y planificación de entrenamientos de ciclismo conectándose a tu cuenta de Strava mediante OAuth. Los resultados tienen fines informativos y no constituyen asesoramiento médico ni profesional.</p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.h2}>2. Uso de datos</h2>
          <p>Solo utilizamos los datos que autorizas a compartir desde Strava. Son necesarios para ofrecerte análisis personalizados. No compartimos tu información con terceros ni la usamos con fines comerciales.</p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.h2}>3. Inteligencia Artificial</h2>
          <p>PaceAlyzer utiliza modelos de IA para generar recomendaciones y adaptar entrenamientos. Estos modelos no toman decisiones médicas ni sustituyen asesoramiento profesional.</p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.h2}>4. Limitación de responsabilidad</h2>
          <p>PaceAlyzer no se responsabiliza por decisiones de entrenamiento tomadas exclusivamente a partir de nuestros análisis. Te recomendamos complementar la información con orientación profesional.</p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.h2}>5. Cambios en los términos</h2>
          <p>Podremos actualizar estos Términos ocasionalmente. Te notificaremos en la app o por email. El uso continuado implica tu aceptación de los cambios.</p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.h2}>6. Contacto</h2>
          <p>Si tienes dudas, escríbenos a <a href="mailto:max.velasco.rajo@gmail.com" className={styles.link}>max.velasco.rajo@gmail.com</a>.</p>
        </section>
      </div>
    </main>
  );
}
