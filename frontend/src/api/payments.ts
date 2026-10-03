import { apiClient } from './client';
import type { Payment, PaymentMethod } from '../types';

export const paymentsApi = {
  getMyPayments: async (): Promise<Payment[]> => {
    const response = await apiClient.get<Payment[]>('/api/payments/me');
    return response.data;
  },

  getPayment: async (id: number): Promise<Payment> => {
    const response = await apiClient.get<Payment>(`/api/payments/${id}`);
    return response.data;
  },

  createPayment: async (data: { session_id: number; amount: number; payment_method: PaymentMethod }): Promise<Payment> => {
    const response = await apiClient.post<Payment>('/api/payments/', data);
    return response.data;
  },

  processPayment: async (id: number, data: { simulate_success: boolean; transaction_id?: string; payment_method?: PaymentMethod }): Promise<Payment> => {
    const response = await apiClient.post<Payment>(`/api/payments/${id}/process`, data);
    return response.data;
  }
};
