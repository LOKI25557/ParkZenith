import React, { createContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import type { User, UserRegisterRequest } from '../types';
import { authApi } from '../api/auth';
import { getStoredToken, setStoredToken, removeStoredToken } from '../api/client';

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (userData: UserRegisterRequest) => Promise<User>;
  logout: () => void;
  refreshUser: () => Promise<User | null>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    removeStoredToken();
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async (): Promise<User | null> => {
    const currentToken = getStoredToken();
    if (!currentToken) {
      setUser(null);
      setToken(null);
      return null;
    }
    try {
      const currentUser = await authApi.getCurrentUser();
      setUser(currentUser);
      setToken(currentToken);
      return currentUser;
    } catch (error) {
      console.error('Failed to refresh user profile:', error);
      logout();
      return null;
    }
  }, [logout]);

  // Initial application authentication check
  useEffect(() => {
    let isMounted = true;

    const initAuth = async () => {
      const storedToken = getStoredToken();
      if (storedToken) {
        try {
          const currentUser = await authApi.getCurrentUser();
          if (isMounted) {
            setUser(currentUser);
            setToken(storedToken);
          }
        } catch (error) {
          console.warn('Stored token is invalid or expired. Session cleared.', error);
          if (isMounted) {
            removeStoredToken();
            setToken(null);
            setUser(null);
          }
        }
      }
      if (isMounted) {
        setIsLoading(false);
      }
    };

    initAuth();

    // Listen for unauthorized 401 events from the API client
    const handleUnauthorized = () => {
      logout();
    };
    window.addEventListener('unauthorized', handleUnauthorized);

    return () => {
      isMounted = false;
      window.removeEventListener('unauthorized', handleUnauthorized);
    };
  }, [logout]);

  const login = async (email: string, password: string): Promise<User> => {
    const tokenResponse = await authApi.login({ email, password });
    setStoredToken(tokenResponse.access_token);
    setToken(tokenResponse.access_token);

    // Immediately fetch the authenticated user profile
    const currentUser = await authApi.getCurrentUser();
    setUser(currentUser);
    return currentUser;
  };

  const register = async (userData: UserRegisterRequest): Promise<User> => {
    return await authApi.register(userData);
  };

  const isAuthenticated = Boolean(token && user);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
