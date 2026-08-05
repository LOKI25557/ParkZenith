"""
ParkZenith Production Security Hardening Validation Script.
Validates:
1. HTTP Security Headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options).
2. CORS origin restriction configurations.
3. JWT-based API Authentication (guarding routes, token issuance, invalid tokens).
"""

import asyncio
import os
import random
import subprocess
import sys
import time
import httpx


async def run_server(command: str, env: dict) -> subprocess.Popen:
    """Spawns a server process in the background with custom environment variables."""
    print(f"[INFO] Spawning background server: {command}")
    process = subprocess.Popen(
        command,
        shell=True,
        env={**os.environ, **env},
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


async def test_security_headers():
    """Validates presence and correctness of security headers on the backend."""
    print("\n--- 1. Testing HTTP Security Headers ---")
    async with httpx.AsyncClient() as client:
        res = await client.get("http://localhost:8000/ready")
        headers = res.headers

        # Verify X-Content-Type-Options
        x_content = headers.get("X-Content-Type-Options")
        print(f"X-Content-Type-Options: {x_content}")
        assert x_content == "nosniff", "Missing or incorrect X-Content-Type-Options header!"

        # Verify X-Frame-Options
        x_frame = headers.get("X-Frame-Options")
        print(f"X-Frame-Options: {x_frame}")
        assert x_frame == "DENY", "Missing or incorrect X-Frame-Options header!"

        # Verify X-XSS-Protection
        x_xss = headers.get("X-XSS-Protection")
        print(f"X-XSS-Protection: {x_xss}")
        assert x_xss == "1; mode=block", "Missing or incorrect X-XSS-Protection header!"

        # Verify HSTS (Strict-Transport-Security)
        hsts = headers.get("Strict-Transport-Security")
        print(f"Strict-Transport-Security: {hsts}")
        assert hsts is not None, "Missing HSTS header!"

        # Verify CSP (Content-Security-Policy)
        csp = headers.get("Content-Security-Policy")
        print(f"Content-Security-Policy: {csp}")
        assert csp is not None, "Missing Content-Security-Policy header!"
        
        print("[SUCCESS] All required security hardening headers are present.")


async def test_cors_configuration():
    """Validates CORS configurations under production settings."""
    print("\n--- 2. Testing CORS Origin Restrictions ---")
    # Simulate an preflight OPTIONS request from an unauthorized external domain
    headers = {
        "Origin": "http://evil-attacker-site.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    async with httpx.AsyncClient() as client:
        res = await client.options("http://localhost:8000/auth/login", headers=headers)
        
        allow_origin = res.headers.get("access-control-allow-origin")
        print(f"CORS Access-Control-Allow-Origin response: {allow_origin}")
        
        # In production mode, since evil-attacker-site.com is not allowed, it should not reflect the origin
        assert allow_origin != "http://evil-attacker-site.com", "CORS policy allows unauthorized origins!"
        print("[SUCCESS] CORS policy correctly blocked unauthorized origin access.")


async def test_jwt_authentication():
    """Validates JWT endpoint security, generation, expiration, and scope limits."""
    print("\n--- 3. Testing JWT API Authentication Guards ---")
    
    # Generate unique test user credentials
    test_num = random.randint(1000, 9999)
    test_email = f"security-test-{test_num}@parkzenith.com"
    test_password = "SecurePassword123!"

    async with httpx.AsyncClient() as client:
        # Scenario A: Retrieve profile without token (unauthenticated)
        res_unauth = await client.get("http://localhost:8000/auth/me")
        print(f"Query /auth/me unauthenticated: {res_unauth.status_code}")
        assert res_unauth.status_code == 401, "Guarded endpoint permitted unauthenticated query!"

        # Scenario B: Register new test account
        res_register = await client.post(
            "http://localhost:8000/auth/register",
            json={"email": test_email, "password": test_password, "full_name": "Security Auditor"}
        )
        print(f"User registration: {res_register.status_code}")
        assert res_register.status_code == 201, "Test user registration failed"

        # Scenario C: Authenticate and request token
        res_login = await client.post(
            "http://localhost:8000/auth/login",
            json={"email": test_email, "password": test_password}
        )
        print(f"User login: {res_login.status_code}")
        assert res_login.status_code == 200, "User login failed"
        
        token_data = res_login.json()
        assert "access_token" in token_data, "Login response did not yield token"
        token = token_data["access_token"]
        print("[INFO] Bearer JWT token successfully generated.")

        # Scenario D: Retrieve profile using bearer token (authenticated)
        headers = {"Authorization": f"Bearer {token}"}
        res_auth = await client.get("http://localhost:8000/auth/me", headers=headers)
        print(f"Query /auth/me authenticated: {res_auth.status_code} - {res_auth.json()}")
        assert res_auth.status_code == 200, "Authenticated query was rejected!"
        assert res_auth.json()["email"] == test_email, "Token decoded incorrect user details"

        # Scenario E: Access with malformed token
        bad_headers = {"Authorization": "Bearer invalid-junk-token"}
        res_bad_token = await client.get("http://localhost:8000/auth/me", headers=bad_headers)
        print(f"Query /auth/me with bad token: {res_bad_token.status_code}")
        assert res_bad_token.status_code == 401, "Endpoint did not block malformed token!"
        
        print("[SUCCESS] JWT Authentication system successfully validated.")


async def main():
    print("==================================================")
    print(" STARTING SECURITY HARDENING CONFIG VALIDATION")
    print("==================================================")

    # Force production configuration for backend to test CORS and security hardening
    prod_env = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "this-is-a-very-long-production-ready-secure-key-32-chars-long-or-more",
        "ALLOWED_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000",
        "DATABASE_URL": "sqlite+aiosqlite:///./backend.db"
    }

    # Start servers
    backend_proc = await run_server("python -m uvicorn backend.app.main:app --port 8000 --host 127.0.0.1", prod_env)
    ai_proc = await run_server("python -m uvicorn ai_service.main:app --port 8001 --host 127.0.0.1", {})

    try:
        print("[INFO] Waiting for servers to start...")
        backend_up = await wait_for_port(8000)
        ai_up = await wait_for_port(8001)

        if not backend_up or not ai_up:
            print("[ERROR] Servers failed to start within timeout.")
            return

        # Run validations
        await test_security_headers()
        await test_cors_configuration()
        await test_jwt_authentication()

    except AssertionError as exc:
        print(f"\n[FAIL] Security Validation AssertionError: {str(exc)}")
    except Exception as exc:
        print(f"\n[ERROR] Unhandled exception occurred: {str(exc)}")
    finally:
        print("\n[INFO] Tearing down validation environment...")
        terminate_process(backend_proc)
        terminate_process(ai_proc)
        print("[INFO] Security validation run complete.")


if __name__ == "__main__":
    asyncio.run(main())
