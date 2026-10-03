import { apiClient } from './client';
import type {
  User,
  Token,
  UserLoginRequest,
  UserRegisterRequest,
  UserUpdateRequest,
} from '../types';

export const authApi = {
  login: async (credentials: UserLoginRequest): Promise<Token> => {
    const response = await apiClient.post<Token>('/auth/login', credentials);
    return response.data;
  },

  register: async (userData: UserRegisterRequest): Promise<User> => {
    const response = await apiClient.post<User>('/auth/register', userData);
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },

  updateProfile: async (data: UserUpdateRequest): Promise<User> => {
    const response = await apiClient.put<User>('/users/profile', data);
    return response.data;
  },
};
