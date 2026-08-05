"""
ParkZenith Lightweight Async Performance Load Validation Script.
Simulates concurrent client requests to backend and AI service APIs.
Measures requests per second (RPS), average latency, peak latency, and error rates.
"""

import argparse
import asyncio
import time
from typing import List, Dict, Any
import httpx

# List of endpoints to hit during the load test
# We simulate user recommendations requests, availability predictions, queue prediction queries, and decisions.
BACKEND_ENDPOINTS = [
    {"method": "GET", "url": "/prediction/occupancy/1?horizon_minutes=15"},
    {"method": "GET", "url": "/prediction/availability/1?eta_minutes=20"},
    {
        "method": "POST",
        "url": "/prediction/recommendations",
        "json": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "eta_minutes": 20,
            "max_distance_km": 5.0,
            "max_results": 3,
        },
    },
    {"method": "GET", "url": "/prediction/queue/1?eta_minutes=20"},
    {"method": "GET", "url": "/prediction/decision/1?eta_minutes=20"},
]

AI_SERVICE_ENDPOINTS = [
    {"method": "GET", "url": "/forecasting/occupancy/1?horizon_minutes=15"},
    {"method": "GET", "url": "/availability/1?eta_minutes=20"},
    {
        "method": "POST",
        "url": "/recommendation",
        "json": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "eta_minutes": 20,
            "max_results": 3,
        },
    },
    {"method": "GET", "url": "/queue/1?eta_minutes=20"},
]


class PerformanceMetrics:
    def __init__(self):
        self.request_times: List[float] = []
        self.errors: int = 0
        self.success: int = 0


async def send_request(client: httpx.AsyncClient, base_url: str, endpoint: Dict[str, Any], metrics: PerformanceMetrics):
    """Sends a single HTTP request and measures its latency."""
    method = endpoint["method"]
    url = f"{base_url}{endpoint['url']}"
    payload = endpoint.get("json", None)

    start_time = time.time()
    try:
        if method == "POST":
            response = await client.post(url, json=payload, timeout=30.0)
        else:
            response = await client.get(url, timeout=30.0)

        latency = (time.time() - start_time) * 1000.0  # in ms
        
        if response.status_code in (200, 201):
            metrics.success += 1
            metrics.request_times.append(latency)
        else:
            metrics.errors += 1
    except Exception:
        metrics.errors += 1


async def worker(base_url: str, endpoints: List[Dict[str, Any]], metrics: PerformanceMetrics, duration: float, spawn_interval: float):
    """Worker task that continuously issues requests until duration expires."""
    async with httpx.AsyncClient() as client:
        end_time = time.time() + duration
        while time.time() < end_time:
            endpoint = endpoints[int(time.time() * 1000) % len(endpoints)]
            await send_request(client, base_url, endpoint, metrics)
            await asyncio.sleep(spawn_interval)


def print_results(metrics: PerformanceMetrics, total_duration: float, concurrency: int):
    """Formats and prints load test statistics."""
    total_requests = metrics.success + metrics.errors
    rps = total_requests / total_duration if total_duration > 0 else 0
    error_rate = (metrics.errors / total_requests * 100) if total_requests > 0 else 0.0

    print("\n" + "=" * 50)
    print(" [METRICS] PARKZENITH LOAD TEST PERFORMANCE RESULTS")
    print("=" * 50)
    print(f"Total Simulating Duration : {total_duration:.2f} seconds")
    print(f"Target Concurrency        : {concurrency} clients")
    print(f"Total Requests Executed   : {total_requests}")
    print(f"Successful Requests       : {metrics.success}")
    print(f"Failed / Error Requests   : {metrics.errors} ({error_rate:.2f}%)")
    print(f"System Throughput (RPS)   : {rps:.2f} requests/sec")
    
    if metrics.request_times:
        avg_latency = sum(metrics.request_times) / len(metrics.request_times)
        peak_latency = max(metrics.request_times)
        min_latency = min(metrics.request_times)
        # sort times for percentiles
        sorted_times = sorted(metrics.request_times)
        p95_latency = sorted_times[int(len(sorted_times) * 0.95)]
        
        print(f"Average Response Latency  : {avg_latency:.2f} ms")
        print(f"P95 Response Latency      : {p95_latency:.2f} ms")
        print(f"Peak Response Latency     : {peak_latency:.2f} ms")
        print(f"Min Response Latency      : {min_latency:.2f} ms")
    else:
        print("No successful responses received to calculate latencies.")
    print("=" * 50 + "\n")


async def main():
    parser = argparse.ArgumentParser(description="ParkZenith Performance Load Tester")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent client workers")
    parser.add_argument("--duration", type=float, default=5.0, help="Test duration in seconds")
    parser.add_argument("--target", type=str, default="backend", choices=["backend", "ai"], help="Target service to test")
    parser.add_argument("--host", type=str, default=None, help="Custom target host URL")

    args = parser.parse_args()

    if args.target == "backend":
        base_url = args.host or "http://localhost:8000"
        endpoints = BACKEND_ENDPOINTS
    else:
        base_url = args.host or "http://localhost:8001"
        endpoints = AI_SERVICE_ENDPOINTS

    print(f"\n[INFO] Initiating load test against {args.target.upper()} at {base_url}...")
    print(f"Parameters: Concurrency={args.concurrency} workers, Duration={args.duration}s")

    metrics = PerformanceMetrics()
    start_time = time.time()
    
    # Spawn worker coroutines
    tasks = []
    for _ in range(args.concurrency):
        # Stagger the starts slightly to simulate realistic ramp-up
        spawn_delay = 0.05
        tasks.append(worker(base_url, endpoints, metrics, args.duration, spawn_delay))
    
    await asyncio.gather(*tasks)
    total_duration = time.time() - start_time

    print_results(metrics, total_duration, args.concurrency)


if __name__ == "__main__":
    asyncio.run(main())
