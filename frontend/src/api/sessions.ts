import { apiClient } from './client';
import type { ParkingSession, SessionStartRequest } from '../types';

export const sessionsApi = {
  getSessions: async (skip: number = 0, limit: number = 100): Promise<ParkingSession[]> => {
    const response = await apiClient.get('/sessions', {
      params: { skip, limit },
    });
    return response.data.items || response.data || [];
  },

  getActiveSession: async (): Promise<ParkingSession | null> => {
    try {
      const response = await apiClient.get<ParkingSession>('/sessions/active');
      return response.data;
    } catch (err: any) {
      if (err.response?.status === 404) {
        return null;
      }
      throw err;
    }
  },

  getSession: async (id: number): Promise<ParkingSession> => {
    const response = await apiClient.get<ParkingSession>(`/sessions/${id}`);
    return response.data;
  },

  startSession: async (data: SessionStartRequest): Promise<ParkingSession> => {
    const response = await apiClient.post<ParkingSession>('/sessions/start', data);
    return response.data;
  },

  endSession: async (id: number): Promise<ParkingSession> => {
    const response = await apiClient.post<ParkingSession>(`/sessions/${id}/end`);
    return response.data;
  },
};

