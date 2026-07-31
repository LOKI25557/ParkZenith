"""
Custom explanation generation module for parking recommendations.
"""

from typing import Dict, Any, List


def generate_recommendation_reason(scores: Dict[str, float]) -> str:
    """
    Generates a human-readable explanation summarizing the strongest positive factors.
    Looks at the individual normalized scores.
    """
    # Mapping of score factors to human-friendly positive descriptions
    descriptions = {
        "availability_score": "high arrival availability",
        "distance_score": "short distance",
        "forecast_score": "low forecasted congestion",
        "occupancy_score": "low current occupancy",
        "walking_score": "short walking distance",
        "utilization_score": "optimal utilization",
        "cost_score": "low parking fee",
        "queue_score": "minimal queue wait times",
    }

    # Sort scores descending
    sorted_factors = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Filter factors that have high scores (e.g. >= 70)
    positive_factors: List[str] = []
    for factor_name, score_val in sorted_factors:
        if score_val >= 70.0 and factor_name in descriptions:
            positive_factors.append(descriptions[factor_name])

    # If no factors are >= 70, take the top 2 highest factors
    if not positive_factors:
        for factor_name, _ in sorted_factors[:2]:
            if factor_name in descriptions:
                positive_factors.append(descriptions[factor_name])

    # Slice to top 3 factors for brevity and cleanliness
    positive_factors = positive_factors[:3]

    # Combine into a natural sentence structure
    if len(positive_factors) == 1:
        reason = f"Recommended due to {positive_factors[0]}."
    elif len(positive_factors) == 2:
        reason = f"Recommended due to {positive_factors[0]} and {positive_factors[1]}."
    else:
        # e.g., "High availability, low forecasted congestion and short walking distance"
        # Let's make it capitalized and flow nicely
        factors_str = f"{positive_factors[0]}, {positive_factors[1]} and {positive_factors[2]}"
        # Capitalize the first letter
        reason = factors_str[0].upper() + factors_str[1:]

    return reason
