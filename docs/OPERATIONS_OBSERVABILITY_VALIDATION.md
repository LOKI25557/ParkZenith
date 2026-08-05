# 📊 Operations & Observability Validation Report

This report documents the validation of production-readiness instrumentation, logging, tracing, and failure-scenario alerting inside the **ParkZenith** system.

---

## 📋 Observability Validation Results

The automated validation script [validate_observability.py](file:///c:/Users/Lenovo/OneDrive/Desktop/ParkZenith/scripts/validate_observability.py) was executed to verify the telemetry and error-handling capabilities of the backend and AI services.

| Check Category | Validation Scenario | Expected Behavior | Actual Behavior / Status |
| :--- | :--- | :--- | :--- |
| **Endpoint Probes** | Backend readiness `GET /ready` | Returns HTTP 200 with status `READY` | ✅ PASS |
| **Endpoint Probes** | AI Service health `GET /health` | Returns HTTP 200 with scheduler status | ✅ PASS |
| **Endpoint Probes** | AI Service readiness `GET /ready` | Returns HTTP 200 with database & models ready | ✅ PASS |
| **Distributed Tracing** | `X-Request-ID` Header Propagation | Tracing ID flows from backend to AI and back to client headers | ✅ PASS (`trace-test-*` returned) |
| **Fault Alert Trigger** | AI Service Connection Loss | Backend enters `DEGRADED` state (`ai_service: DISCONNECTED`) | ✅ PASS |

---

## 🔍 Detailed Validation Steps

### 1. Health and Readiness Checks
The health checks ensure that load balancers (e.g. AWS ALB, Kubernetes readiness/liveness probes) can determine if the application is ready to receive traffic.
- **Backend Probe**: Checks SQLite/PostgreSQL connection and calls the AI Service health API.
- **AI Service Probe**: Verifies internal database access and ensures machine learning model packages are correctly loaded in memory.

### 2. Distributed Tracing (`X-Request-ID` propagation)
For request tracking across microservices, ParkZenith uses a middleware that intercepts incoming requests:
1. If the client sends an `X-Request-ID` header, the system preserves it. Otherwise, a unique UUIDv4 is generated.
2. The Request ID is stored in a context variable (`ContextVar`) to automatically format all application log lines with `[req_id=...]`.
3. When the backend communicates with the AI Service via the HTTP client, it attaches the Request ID to the outgoing `X-Request-ID` header.
4. The AI Service logs the request with the identical request ID, completing the end-to-end tracing path.
5. Finally, the response headers include the `X-Request-ID` for client-side auditing.

### 3. Failure Scenario Simulation (Connection Loss)
To validate the reliability of operational alerts:
1. The AI Service process was forcefully terminated.
2. The backend `/ready` endpoint was queried under this degraded state.
3. The backend successfully caught the connection exception, logged a warning, and responded with:
   ```json
   {
     "status": "DEGRADED",
     "database": "CONNECTED",
     "ai_service": "DISCONNECTED"
   }
   ```
4. This ensures that orchestration tools can automatically trigger alarms or reroute traffic to static fallback mechanisms when subservices fail.

---

## 🚀 Running the Observability Validation Script

To execute the validation pipeline locally:

```powershell
python -m scripts.validate_observability
```
