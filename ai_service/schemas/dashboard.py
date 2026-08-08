"""
Pydantic response schemas for the AI Analytics Dashboard.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class AIInsight(BaseModel):
    """
    Represents a single actionable natural language insight.
    """
    type: str = Field(..., description="Insight category (e.g. occupancy, queue, events, heatmap)")
    severity: str = Field(..., description="Severity level of the insight (e.g. INFO, WARNING, CRITICAL)")
    message: str = Field(..., description="Actionable text description of the insight")


class OccupancyDashboard(BaseModel):
    """
    Occupancy analytics section for the dashboard.
    """
    facility_id: Optional[str] = Field(None, description="Identifier of the facility")
    current_occupancy: float = Field(..., description="Current occupancy percentage")
    total_capacity: int = Field(..., description="Total slots capacity")
    available_spaces: int = Field(..., description="Available slots count")
    occupied_spaces: int = Field(..., description="Occupied slots count")
    reserved_spaces: int = Field(..., description="Reserved slots count")
    utilization_percentage: float = Field(..., description="Average utilization percentage over period")
    historical_occupancy: List[Dict[str, Any]] = Field(default_factory=list, description="Historical occupancy trend list")
    peak_occupancy: float = Field(..., description="Peak occupancy percentage seen in the window")
    peak_hours: List[int] = Field(default_factory=list, description="Busiest hours (0-23) list")
    occupancy_trends: Dict[str, Any] = Field(default_factory=dict, description="Detailed trend patterns")


class ForecastDashboard(BaseModel):
    """
    Occupancy forecasting section for the dashboard.
    """
    forecast_30m: float = Field(..., description="Expected occupancy percentage in 30 minutes")
    forecast_60m: float = Field(..., description="Expected occupancy percentage in 60 minutes")
    forecast_horizon: List[Dict[str, Any]] = Field(default_factory=list, description="List of forecast horizons (e.g. 15, 30, 60 minutes)")
    confidence: float = Field(..., description="Model forecast confidence score (0.0 to 1.0)")
    expected_demand: float = Field(..., description="Expected parking demand score")
    expected_occupancy: float = Field(..., description="Average expected occupancy percentage")
    peak_demand_window: Optional[str] = Field(None, description="Predicted peak demand timeframe")
    event_adjusted_forecast: Optional[float] = Field(None, description="Event-adjusted expected occupancy at ETA")


class AvailabilityDashboard(BaseModel):
    """
    Arrival availability prediction section for the dashboard.
    """
    arrival_availability_probability: float = Field(..., description="Availability probability at arrival ETA (0.0 to 1.0 or 0 to 100)")
    eta_minutes: int = Field(..., description="Estimated arrival time offset in minutes")
    expected_occupancy_at_arrival: float = Field(..., description="Expected occupancy percentage at arrival")
    available_capacity: int = Field(..., description="Expected vacant slots at arrival")
    confidence: float = Field(..., description="Availability prediction confidence score (0.0 to 1.0)")
    risk_level: str = Field(..., description="Occupancy risk level at arrival (LOW, MEDIUM, HIGH)")


class RecommendationItem(BaseModel):
    """
    Represents a recommended facility in dashboard recommendations.
    """
    facility_id: str = Field(..., description="Facility Identifier")
    facility_name: str = Field(..., description="Facility Name")
    score: float = Field(..., description="Recommendation score (0.0 to 1.0 or 0 to 100)")
    distance_km: float = Field(..., description="Distance from user coordinates in kilometers")
    expected_occupancy: float = Field(..., description="Expected occupancy percentage")
    expected_queue: float = Field(..., description="Expected queue waiting time in minutes")
    walking_distance: int = Field(..., description="Walking distance in meters")
    event_impact: float = Field(..., description="Additional demand impact from nearby events")
    confidence: float = Field(..., description="Recommendation confidence level")


class RecommendationDashboard(BaseModel):
    """
    Smart Recommendations section for the dashboard.
    """
    recommended_facilities: List[RecommendationItem] = Field(default_factory=list, description="Ranked recommendations list")
    summary_insights: List[str] = Field(default_factory=list, description="Actionable recommendation insights")


class QueueDashboard(BaseModel):
    """
    Virtual queue and queue prediction section for the dashboard.
    """
    current_queue_estimate: int = Field(..., description="Current virtual queue length")
    predicted_waiting_time: float = Field(..., description="Estimated waiting time in minutes")
    congestion_level: str = Field(..., description="Current queue congestion level")
    queue_growth: float = Field(..., description="Rate of queue size growth")
    peak_queue_period: Optional[str] = Field(None, description="Time window when queue is expected to be longest")
    event_adjusted_queue_prediction: Optional[float] = Field(None, description="Event-adjusted waiting time in minutes")


class ZoneHeatmapItem(BaseModel):
    """
    Represents zone congestion item in heatmap section.
    """
    zone_id: str = Field(..., description="Zone Identifier")
    congestion_score: float = Field(..., description="Congestion score (0.0 to 1.0)")
    density: float = Field(..., description="Occupancy density percentage")
    utilization: float = Field(..., description="Zone utilization percentage")


class HeatmapDashboard(BaseModel):
    """
    AI Heatmap analytics section for the dashboard.
    """
    zone_congestion: List[ZoneHeatmapItem] = Field(default_factory=list, description="Congestion statistics per zone")
    most_congested_zones: List[str] = Field(default_factory=list, description="List of most busy zones")
    least_congested_zones: List[str] = Field(default_factory=list, description="List of least busy zones")
    peak_congestion_period: Optional[str] = Field(None, description="Period of peak congestion")
    historical_comparison: Dict[str, Any] = Field(default_factory=dict, description="Comparison with historical periods")


class EventDashboard(BaseModel):
    """
    Event-aware intelligence section for the dashboard.
    """
    active_events: List[Dict[str, Any]] = Field(default_factory=list, description="List of active events")
    upcoming_events: List[Dict[str, Any]] = Field(default_factory=list, description="List of upcoming events within 24 hours")
    event_impact: Dict[str, Any] = Field(default_factory=dict, description="Active event composite impact")
    expected_demand_increase: float = Field(..., description="Expected demand percentage increase")
    affected_facilities: List[str] = Field(default_factory=list, description="List of facilities affected by events")
    congestion_risk: str = Field(..., description="Congestion risk level (LOW, MEDIUM, HIGH, SEVERE)")
    event_adjusted_occupancy: float = Field(..., description="Occupancy percentage adjusted for active events")
    event_adjusted_queue_estimates: float = Field(..., description="Queue wait minutes adjusted for events")


class ModelPerformance(BaseModel):
    """
    Model performance and accuracy evaluation metrics section.
    """
    prediction_accuracy: float = Field(..., description="Average prediction accuracy percentage")
    error_metrics: Dict[str, float] = Field(default_factory=dict, description="Dictionary of error metrics (e.g. MAE, RMSE, MAPE)")
    confidence: float = Field(..., description="Average prediction confidence")
    forecast_performance: Dict[str, Any] = Field(default_factory=dict, description="Forecast model specific performance")
    availability_prediction_performance: Dict[str, Any] = Field(default_factory=dict, description="Availability model specific performance")
    recommendation_performance: Dict[str, Any] = Field(default_factory=dict, description="Recommendation evaluation metrics")
    queue_prediction_performance: Dict[str, Any] = Field(default_factory=dict, description="Queue prediction evaluation metrics")


class DashboardSummary(BaseModel):
    """
    High-level overview summary indicators.
    """
    status: str = Field(..., description="Overall status indicator (e.g. NORMAL, WARNING, CRITICAL)")
    timestamp: datetime = Field(..., description="Aggregation timestamp")
    total_facilities_monitored: int = Field(..., description="Number of facilities aggregated in this view")


class AIOverview(BaseModel):
    """
    Unified Master AI Dashboard Overview Schema.
    """
    occupancy: OccupancyDashboard = Field(..., description="Occupancy dashboard metrics")
    forecast: ForecastDashboard = Field(..., description="Forecasting dashboard metrics")
    availability: AvailabilityDashboard = Field(..., description="Availability prediction dashboard metrics")
    recommendations: RecommendationDashboard = Field(..., description="Smart recommendations analytics")
    queue: QueueDashboard = Field(..., description="Queue predictions and waiting times")
    heatmap: HeatmapDashboard = Field(..., description="Zone level heatmap analytics")
    events: EventDashboard = Field(..., description="Event aware intelligence analytics")
    performance: ModelPerformance = Field(..., description="Model evaluation and performance metrics")
    insights: List[AIInsight] = Field(default_factory=list, description="Consolidated natural language actionable insights")
    summary: DashboardSummary = Field(..., description="High-level dashboard summary metadata")
