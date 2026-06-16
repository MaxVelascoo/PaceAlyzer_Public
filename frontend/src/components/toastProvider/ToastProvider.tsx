'use client';
import React, { createContext, useContext, useState, useCallback } from 'react';
import styles from './toast.module.css';
import { Syne } from 'next/font/google';


type ToastType = 'success' | 'error';

type Toast = {
  message: string;
  type: ToastType;
};

const ToastContext = createContext<(message: string, type?: ToastType) => void>(() => {});
const syne = Syne({ subsets: ['latin'], weight: ['700'] });


export const useToast = () => useContext(ToastContext);

export const ToastProvider = ({ children }: { children: React.ReactNode }) => {
  const [toast, setToast] = useState<Toast | null>(null);

  const showToast = useCallback((message: string, type: ToastType = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000); // duración del toast
  }, []);

  return (
    <ToastContext.Provider value={showToast}>
      {children}
      {toast && (
        <div
          className={`${styles.toast} ${toast.type === 'error' ? styles.error : styles.success} ${syne.className}`}
        >
          {toast.message}
        </div>
      )}

    </ToastContext.Provider>
  );
};
