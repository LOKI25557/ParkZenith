import { apiClient } from './client';
import type { Payment, PaymentProcessRequest } from '../types';

export interface PaginationParams {
  skip?: number;
  limit?: number;
}

export const paymentsApi = {
  getMyPayments: async (params?: PaginationParams): Promise<Payment[]> => {
    const response = await apiClient.get<Payment[]>('/payments/me', {
      params: {
        skip: params?.skip ?? 0,
        limit: params?.limit ?? 100,
      },
    });
    return response.data || [];
  },

  getPayment: async (id: number): Promise<Payment> => {
    const response = await apiClient.get<Payment>(`/payments/${id}`);
    return response.data;
  },

  getSessionPayment: async (sessionId: number): Promise<Payment> => {
    const response = await apiClient.get<Payment>(`/payments/session/${sessionId}`);
    return response.data;
  },

  processPayment: async (
    id: number,
    data: PaymentProcessRequest = { simulate_success: true }
  ): Promise<Payment> => {
    const response = await apiClient.post<Payment>(`/payments/${id}/process`, data);
    return response.data;
  },
};

