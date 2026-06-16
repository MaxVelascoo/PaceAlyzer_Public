import './styles.css';
import Link from 'next/link';
import Image from 'next/image';
import { Syne } from 'next/font/google';
import { UserProvider } from '@/context/userContext';
import Header from '@/components/header';
import { ToastProvider } from '@/components/toastProvider/ToastProvider';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });

export const metadata = {
  title: 'PaceAlyzer',
  description: 'Entrenador virtual inteligente',
  icons: {
    icon: [
      { url: '/symbol.png', type: 'image/png' },
    ],
    apple: '/symbol.png',
    shortcut: '/symbol.png',
  },
  openGraph: {
    title: 'PaceAlyzer',
    description: 'Entrenador virtual inteligente',
    url: 'https://pacealyzer.onrender.com/',
    type: 'website',
    images: [
      {
        url: 'https://xtimujswspgehcymyvfr.supabase.co/storage/v1/object/public/assets//portada.png',
        width: 1200,
        height: 630,
        alt: 'PaceAlyzer portada',
      },
    ],
  },
  metadataBase: new URL('https://pacealyzer.onrender.com'),
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/symbol.png" type="image/png" />
        <link rel="apple-touch-icon" href="/symbol.png" />
      </head>
      <body>
        <ToastProvider>
          <UserProvider>
            <Header />
            <main>{children}</main>
          </UserProvider>

          <footer className="footer">
            <div className="footer-left">
              <h2 className={syne.className}>PaceAlyzer</h2>
              <p>123-456-789</p>
              <p>max.velasco.rajo@gmail.com</p>
              <p>Barcelona</p>
            </div>
            <div className="footer-right">
              <ul>
                <li><Link href="/privacy">Política de Privacidad</Link></li>
                <li><Link href="/terms">Términos y Condiciones</Link></li>
              </ul>
            </div>
            <div className="footer-bottom">
              <div className="footer-bottom-content">
                <p>© 2025 by PaceAlyzer.</p>
                <Image
                  src="/api_logo_pwrdBy_strava_stack_white.png"
                  alt="Powered by Strava"
                  width={120}
                  height={30}
                  className="strava-logo"
                />
              </div>
            </div>
          </footer>
        </ToastProvider>
      </body>
    </html>
  );
}
