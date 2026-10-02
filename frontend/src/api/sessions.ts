import { apiClient } from './client';
import type { ParkingSession } from '../types';

export const sessionsApi = {
  getSessions: async (): Promise<ParkingSession[]> => {
    const response = await apiClient.get('/api/sessions/');
    return response.data.items || response.data;
  },

  startSession: async (data: { slot_id: number, reservation_id?: number }): Promise<ParkingSession> => {
    const response = await apiClient.post<ParkingSession>('/api/sessions/', data);
    return response.data;
  },

  endSession: async (id: number): Promise<ParkingSession> => {
    const response = await apiClient.post<ParkingSession>(`/api/sessions/${id}/end`);
    return response.data;
  }
};
