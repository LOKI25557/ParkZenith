import { apiClient } from './client';
import type { Facility, Zone, Slot, Availability, UnifiedFacilityIntelligence } from '../types';

export interface PaginationParams {
  skip?: number;
  limit?: number;
}

export const parkingApi = {
  getFacilities: async (params?: PaginationParams): Promise<Facility[]> => {
    const response = await apiClient.get<Facility[]>('/facilities', { params });
    return response.data;
  },

  getFacility: async (id: number): Promise<Facility> => {
    const response = await apiClient.get<Facility>(`/facilities/${id}`);
    return response.data;
  },

  getFacilityAvailability: async (id: number): Promise<Availability> => {
    const response = await apiClient.get<Availability>(`/facilities/${id}/availability`);
    return response.data;
  },

  getZones: async (facilityId: number, params?: PaginationParams): Promise<Zone[]> => {
    const response = await apiClient.get<Zone[]>(`/facilities/${facilityId}/zones`, { params });
    return response.data;
  },

  getZone: async (zoneId: number): Promise<Zone> => {
    const response = await apiClient.get<Zone>(`/zones/${zoneId}`);
    return response.data;
  },

  getZoneAvailability: async (zoneId: number): Promise<Availability> => {
    const response = await apiClient.get<Availability>(`/zones/${zoneId}/availability`);
    return response.data;
  },

  getSlots: async (zoneId: number, params?: PaginationParams): Promise<Slot[]> => {
    const response = await apiClient.get<Slot[]>(`/zones/${zoneId}/slots`, { params });
    return response.data;
  },

  getSlot: async (slotId: number): Promise<Slot> => {
    const response = await apiClient.get<Slot>(`/slots/${slotId}`);
    return response.data;
  },

  getFacilityIntelligence: async (facilityId: number, etaMinutes = 20): Promise<UnifiedFacilityIntelligence> => {
    const response = await apiClient.get<UnifiedFacilityIntelligence>(`/parking/intelligence/${facilityId}`, {
      params: { eta_minutes: etaMinutes },
    });
    return response.data;
  },
};
