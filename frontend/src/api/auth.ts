import { apiClient } from './client';
import type { User, Token } from '../types';

export const authApi = {
  login: async (email: string, password: string): Promise<Token> => {
    // FastAPI OAuth2PasswordRequestForm requires form-data
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);
    const response = await apiClient.post<Token>('/api/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    return response.data;
  },

  register: async (userData: any): Promise<User> => {
    const response = await apiClient.post<User>('/api/users/', userData);
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/users/me');
    return response.data;
  }
};
