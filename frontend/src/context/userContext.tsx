'use client';
import { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import type { User } from '@supabase/supabase-js';
import type { Dispatch, SetStateAction } from 'react';

type UserContextType = {
  user: User | null;
  setUser: Dispatch<SetStateAction<User | null>>;
};

export const UserContext = createContext<UserContextType | undefined>(undefined);

export const UserProvider = ({ children }: { children: React.ReactNode }) => {
   const [user, setUser] = useState<User | null>(null)

useEffect(() => {
  const getSession = async () => {
    const { data } = await supabase.auth.getSession()
    setUser(data?.session?.user ?? null)
  }
  getSession()
  const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
    setUser(session?.user ?? null)
  })
  return () => listener.subscription.unsubscribe()
}, [])

// Más abajo, en `useUser()` o donde lo consumas,
// contempla `undefined` como “cargando”



  return (
    <UserContext.Provider value={{ user, setUser }}>
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => useContext(UserContext);
