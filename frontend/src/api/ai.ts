import { apiClient, aiClient } from './client';

export const aiApi = {
  getRecommendations: async (data: { 
    latitude: number;
    longitude: number;
    eta_minutes?: number;
    max_distance_km?: number;
    max_results?: number;
    destination_latitude?: number;
    destination_longitude?: number;
  }): Promise<any> => {
    try {
      // First try backend prediction proxy which has built-in DB fallbacks
      const response = await apiClient.post('/api/prediction/recommendations', data);
      return response.data;
    } catch {
      // Fallback directly to AI service port if available
      const response = await aiClient.post('/api/recommendations', data);
      return response.data;
    }
  },
  
  getPrediction: async (facilityId: number, targetTime?: string, etaMinutes: number = 20): Promise<any> => {
    try {
      const response = await apiClient.get(`/api/prediction/availability/${facilityId}`, {
        params: { eta_minutes: etaMinutes }
      });
      return response.data;
    } catch {
      const response = await aiClient.get(`/api/predictions/availability/${facilityId}`, {
        params: { target_time: targetTime || new Date().toISOString() }
      });
      return response.data;
    }
  },

  getOccupancyForecast: async (facilityId: number, horizonMinutes: number = 15): Promise<any> => {
    const response = await apiClient.get(`/api/prediction/occupancy/${facilityId}`, {
      params: { horizon_minutes: horizonMinutes }
    });
    return response.data;
  },

  getQueueMetrics: async (facilityId: number, etaMinutes?: number): Promise<any> => {
    const response = await apiClient.get(`/api/prediction/queue/${facilityId}`, {
      params: etaMinutes !== undefined ? { eta_minutes: etaMinutes } : undefined
    });
    return response.data;
  },

  getDashboard: async (params?: { facility_id?: string; eta_minutes?: number }): Promise<any> => {
    const response = await apiClient.get('/api/prediction/dashboard', {
      params
    });
    return response.data;
  },

  getLiveHeatmap: async (): Promise<any> => {
    const response = await apiClient.get('/api/heatmap/live');
    return response.data;
  },

  getZoneAnalytics: async (facilityId?: number): Promise<any> => {
    const response = await apiClient.get('/api/heatmap/zones', {
      params: facilityId ? { facility_id: String(facilityId) } : undefined
    });
    return response.data;
  }
};
