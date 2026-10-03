import { apiClient } from './client';
import type { Reservation, ReservationCreateRequest } from '../types';

export const reservationsApi = {
  getReservations: async (): Promise<Reservation[]> => {
    const response = await apiClient.get('/reservations');
    // Backend schema returns { items: [...], total: ... }
    return response.data.items || response.data || [];
  },

  getReservation: async (id: number): Promise<Reservation> => {
    try {
      const response = await apiClient.get<Reservation>(`/reservations/${id}`);
      return response.data;
    } catch {
      // Fallback if backend only exposes list endpoint for user
      const list = await reservationsApi.getReservations();
      const found = list.find((r) => r.id === id);
      if (!found) {
        throw new Error(`Reservation #${id} not found`);
      }
      return found;
    }
  },

  createReservation: async (data: ReservationCreateRequest): Promise<Reservation> => {
    const response = await apiClient.post<Reservation>('/reservations', data);
    return response.data;
  },

  cancelReservation: async (id: number): Promise<Reservation> => {
    const response = await apiClient.delete<Reservation>(`/reservations/${id}`);
    return response.data;
  },
};

