import threading
from collections import defaultdict
from typing import Dict, Any

class MetricsRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self.request_counts = defaultdict(int)
        self.request_latencies = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.ai_service_latencies = []
        self.ai_service_failures = 0
        self.db_failures = 0
        self.prediction_failures = 0
        
    def record_request(self, endpoint: str, status_code: int, latency_ms: float):
        with self._lock:
            key = f"{endpoint}:{status_code}"
            self.request_counts[key] += 1
            self.request_latencies[endpoint].append(latency_ms)
            # limit in-memory storage size to prevent memory leaks
            if len(self.request_latencies[endpoint]) > 100:
                self.request_latencies[endpoint].pop(0)
            if status_code >= 400:
                self.error_counts[endpoint] += 1

    def record_ai_latency(self, latency_ms: float, success: bool):
        with self._lock:
            self.ai_service_latencies.append(latency_ms)
            if len(self.ai_service_latencies) > 100:
                self.ai_service_latencies.pop(0)
            if not success:
                self.ai_service_failures += 1

    def record_db_failure(self):
        with self._lock:
            self.db_failures += 1

    def record_prediction_failure(self):
        with self._lock:
            self.prediction_failures += 1

    def get_metrics_summary(self) -> Dict[str, Any]:
        with self._lock:
            summary = {
                "request_counts": dict(self.request_counts),
                "error_counts": dict(self.error_counts),
                "ai_service_failures": self.ai_service_failures,
                "db_failures": self.db_failures,
                "prediction_failures": self.prediction_failures,
                "avg_latencies": {},
            }
            for ep, lats in self.request_latencies.items():
                summary["avg_latencies"][ep] = round(sum(lats) / len(lats), 2) if lats else 0.0
            summary["avg_ai_service_latency"] = round(sum(self.ai_service_latencies) / len(self.ai_service_latencies), 2) if self.ai_service_latencies else 0.0
            return summary

metrics = MetricsRegistry()
