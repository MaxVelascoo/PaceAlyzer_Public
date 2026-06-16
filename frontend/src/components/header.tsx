'use client';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { Syne } from 'next/font/google';
import { useUser } from '@/context/userContext';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });

export default function Header() {
  const pathname = usePathname();
  const isHome = pathname === '/';
  const { user } = useUser() || {};

  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          <Link href="/" className={`logo ${syne.className}`}>
            PaceAlyzer
          </Link>
        </div>

        <div className="header-center">
          <Link href="/">
            <Image
              src={isHome ? '/logo.png' : '/logo-color.png'}
              alt="PaceAlyzer logo"
              className="header-logo"
              width={isHome ? 1024 : 500}
              height={isHome ? 1024 : 500}
            />
          </Link>
        </div>

        <div className="header-right">
          <nav className="nav">
            {user ? (
              <>
                <Link href="/chat" className={`nav-link ${syne.className}`}>
                  Chat
                </Link>
                <Link href="/dashboard" className={`nav-link ${syne.className}`}>
                  Dashboard
                </Link>
                <Link href="/calendario" className={`nav-link calendario-link ${syne.className}`}>
                  Calendario
                </Link>
                <Link href="/profile" className={`nav-link ${syne.className}`}>
                  Perfil
                </Link>
              </>
            ) : (
              <>
                <Link href="/start/login" className={`nav-link ${syne.className}`}>
                  Iniciar sesión
                </Link>
                <Link href="/start/register" className={`nav-link ${syne.className}`}>
                  Registrarse
                </Link>
              </>
            )}
            <Link href="/" className={`nav-link ${syne.className}`}>
              Inicio
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
