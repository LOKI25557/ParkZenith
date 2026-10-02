import { apiClient } from './client';
import type { Reservation } from '../types';

export const reservationsApi = {
  getReservations: async (): Promise<Reservation[]> => {
    const response = await apiClient.get('/api/reservations/');
    // Based on backend schema it might return { items: [...], total: ... }
    return response.data.items || response.data;
  },

  createReservation: async (data: { slot_id: number, reservation_start: string, reservation_end: string }): Promise<Reservation> => {
    const response = await apiClient.post<Reservation>('/api/reservations/', data);
    return response.data;
  },

  cancelReservation: async (id: number): Promise<Reservation> => {
    const response = await apiClient.delete<Reservation>(`/api/reservations/${id}`);
    return response.data;
  }
};
