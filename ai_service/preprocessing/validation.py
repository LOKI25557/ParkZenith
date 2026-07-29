"""
Validation module for ParkZenith Preprocessing Pipeline.
Implements schema and boundary check validation for occupancy, reservation, and session datasets.
"""

from typing import Dict, Any, List
import pandas as pd


def _check_missing_columns(df: pd.DataFrame, expected: List[str]) -> List[str]:
    """Helper to find missing columns."""
    missing = []
    for col in expected:
        if col not in df.columns:
            missing.append(col)
    return missing


def validate_occupancy_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validates the schema and boundary conditions of occupancy history data.
    """
    errors = []
    warnings = []
    
    # 1. Check columns
    required_cols = ["facility_id", "total_slots", "occupied_slots", "occupancy_percentage", "collected_at"]
    missing = _check_missing_columns(df, required_cols)
    if missing:
        errors.append(f"Missing required columns: {missing}")
        return {"valid": False, "row_count": len(df), "errors": errors, "warnings": warnings}

    if len(df) == 0:
        errors.append("Dataset is empty.")
        return {"valid": False, "row_count": 0, "errors": errors, "warnings": warnings}

    # 2. Check types & values
    if (df["total_slots"] <= 0).any():
        errors.append("Dataset contains records where total_slots is less than or equal to 0.")

    if (df["occupied_slots"] < 0).any():
        errors.append("Dataset contains negative occupied_slots values.")

    # Check occupancy percent boundary
    pct_out_of_bounds = (df["occupancy_percentage"] < 0) | (df["occupancy_percentage"] > 100)
    if pct_out_of_bounds.any():
        warnings.append(f"Found {pct_out_of_bounds.sum()} records with occupancy_percentage outside [0, 100].")

    # Check if occupied_slots exceeds total_slots
    occupied_exceeds_total = df["occupied_slots"] > df["total_slots"]
    if occupied_exceeds_total.any():
        warnings.append(f"Found {occupied_exceeds_total.sum()} records where occupied_slots > total_slots.")

    # 3. Check for null values
    null_counts = df[required_cols].isnull().sum()
    for col, count in null_counts.items():
        if count > 0:
            errors.append(f"Column '{col}' has {count} missing values.")

    return {
        "valid": len(errors) == 0,
        "row_count": len(df),
        "errors": errors,
        "warnings": warnings,
    }


def validate_reservation_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validates schema and constraints for reservation history data.
    """
    errors = []
    warnings = []

    required_cols = [
        "reservation_id",
        "facility_id",
        "slot_id",
        "reservation_status",
        "reservation_start",
        "reservation_end",
        "duration_minutes",
        "collected_at",
    ]
    missing = _check_missing_columns(df, required_cols)
    if missing:
        errors.append(f"Missing required columns: {missing}")
        return {"valid": False, "row_count": len(df), "errors": errors, "warnings": warnings}

    if len(df) == 0:
        errors.append("Dataset is empty.")
        return {"valid": False, "row_count": 0, "errors": errors, "warnings": warnings}

    # Verify duration
    negative_duration = df["duration_minutes"] < 0
    if negative_duration.any():
        errors.append(f"Found {negative_duration.sum()} records with negative duration_minutes.")

    # Chronology validation
    invalid_dates = df["reservation_start"] > df["reservation_end"]
    if invalid_dates.any():
        errors.append(f"Found {invalid_dates.sum()} records where reservation_start > reservation_end.")

    # Check for null values
    null_counts = df[required_cols].isnull().sum()
    for col, count in null_counts.items():
        if count > 0:
            errors.append(f"Column '{col}' has {count} missing (NaN) values.")

    return {
        "valid": len(errors) == 0,
        "row_count": len(df),
        "errors": errors,
        "warnings": warnings,
    }


def validate_session_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validates schema and constraints for parking session history data.
    """
    errors = []
    warnings = []

    required_cols = [
        "session_id",
        "facility_id",
        "vehicle_type",
        "check_in_time",
        "check_out_time",
        "duration_minutes",
        "parking_fee",
        "collected_at",
    ]
    
    # Exclude check_out_time, duration_minutes, parking_fee from strict non-null check since active sessions won't have them.
    strict_required = ["session_id", "facility_id", "vehicle_type", "check_in_time", "collected_at"]
    
    missing = _check_missing_columns(df, required_cols)
    if missing:
        errors.append(f"Missing required columns: {missing}")
        return {"valid": False, "row_count": len(df), "errors": errors, "warnings": warnings}

    if len(df) == 0:
        errors.append("Dataset is empty.")
        return {"valid": False, "row_count": 0, "errors": errors, "warnings": warnings}

    # Null values in primary columns
    null_counts = df[strict_required].isnull().sum()
    for col, count in null_counts.items():
        if count > 0:
            errors.append(f"Column '{col}' has {count} missing values.")

    # Validate chronology for completed sessions
    completed_mask = df["check_out_time"].notna()
    if completed_mask.any():
        completed_sessions = df[completed_mask]
        invalid_dates = completed_sessions["check_in_time"] > completed_sessions["check_out_time"]
        if invalid_dates.any():
            errors.append(f"Found {invalid_dates.sum()} completed sessions with check_in_time > check_out_time.")

        # Validate duration_minutes
        negative_duration = completed_sessions["duration_minutes"] < 0
        if negative_duration.any():
            errors.append(f"Found {negative_duration.sum()} completed sessions with negative duration_minutes.")

        # Validate parking fee
        negative_fees = completed_sessions["parking_fee"] < 0
        if negative_fees.any():
            errors.append(f"Found {negative_fees.sum()} completed sessions with negative parking_fee.")

    return {
        "valid": len(errors) == 0,
        "row_count": len(df),
        "errors": errors,
        "warnings": warnings,
    }
