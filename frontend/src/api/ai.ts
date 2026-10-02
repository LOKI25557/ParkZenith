import { aiClient } from './client';

export const aiApi = {
  getRecommendations: async (data: { 
    latitude: number, 
    longitude: number, 
    eta_minutes?: number, 
    max_distance_km?: number, 
    max_results?: number 
  }): Promise<any> => {
    const response = await aiClient.post('/api/recommendations', data);
    return response.data;
  },
  
  getPrediction: async (facilityId: number, targetTime: string): Promise<any> => {
    const response = await aiClient.get(`/api/predictions/availability/${facilityId}`, {
      params: { target_time: targetTime }
    });
    return response.data;
  }
};
