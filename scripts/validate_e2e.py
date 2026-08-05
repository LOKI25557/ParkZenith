"""
ParkZenith End-to-End (E2E) System Validation Script.
Verifies the complete integration cycle between the Backend API and AI Service:
1. User registration & login.
2. Querying AI-based facility recommendations.
3. Fetching facility arrival availability predictions.
4. Creating a slot reservation.
5. Fetching queue forecasts and ETA waiting times.
6. Triggering the data collector sync cycle on the AI Service.
"""

import asyncio
import os
import random
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
import httpx


async def run_server(command: str) -> subprocess.Popen:
    """Spawns a server process in the background."""
    print(f"[INFO] Spawning background server: {command}")
    process = subprocess.Popen(
        command,
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    return process


def terminate_process(process: subprocess.Popen):
    """Gracefully terminates a spawned process tree."""
    if process:
        print(f"[INFO] Terminating process {process.pid}...")
        if sys.platform == "win32":
            subprocess.run(
                f"taskkill /F /T /PID {process.pid}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()


async def wait_for_port(port: int, timeout: float = 15.0) -> bool:
    """Waits until a port is responding to HTTP queries."""
    start_time = time.time()
    url = f"http://localhost:{port}/ready"
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                res = await client.get(url, timeout=1.0)
                if res.status_code in (200, 503):
                    return True
            except httpx.RequestError:
                pass
            await asyncio.sleep(0.5)
    return False


async def run_e2e_cycle():
    """Executes the complete E2E scenario validation."""
    print("\n--- 1. Authenticating E2E Client ---")
    test_num = random.randint(1000, 9999)
    test_email = f"e2e-client-{test_num}@parkzenith.com"
    test_password = "E2EPassword123!"

    async with httpx.AsyncClient() as client:
        # Register user
        reg_res = await client.post(
            "http://localhost:8000/auth/register",
            json={"email": test_email, "password": test_password, "full_name": "E2E Tester"}
        )
        print(f"Register User: {reg_res.status_code} - {reg_res.json()}")
        assert reg_res.status_code == 201, f"User registration failed: {reg_res.text}"

        # Login
        login_res = await client.post(
            "http://localhost:8000/auth/login",
            json={"email": test_email, "password": test_password}
        )
        print(f"Login User: {login_res.status_code}")
        assert login_res.status_code == 200, f"User login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print("\n--- 2. Requesting AI Recommendations ---")
        rec_payload = {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "eta_minutes": 20,
            "max_distance_km": 5.0,
            "max_results": 3
        }
        # Increase timeout to 30s to allow ML cold-starts to complete successfully
        rec_res = await client.post(
            "http://localhost:8000/prediction/recommendations",
            json=rec_payload,
            headers=headers,
            timeout=30.0
        )
        print(f"Recommendations Status: {rec_res.status_code}")
        assert rec_res.status_code == 200, f"Recommendations query failed: {rec_res.text}"
        
        recs = rec_res.json()["recommendations"]
        assert len(recs) > 0, "No recommendation candidates returned"
        recommended_facility_id = recs[0]["facility_id"]
        print(f"Recommended Facility ID: {recommended_facility_id} (Score: {recs[0]['recommendation_score']})")

        print("\n--- 3. Fetching Arrival Availability Predictions ---")
        avail_res = await client.get(
            f"http://localhost:8000/prediction/availability/{recommended_facility_id}?eta_minutes=20",
            headers=headers,
            timeout=30.0
        )
        print(f"Availability Status: {avail_res.status_code} - {avail_res.json()}")
        assert avail_res.status_code == 200, f"Availability forecast query failed: {avail_res.text}"

        print("\n--- 4. Creating a Slot Reservation ---")
        # Reserve slot 1 for the next 2 hours
        now = datetime.now(timezone.utc)
        res_payload = {
            "slot_id": 1,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat()
        }
        res_res = await client.post("http://localhost:8000/reservations", json=res_payload, headers=headers)
        print(f"Reservation Creation: {res_res.status_code} - {res_res.json()}")
        assert res_res.status_code == 200, f"Slot reservation failed: {res_res.text}"
        reservation_id = res_res.json()["id"]

        print("\n--- 5. Estimating ETA and Virtual Queue Wait times ---")
        queue_res = await client.get(
            f"http://localhost:8000/prediction/queue/{recommended_facility_id}?eta_minutes=20",
            headers=headers,
            timeout=30.0
        )
        print(f"Queue Status: {queue_res.status_code} - {queue_res.json()}")
        assert queue_res.status_code == 200, f"Queue prediction query failed: {queue_res.text}"

        print("\n--- 6. Running AI Service Collector Data Sync Cycle ---")
        # Trigger collectors to read reservation history and occupancy from backend
        sync_res = await client.get("http://localhost:8001/collector/run", timeout=30.0)
        print(f"Collector run status: {sync_res.status_code}")
        assert sync_res.status_code == 200, f"AI Collector execution failed: {sync_res.text}"
        
        sync_data = sync_res.json()
        print(f"Collector summary: {sync_data}")
        # Validate that the collectors connected to the backend APIs successfully
        for collector_name, details in sync_data.items():
            print(f"Collector '{collector_name}': status={details['status']}, fetched={details['fetched_count']}, inserted={details['inserted_count']}")
            assert details["status"] == "SUCCESS", f"Collector {collector_name} failed"

        print("\n[SUCCESS] Entire Backend <-> AI Service E2E integration cycle validated successfully!")


async def main():
    print("==================================================")
    print(" STARTING PARKZENITH SYSTEM E2E VALIDATION")
    print("==================================================")

    # Start servers
    backend_proc = await run_server("python -m uvicorn backend.app.main:app --port 8000 --host 127.0.0.1")
    ai_proc = await run_server("python -m uvicorn ai_service.main:app --port 8001 --host 127.0.0.1")

    try:
        print("[INFO] Waiting for servers to start...")
        backend_up = await wait_for_port(8000)
        ai_up = await wait_for_port(8001)

        if not backend_up or not ai_up:
            print("[ERROR] Servers failed to start within timeout.")
            return

        # Run validations
        await run_e2e_cycle()

    except Exception as exc:
        print(f"\n[ERROR] Unhandled exception occurred: {str(exc)}")
        traceback.print_exc()
    finally:
        print("\n[INFO] Tearing down validation environment...")
        terminate_process(backend_proc)
        terminate_process(ai_proc)
        print("[INFO] E2E validation run complete.")


if __name__ == "__main__":
    asyncio.run(main())
