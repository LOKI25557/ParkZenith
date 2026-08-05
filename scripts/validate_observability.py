"""
ParkZenith Production Observability and Operations Validation Script.
Validates:
1. Health and readiness endpoints.
2. Request ID propagation and distributed tracing.
3. Service connection drop alert scenario (by stopping the AI Service and checking readiness).
"""

import asyncio
import os
import subprocess
import sys
import time
import httpx


async def run_server(command: str) -> subprocess.Popen:
    """Spawns a server process in the background."""
    print(f"[INFO] Spawning background server: {command}")
    # Do not pipe stdout/stderr to avoid blocking when buffers fill up
    process = subprocess.Popen(
        command,
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    return process


def terminate_process(process: subprocess.Popen):
    """Gracefully terminates a spawned process and its child tree."""
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


async def test_health_endpoints():
    """Validates the health check API outputs."""
    print("\n--- 1. Testing Health & Readiness Endpoints ---")
    async with httpx.AsyncClient() as client:
        # Backend health/ready checks
        res_backend_ready = await client.get("http://localhost:8000/ready")
        print(f"Backend Ready Status: {res_backend_ready.status_code} - {res_backend_ready.json()}")
        assert res_backend_ready.status_code == 200, "Backend readiness failed"
        assert res_backend_ready.json()["status"] == "READY", "Backend is not fully ready"

        # AI Service health/ready checks
        res_ai_health = await client.get("http://localhost:8001/health")
        print(f"AI Service Health: {res_ai_health.status_code} - {res_ai_health.json()}")
        assert res_ai_health.status_code == 200, "AI Service health check failed"
        assert res_ai_health.json()["status"] == "UP", "AI Service scheduler is down"

        res_ai_ready = await client.get("http://localhost:8001/ready")
        print(f"AI Service Ready Status: {res_ai_ready.status_code} - {res_ai_ready.json()}")
        assert res_ai_ready.status_code == 200, "AI Service readiness check failed"


async def test_request_id_propagation():
    """Validates X-Request-ID propagation."""
    print("\n--- 2. Testing Request-ID Trace Propagation ---")
    test_id = f"trace-test-{int(time.time())}"
    headers = {"X-Request-ID": test_id}
    
    async with httpx.AsyncClient() as client:
        # Hit backend which will call AI Service internally
        res = await client.get("http://localhost:8000/prediction/occupancy/1?horizon_minutes=15", headers=headers)
        
        returned_id = res.headers.get("X-Request-ID")
        print(f"Sent Request ID: {test_id}")
        print(f"Returned Request ID: {returned_id}")
        
        assert returned_id == test_id, "Request-ID tracing propagation failed!"
        print("[SUCCESS] X-Request-ID propagated correctly from client to response headers.")


async def main():
    print("==================================================")
    print(" STARTING OBSERVABILITY & OPERATIONS VALIDATION")
    print("==================================================")

    # 1. Start servers
    backend_proc = await run_server("python -m uvicorn backend.app.main:app --port 8000 --host 127.0.0.1")
    ai_proc = await run_server("python -m uvicorn ai_service.main:app --port 8001 --host 127.0.0.1")

    try:
        print("[INFO] Waiting for servers to start...")
        backend_up = await wait_for_port(8000)
        ai_up = await wait_for_port(8001)

        if not backend_up or not ai_up:
            print("[ERROR] Servers failed to start within timeout.")
            return

        # 2. Run validations
        await test_health_endpoints()
        await test_request_id_propagation()

        # 3. Simulate Connection Drop Alert Scenario (Stop AI Service)
        print("\n--- 3. Simulating Connection Drop / Timeout Alert Scenario ---")
        print("[INFO] Shutting down AI Service to simulate connection loss...")
        terminate_process(ai_proc)
        ai_proc = None

        # Give it a moment to release ports
        await asyncio.sleep(2)

        # Check backend readiness again
        print("[INFO] Querying backend readiness with AI Service offline...")
        async with httpx.AsyncClient() as client:
            res_degraded = await client.get("http://localhost:8000/ready")
            print(f"Degraded Status response: {res_degraded.status_code} - {res_degraded.json()}")
            
            # Verify backend enters DEGRADED state and marks AI service DISCONNECTED
            assert res_degraded.json()["status"] == "DEGRADED", "Backend failed to enter DEGRADED state"
            assert res_degraded.json()["ai_service"] == "DISCONNECTED", "Backend did not detect AI Service disconnection"
            print("[SUCCESS] Backend entered DEGRADED state and correctly reported AI Service offline.")

    except AssertionError as exc:
        print(f"\n[FAIL] Validation AssertionError: {str(exc)}")
    except Exception as exc:
        print(f"\n[ERROR] Unhandled exception occurred: {str(exc)}")
    finally:
        # Shutdown any remaining servers
        print("\n[INFO] Tearing down validation environment...")
        terminate_process(backend_proc)
        if ai_proc:
            terminate_process(ai_proc)
        print("[INFO] Observability & Operations validation run complete.")


if __name__ == "__main__":
    asyncio.run(main())
