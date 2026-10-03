import { apiClient } from './client';
import type {
  Facility,
  Zone,
  Slot,
  Availability,
  UnifiedFacilityIntelligence,
  FacilityCreateRequest,
  FacilityUpdateRequest,
  ZoneCreateRequest,
  ZoneUpdateRequest,
  SlotCreateRequest,
  SlotUpdateRequest,
  ParkingSlotStatus,
} from '../types';

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

  createFacility: async (data: FacilityCreateRequest): Promise<Facility> => {
    const response = await apiClient.post<Facility>('/facilities', data);
    return response.data;
  },

  updateFacility: async (id: number, data: FacilityUpdateRequest): Promise<Facility> => {
    const response = await apiClient.patch<Facility>(`/facilities/${id}`, data);
    return response.data;
  },

  deleteFacility: async (id: number): Promise<void> => {
    await apiClient.delete(`/facilities/${id}`);
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

  createZone: async (facilityId: number, data: ZoneCreateRequest): Promise<Zone> => {
    const response = await apiClient.post<Zone>(`/facilities/${facilityId}/zones`, data);
    return response.data;
  },

  updateZone: async (zoneId: number, data: ZoneUpdateRequest): Promise<Zone> => {
    const response = await apiClient.patch<Zone>(`/zones/${zoneId}`, data);
    return response.data;
  },

  deleteZone: async (zoneId: number): Promise<void> => {
    await apiClient.delete(`/zones/${zoneId}`);
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

  createSlot: async (zoneId: number, data: SlotCreateRequest): Promise<Slot> => {
    const response = await apiClient.post<Slot>(`/zones/${zoneId}/slots`, data);
    return response.data;
  },

  updateSlot: async (slotId: number, data: SlotUpdateRequest): Promise<Slot> => {
    const response = await apiClient.patch<Slot>(`/slots/${slotId}`, data);
    return response.data;
  },

  updateSlotStatus: async (slotId: number, status: ParkingSlotStatus): Promise<Slot> => {
    const response = await apiClient.patch<Slot>(`/slots/${slotId}/status`, { status });
    return response.data;
  },

  deleteSlot: async (slotId: number): Promise<void> => {
    await apiClient.delete(`/slots/${slotId}`);
  },

  getFacilityIntelligence: async (facilityId: number, etaMinutes = 20): Promise<UnifiedFacilityIntelligence> => {
    const response = await apiClient.get<UnifiedFacilityIntelligence>(`/parking/intelligence/${facilityId}`, {
      params: { eta_minutes: etaMinutes },
    });
    return response.data;
  },
};
