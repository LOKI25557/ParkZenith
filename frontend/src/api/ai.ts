import { apiClient, aiClient } from './client';
import type {
  AvailabilityPrediction,
  OccupancyForecast,
  QueuePrediction,
  RecommendationRequest,
  RecommendationsResponse,
  UnifiedDecision,
  ZoneAnalytics,
} from '../types';

export const aiApi = {
  /**
   * Health ping to check prediction proxy status
   */
  checkAIHealth: async (): Promise<{ message: string }> => {
    const response = await apiClient.get('/prediction/ping');
    return response.data;
  },

  /**
   * Smart AI / DB-distance-ranked parking recommendations
   */
  getRecommendations: async (data: RecommendationRequest): Promise<RecommendationsResponse> => {
    try {
      const response = await apiClient.post<RecommendationsResponse>('/prediction/recommendations', data);
      return response.data;
    } catch {
      // Fallback directly to AI service port if available
      const response = await aiClient.post<RecommendationsResponse>('/api/recommendations', data);
      return response.data;
    }
  },

  /**
   * Realtime availability prediction at specific ETA horizon
   */
  getPrediction: async (
    facilityId: number | string,
    _targetTime?: string,
    etaMinutes: number = 20
  ): Promise<AvailabilityPrediction> => {
    try {
      const response = await apiClient.get<AvailabilityPrediction>(`/prediction/availability/${facilityId}`, {
        params: { eta_minutes: etaMinutes },
      });
      return response.data;
    } catch {
      // Direct AI service fallback if backend proxy errored
      const response = await aiClient.get<AvailabilityPrediction>(`/api/predictions/availability/${facilityId}`, {
        params: { target_time: _targetTime || new Date().toISOString() },
      });
      return response.data;
    }
  },

  /**
   * Temporal occupancy prediction forecast (15m, 30m, 60m)
   */
  getOccupancyForecast: async (
    facilityId: number | string,
    horizonMinutes: number = 15
  ): Promise<OccupancyForecast> => {
    const response = await apiClient.get<OccupancyForecast>(`/prediction/occupancy/${facilityId}`, {
      params: { horizon_minutes: horizonMinutes },
    });
    return response.data;
  },

  /**
   * Gate queue wait time and throughput telemetry
   */
  getQueueMetrics: async (
    facilityId: number | string,
    etaMinutes?: number
  ): Promise<QueuePrediction> => {
    const response = await apiClient.get<QueuePrediction>(`/prediction/queue/${facilityId}`, {
      params: etaMinutes !== undefined ? { eta_minutes: etaMinutes } : undefined,
    });
    return response.data;
  },

  /**
   * Unified orchestrator decision with alternatives and reasoning
   */
  getIntelligenceDecision: async (
    facilityId: number | string,
    params?: {
      eta_minutes?: number;
      latitude?: number;
      longitude?: number;
      destination_latitude?: number;
      destination_longitude?: number;
    }
  ): Promise<UnifiedDecision> => {
    const response = await apiClient.get<UnifiedDecision>(`/prediction/decision/${facilityId}`, {
      params: {
        eta_minutes: params?.eta_minutes ?? 20,
        latitude: params?.latitude,
        longitude: params?.longitude,
        destination_latitude: params?.destination_latitude,
        destination_longitude: params?.destination_longitude,
      },
    });
    return response.data;
  },

  /**
   * Consolidated AI Analytics Dashboard
   */
  getDashboard: async (params?: { facility_id?: string; eta_minutes?: number }): Promise<any> => {
    const response = await apiClient.get('/prediction/dashboard', {
      params,
    });
    return response.data;
  },

  /**
   * Live heatmap data across all monitored facilities
   */
  getLiveHeatmap: async (): Promise<any> => {
    const response = await apiClient.get('/heatmap/live');
    return response.data;
  },

  /**
   * Zone density analytics and congestion matrix
   */
  getZoneAnalytics: async (facilityId?: number | string): Promise<ZoneAnalytics> => {
    const response = await apiClient.get<ZoneAnalytics>('/heatmap/zones', {
      params: facilityId ? { facility_id: String(facilityId) } : undefined,
    });
    return response.data;
  },

  /**
   * Facility-specific heatmap metrics
   */
  getFacilityHeatmap: async (facilityId: number | string): Promise<any> => {
    const response = await apiClient.get(`/heatmap/facility/${facilityId}`);
    return response.data;
  },
};
