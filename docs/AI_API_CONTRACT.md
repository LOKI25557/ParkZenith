# ParkZenith AI Service API Contract

This document specifies the REST API endpoints exposed by the ParkZenith AI Service (default: `http://localhost:8001`). All requests and responses use the `application/json` content type.

---

## 1. Unified Error Responses

All error responses from the AI Service conform to a standardized JSON structure. This prevents internal information leaks and ensures predictable client parsing:

```json
{
  "success": false,
  "detail": "Descriptive error message.",
  "error": {
    "code": "ERROR_CODE",
    "message": "User-friendly description of what went wrong.",
    "details": {},
    "path": "/api/endpoint/path"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
| :--- | :--- | :--- |
| `MODEL_UNAVAILABLE` | `404 Not Found` | The forecasting model package is not trained or loaded. |
| `MISSING_FACILITY` | `404 Not Found` | The specified facility ID does not exist or has no occupancy history logs. |
| `INSUFFICIENT_DATA` | `400 Bad Request` | Too few historical logs exist for feature engineering or dynamic training. |
| `INVALID_DATE_RANGE` | `400 Bad Request` | Start date query parameter occurs after the end date. |
| `DUPLICATE_DATA` | `409 Conflict` | Attempted to insert a record that violates strict unique constraints. |
| `INTERNAL_SERVER_ERROR` | `500 Internal Server Error` | An unexpected python runtime exception occurred. |

---

## 2. Occupancy Forecasting Endpoints

### Get Model Status
- **Method & Path**: `GET /forecast/status`
- **Response (200 OK)**:
  ```json
  {
    "status": "READY",
    "models_ready": true,
    "trained_horizons": ["15", "30", "60"]
  }
  ```

### Get Forecast Snapshots
- **Method & Path**: `GET /forecast/{horizon}`
  - `horizon` (Path Parameter): `15`, `30`, or `60` (minutes)
  - `facility_id` (Query Parameter): `int` (Required)
- **Response (200 OK)**:
  ```json
  {
    "facility_id": 1,
    "current_occupancy": 64.5,
    "prediction_15": 68.2,
    "prediction_30": 72.0,
    "prediction_60": 76.5,
    "confidence": 98.2
  }
  ```

### Custom Horizon Prediction
- **Method & Path**: `POST /forecast/custom`
- **Request Body**:
  ```json
  {
    "facility_id": 1,
    "target_minutes": 45
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "facility_id": 1,
    "current_occupancy": 64.5,
    "prediction_custom": 71.3,
    "confidence": 95.5
  }
  ```

---

## 3. Arrival Availability Predictions

### Predict Facility Availability
- **Method & Path**: `GET /availability/{facility_id}`
  - `facility_id` (Path Parameter): `str` (Required)
  - `eta_minutes` (Query Parameter): `int` (Default: `20`)
- **Response (200 OK)**:
  ```json
  {
    "facility_id": "FAC-001",
    "eta_minutes": 20,
    "current_occupancy": 64.5,
    "forecast_occupancy": 68.2,
    "expected_free_slots": 31.0,
    "availability_probability": 85.0,
    "occupancy_risk": "LOW",
    "confidence": 98.2
  }
  ```

---

## 4. Smart Parking Recommendations

### Query Ranked Parking Options
- **Method & Path**: `POST /recommendations`
- **Request Body**:
  ```json
  {
    "latitude": 12.9716,
    "longitude": 77.5946,
    "eta_minutes": 20,
    "destination_latitude": 12.9750,
    "destination_longitude": 77.6000,
    "max_distance_km": 5.0,
    "max_results": 5,
    "max_parking_fee": 10.0,
    "parking_type": "EV",
    "preferred_facility": "FAC-001",
    "accessibility_required": false,
    "weights": {
      "distance": 0.3,
      "cost": 0.2,
      "availability": 0.4,
      "utilization": 0.1
    }
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "recommendations": [
      {
        "rank": 1,
        "facility_id": "FAC-001",
        "facility_name": "Zenith Central",
        "recommendation_score": 94.2,
        "availability_probability": 88.0,
        "current_occupancy": 62.0,
        "forecast_occupancy": 66.0,
        "distance_km": 1.2,
        "walking_distance_m": 420,
        "estimated_cost": 5.0,
        "queue_wait_minutes": 1.5,
        "occupancy_risk": "LOW",
        "confidence": 97.5,
        "reason": "Top scoring option. Zenith Central features low walking distance to destination and a very high probability of vacancy at arrival."
      }
    ],
    "total_candidates": 3,
    "returned_results": 1
  }
  ```

---

## 5. Real-Time Virtual Queues

All virtual queue operations operate under concurrency-safe facility locks.

### Join Virtual Queue
- **Method & Path**: `POST /queue/{facility_id}/enqueue`
- **Request Body**:
  ```json
  {
    "user_id": "USER-10023"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "facility_id": "FAC-001",
    "user_id": "USER-10023",
    "position": 4
  }
  ```

### Dequeue Driver
- **Method & Path**: `POST /queue/{facility_id}/dequeue`
- **Request Body** (Optional `user_id` to pop specific driver, or omit to pop queue head):
  ```json
  {
    "user_id": "USER-10023"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "facility_id": "FAC-001",
    "user_id": "USER-10023",
    "success": true
  }
  ```

### Cancel Queue Position
- **Method & Path**: `POST /queue/{facility_id}/cancel`
- **Request Body**:
  ```json
  {
    "user_id": "USER-10023"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "facility_id": "FAC-001",
    "user_id": "USER-10023",
    "success": true
  }
  ```

### Lookup Queue Position
- **Method & Path**: `GET /queue/{facility_id}/position`
  - `user_id` (Query Parameter): `str` (Required)
- **Response (200 OK)**:
  ```json
  {
    "facility_id": "FAC-001",
    "user_id": "USER-10023",
    "position": 3
  }
  ```
