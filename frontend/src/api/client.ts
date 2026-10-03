import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const AI_SERVICE_URL = import.meta.env.VITE_AI_SERVICE_URL || 'http://127.0.0.1:8001';

// Main backend API client
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// AI Service API client
export const aiClient = axios.create({
  baseURL: AI_SERVICE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const TOKEN_STORAGE_KEY = 'parkzenith_token';

export const getStoredToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
};

export const setStoredToken = (token: string): void => {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch (e) {
    console.error('Failed to save authentication token to localStorage', e);
  }
};

export const removeStoredToken = (): void => {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch (e) {
    console.error('Failed to remove authentication token from localStorage', e);
  }
};

// Interceptor to attach the JWT token to requests
const authInterceptor = (config: any) => {
  const token = getStoredToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

apiClient.interceptors.request.use(authInterceptor);
aiClient.interceptors.request.use(authInterceptor);

// Global response interceptor for handling 401 Unauthorized
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url = String(error.config?.url || '');
      // Do not trigger global unauthorized event if the user is currently submitting login or register
      if (!url.includes('/auth/login') && !url.includes('/auth/register')) {
        removeStoredToken();
        window.dispatchEvent(new Event('unauthorized'));
      }
    }
    return Promise.reject(error);
  }
);
