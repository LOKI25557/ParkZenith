"""
Recommendation Engine package initialization.
"""

from .weights import WeightConfiguration, DEFAULT_WEIGHTS, get_facility_metadata
from .scoring import RecommendationScorer
from .ranking import rank_facilities
from .filters import calculate_distance_km, filter_candidate_facilities
from .explanation import generate_recommendation_reason
from .recommendation_engine import RecommendationEngine

__all__ = [
    "WeightConfiguration",
    "DEFAULT_WEIGHTS",
    "get_facility_metadata",
    "RecommendationScorer",
    "rank_facilities",
    "calculate_distance_km",
    "filter_candidate_facilities",
    "generate_recommendation_reason",
    "RecommendationEngine",
]
