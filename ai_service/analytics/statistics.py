"""
Utility functions for calculating descriptive statistics safely on Pandas series.
"""

from typing import List, Dict
import numpy as np
import pandas as pd


def safe_mean(series: pd.Series) -> float:
    """
    Computes the mean of a Pandas Series. Returns 0.0 if empty or all NaN.
    """
    if series.empty or series.isna().all():
        return 0.0
    return float(np.round(series.mean(), 2))


def safe_median(series: pd.Series) -> float:
    """
    Computes the median of a Pandas Series. Returns 0.0 if empty or all NaN.
    """
    if series.empty or series.isna().all():
        return 0.0
    return float(np.round(series.median(), 2))


def safe_min(series: pd.Series) -> float:
    """
    Computes the minimum of a Pandas Series. Returns 0.0 if empty or all NaN.
    """
    if series.empty or series.isna().all():
        return 0.0
    return float(np.round(series.min(), 2))


def safe_max(series: pd.Series) -> float:
    """
    Computes the maximum of a Pandas Series. Returns 0.0 if empty or all NaN.
    """
    if series.empty or series.isna().all():
        return 0.0
    return float(np.round(series.max(), 2))


def safe_std(series: pd.Series) -> float:
    """
    Computes the standard deviation of a Pandas Series. Returns 0.0 if empty or all NaN.
    """
    if series.empty or series.isna().all() or len(series.dropna()) < 2:
        return 0.0
    return float(np.round(series.std(), 2))


def calculate_distribution(series: pd.Series, bins: List[float], labels: List[str]) -> Dict[str, int]:
    """
    Computes the frequency distribution of a series based on specified bins and labels.
    Returns a dictionary of counts.
    """
    if series.empty or series.isna().all():
        return {label: 0 for label in labels}
    
    # Categorize elements into bins
    categorized = pd.cut(series, bins=bins, labels=labels, right=False)
    counts = categorized.value_counts()
    
    # Fill in any missing categories with count 0
    return {str(label): int(counts.get(label, 0)) for label in labels}
