'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { apiClient, setMemoryToken, setAuthCallbacks } from '@/lib/api';

export interface User {
  id: number;
  email: string;
  full_name?: string;
  role: string;
}

export interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  isLoading: boolean;
  isInitialized: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name: string, role: 'Admin' | 'Editor') => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const PUBLIC_PATHS = ['/login', '/register', '/privacy-policy', '/data-deletion', '/terms'];

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isInitialized, setIsInitialized] = useState<boolean>(false);
  const router = useRouter();
  const pathname = usePathname();

  const updateAccessToken = useCallback((token: string | null) => {
    setMemoryToken(token);
    setAccessTokenState(token);
  }, []);

  const handleLogout = useCallback(() => {
    updateAccessToken(null);
    setUser(null);
    if (typeof window !== 'undefined') {
      const isPublic = PUBLIC_PATHS.some((p) => window.location.pathname.startsWith(p));
      if (!isPublic) {
        router.push('/login');
      }
    }
  }, [updateAccessToken, router]);

  // Register interceptor callbacks with apiClient
  useEffect(() => {
    setAuthCallbacks(
      (newToken: string, data: any) => {
        updateAccessToken(newToken);
        if (data?.user_id) {
          setUser({
            id: data.user_id,
            email: data.email,
            full_name: data.full_name,
            role: data.role,
          });
        }
      },
      () => {
        handleLogout();
      }
    );
  }, [updateAccessToken, handleLogout]);

  // Initial silent refresh on app startup / page reload (F5)
  const refreshSession = useCallback(async (): Promise<boolean> => {
    try {
      const res = await apiClient.post('/auth/refresh');
      if (res.data?.access_token) {
        updateAccessToken(res.data.access_token);
        if (res.data.user_id) {
          setUser({
            id: res.data.user_id,
            email: res.data.email,
            full_name: res.data.full_name,
            role: res.data.role,
          });
        }
        return true;
      }
    } catch {
      updateAccessToken(null);
      setUser(null);
    }
    return false;
  }, [updateAccessToken]);

  useEffect(() => {
    let isMounted = true;

    async function initAuth() {
      setIsLoading(true);
      await refreshSession();
      if (isMounted) {
        setIsLoading(false);
        setIsInitialized(true);
      }
    }

    initAuth();

    return () => {
      isMounted = false;
    };
  }, [refreshSession]);

  const login = async (email: string, password: string) => {
    const res = await apiClient.post('/auth/login', {
      email: email.trim(),
      password,
    });

    if (res.data?.access_token) {
      updateAccessToken(res.data.access_token);
      if (res.data.user_id) {
        setUser({
          id: res.data.user_id,
          email: res.data.email,
          full_name: res.data.full_name,
          role: res.data.role,
        });
      }
    } else {
      throw new Error('Authentication response did not return an access token.');
    }
  };

  const register = async (
    email: string,
    password: string,
    full_name: string,
    role: 'Admin' | 'Editor'
  ) => {
    await apiClient.post('/auth/register', {
      full_name: full_name.trim(),
      email: email.trim(),
      password,
      role,
    });

    // Auto-login after registration
    await login(email, password);
  };

  const logout = async () => {
    try {
      await apiClient.post('/auth/logout');
    } catch (e) {
      console.warn('Logout request warning:', e);
    } finally {
      handleLogout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken,
        isLoading,
        isInitialized,
        login,
        register,
        logout,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
