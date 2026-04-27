import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { createContext, useContext, useEffect, useState } from 'react';
import type { Id } from '../../convex/_generated/dataModel';

type AuthState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'authenticated'; userId: Id<'users'> };

type AuthContextValue = {
  auth: AuthState;
  signIn: (userId: Id<'users'>) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY = 'darlink:userId';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({ status: 'loading' });

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then((stored) => {
      if (stored) {
        setAuth({ status: 'authenticated', userId: stored as Id<'users'> });
      } else {
        setAuth({ status: 'unauthenticated' });
      }
    });
  }, []);

  async function signIn(userId: Id<'users'>) {
    await AsyncStorage.setItem(STORAGE_KEY, userId);
    setAuth({ status: 'authenticated', userId });
  }

  async function signOut() {
    await AsyncStorage.removeItem(STORAGE_KEY);
    setAuth({ status: 'unauthenticated' });
  }

  return (
    <AuthContext.Provider value={{ auth, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
