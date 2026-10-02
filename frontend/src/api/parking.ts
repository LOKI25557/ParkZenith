import { apiClient } from './client';
import type { Facility, Zone, Slot, Availability } from '../types';

export const parkingApi = {
  getFacilities: async (): Promise<Facility[]> => {
    const response = await apiClient.get<Facility[]>('/api/facilities/');
    return response.data;
  },
  
  getFacility: async (id: number): Promise<Facility> => {
    const response = await apiClient.get<Facility>(`/api/facilities/${id}`);
    return response.data;
  },

  getFacilityAvailability: async (id: number): Promise<Availability> => {
    const response = await apiClient.get<Availability>(`/api/facilities/${id}/availability`);
    return response.data;
  },

  getZones: async (facilityId: number): Promise<Zone[]> => {
    const response = await apiClient.get<Zone[]>(`/api/facilities/${facilityId}/zones/`);
    return response.data;
  },

  getSlots: async (zoneId: number): Promise<Slot[]> => {
    const response = await apiClient.get<Slot[]>(`/api/zones/${zoneId}/slots/`);
    return response.data;
  }
};
