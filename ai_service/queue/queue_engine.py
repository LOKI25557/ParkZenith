"""
Queue Engine coordinator.
Integrates estimation, prediction, congestion classification, waiting time, and confidence scoring.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .estimator import estimate_current_queue
from .predictor import predict_future_queue
from .waiting_time import estimate_waiting_time
from .congestion import classify_congestion

logger = logging.getLogger(__name__)

class QueueEngine:
    """
    QueueEngine coordinates the queue intelligence suite:
    estimating current queue length, predicting future queue length, calculating wait times,
    classifying congestion levels, and assessing prediction confidence.
    """

    @staticmethod
    def calculate_confidence(
        has_current_occupancy: bool,
        has_historical_sessions: bool,
        session_data_count: int,
        has_reservations: bool,
    ) -> float:
        """
        Calculates prediction confidence score (0-100) based on data availability and depth.
        """
        confidence = 50.0  # Base confidence
        
        # Current data availability (+20)
        if has_current_occupancy:
            confidence += 20.0
            
        # Historical sessions availability and depth (+20 max)
        if has_historical_sessions:
            if session_data_count >= 10:
                confidence += 20.0
            elif session_data_count > 0:
                confidence += 10.0
                
        # Reservation availability (+10)
        if has_reservations:
            confidence += 10.0
            
        # Clamp between 0 and 100
        return float(max(0.0, min(confidence, 100.0)))

    def process(
        self,
        facility_id: str,
        capacity: int,
        occupied_slots: int,
        arrival_rate_per_hour: float,
        departure_rate_per_hour: float,
        eta_minutes: int = 0,
        session_data_count: int = 0,
        has_reservations: bool = False,
        entry_throughput_per_minute: float = 3.0,
        actual_queue_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Runs the full queue estimation and prediction pipeline.
        
        Returns:
            Dict containing prediction and estimation metrics.
        """
        # 1. Check data presence flags
        has_current_occupancy = capacity > 0
        has_historical_sessions = session_data_count > 0 or arrival_rate_per_hour > 0.0 or departure_rate_per_hour > 0.0
        
        # 2. Current queue length estimation
        estimated_queue = estimate_current_queue(
            capacity=capacity,
            occupied_slots=occupied_slots,
            arrival_rate_per_hour=arrival_rate_per_hour,
            departure_rate_per_hour=departure_rate_per_hour,
            entry_throughput_per_minute=entry_throughput_per_minute,
        )
        
        current_queue = estimated_queue
        if actual_queue_length is not None:
            current_queue = max(float(actual_queue_length), estimated_queue)
        
        # 3. Future queue prediction
        predicted_queue, expected_arrivals, expected_departures, trend = predict_future_queue(
            current_queue_length=current_queue,
            arrival_rate_per_hour=arrival_rate_per_hour,
            departure_rate_per_hour=departure_rate_per_hour,
            eta_minutes=eta_minutes,
            capacity=capacity,
            occupied_slots=occupied_slots,
        )
        
        # 4. Entry waiting time prediction
        # For current queue:
        wait_time = estimate_waiting_time(
            queue_length=current_queue,
            capacity=capacity,
            occupied_slots=occupied_slots,
            departure_rate_per_hour=departure_rate_per_hour,
            entry_throughput_per_minute=entry_throughput_per_minute,
        )
        
        # 5. Congestion classification
        congestion = classify_congestion(
            queue_length=current_queue,
            capacity=capacity,
            occupied_slots=occupied_slots,
            waiting_time_minutes=wait_time,
        )
        
        # 6. Confidence calculation
        confidence = self.calculate_confidence(
            has_current_occupancy=has_current_occupancy,
            has_historical_sessions=has_historical_sessions,
            session_data_count=session_data_count,
            has_reservations=has_reservations,
        )
        
        congestion_status = "CRITICAL" if congestion == "SEVERE" else congestion
        
        return {
            "facility_id": facility_id,
            "timestamp": datetime.now(timezone.utc),
            "current_queue_length": current_queue,
            "predicted_queue_length": predicted_queue,
            "expected_arrivals": expected_arrivals,
            "expected_departures": expected_departures,
            "expected_wait_minutes": wait_time,
            "estimated_wait_minutes": wait_time,
            "queue_trend": trend,
            "congestion_level": congestion,
            "congestion_status": congestion_status,
            "confidence": confidence,
        }
