import { createContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import type { User, Token } from '../types';
import { authApi } from '../api/auth';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('parkzenith_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          const currentUser = await authApi.getCurrentUser();
          setUser(currentUser);
        } catch (error) {
          console.error("Failed to authenticate token", error);
          logout();
        }
      }
      setIsLoading(false);
    };

    initAuth();

    // Listen for unauthorized events from api client
    const handleUnauthorized = () => logout();
    window.addEventListener('unauthorized', handleUnauthorized);
    
    return () => {
      window.removeEventListener('unauthorized', handleUnauthorized);
    };
  }, [token]);

  const login = async (email: string, password: string) => {
    try {
      const response: Token = await authApi.login(email, password);
      localStorage.setItem('parkzenith_token', response.access_token);
      setToken(response.access_token);
    } catch (error) {
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('parkzenith_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
