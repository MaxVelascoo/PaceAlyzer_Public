// src/app/calendario/page.tsx
import styles from './page.module.css';
import { Syne, Inter } from 'next/font/google';
import Link from 'next/link';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });
const inter = Inter({ subsets: ['latin'], weight: ['400'] });

export default function CompletarRegistroPage() {
  return (
    <main className={styles.root}>
      <div className={styles.container}>
        {/* Añade syne.className aquí */}
        <h1 className={`${styles.title} ${syne.className}`}>
          ¡Bienvenido a PaceAlyzer!
        </h1>

        {/* Y añade inter.className aquí */}
        <p className={`${styles.description} ${inter.className}`}>
          Has conectado exitosamente tu cuenta de Strava. …
        </p>

        <ul className={`${styles.features} ${inter.className}`}>
          {[
            'Analiza tu progreso en tiempo real',
            'Recibe recomendaciones de entrenamiento',
            'Explora tus mejores rendimientos',
          ].map((txt) => (
            <li key={txt} className={styles.featureItem}>
              <span className={styles.checkIcon}>✔</span>
              <span>{txt}</span>
            </li>
          ))}
        </ul>

        <Link href="/profile">
          <button className={`${styles.button} ${inter.className}`}>
            Ver mi perfil
          </button>
        </Link>
      </div>
    </main>
  );
}
