"""
Deterministic ranking module for candidate facilities.
"""

from typing import Dict, Any, List


def rank_facilities(scored_facilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ranks facilities from best to worst based on recommendation_score descending.
    Sorts deterministically for identical scores by distance_km ascending, then facility_id ascending.
    Injects a 1-indexed 'rank' field into each dictionary.
    """
    # Deterministic sorting key:
    # 1. recommendation_score (descending, so negate)
    # 2. distance_km (ascending)
    # 3. facility_id (ascending, converted to string/integer representation for comparison)
    def sort_key(item: Dict[str, Any]):
        score = float(item.get("recommendation_score", 0.0))
        dist = float(item.get("distance_km", 0.0))
        fid = str(item.get("facility_id", ""))
        return (-score, dist, fid)

    ranked = sorted(scored_facilities, key=sort_key)

    # Assign rank number
    for index, item in enumerate(ranked):
        item["rank"] = index + 1

    return ranked
