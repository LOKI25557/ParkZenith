from typing import List, Optional
from pydantic import BaseModel, Field

class UnifiedFacilityIntelligence(BaseModel):
    facility_id: int
    
    # Real-time DB state
    total_slots: int
    available_slots: int
    occupied_slots: int
    reserved_slots: int
    current_occupancy_percentage: float
    
    # AI Predictions
    predicted_occupancy_percentage: Optional[float] = None
    predicted_availability_probability: Optional[float] = None
    expected_free_slots: Optional[int] = None
    queue_wait_minutes: Optional[float] = None
    
    # Recommendations & Status
    recommendation: Optional[str] = None
    occupancy_risk: Optional[str] = None
    prediction_status: str
    reasoning: List[str] = Field(default_factory=list)

class EnrichedRecommendation(BaseModel):
    rank: int
    facility_id: str
    facility_name: str
    recommendation_score: float
    
    # Enriched real-time DB data
    actual_available_slots: int
    actual_occupancy_percentage: float
    
    # AI Predictions
    availability_probability: float
    forecast_occupancy: float
    distance_km: float
    walking_distance_m: int
    estimated_cost: float
    queue_wait_minutes: float
    occupancy_risk: str
    confidence: float
    reason: str

class UnifiedRecommendationResponse(BaseModel):
    recommendations: List[EnrichedRecommendation]
    total_candidates: int
    returned_results: int
