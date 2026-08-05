# Database Schema & Migration Guide

This document describes the production PostgreSQL database architecture, connection pooling, schema structure, indexing, health checks, and safe migration/initialization strategies for ParkZenith.

## Production Connection Configuration
In production, the application connects to a PostgreSQL instance via the async dialect `postgresql+asyncpg`. 
Settings are loaded from the `DATABASE_URL` environment variable.

### Connection Pooling
Connection pooling is handled in `backend/app/database/session.py` and `ai_service/database/session.py`. For PostgreSQL, the following pool parameters are configured:
- **`pool_size`**: `20` (maximum persistent connections in the pool)
- **`max_overflow`**: `10` (temporary additional connections allowed during traffic bursts)
- **`pool_recycle`**: `1800` seconds (connections are recycled after 30 minutes to prevent resource leaks)
- **`pool_pre_ping`**: `True` (verifies connection liveness before checking out to avoid stale connection errors)

---

## Schema & Tables

### 1. `users`
- Stores system users and credentials.
- Columns:
  - `id` (Integer, Primary Key)
  - `email` (String(255), Unique Index)
  - `full_name` (String(255))
  - `phone` (String(32))
  - `vehicle_number` (String(32))
  - `password_hash` (String(512))
  - `is_active` (Boolean)
  - `is_superuser` (Boolean)
  - `created_at` (DateTime, Default: `CURRENT_TIMESTAMP`)
  - `updated_at` (DateTime, Default: `CURRENT_TIMESTAMP`)

### 2. `parking_facilities`
- Stores parking facility details.
- Columns:
  - `id` (Integer, Primary Key, Index)
  - `name` (String(255))
  - `address` (Text)
  - `city` (String(128))
  - `is_active` (Boolean)

### 3. `parking_slots`
- Individual parking slots assigned to facilities.
- Columns:
  - `id` (Integer, Primary Key, Index)
  - `facility_id` (Integer, Foreign Key to `parking_facilities.id`)
  - `slot_number` (String(50))
  - `is_available` (Boolean)

### 4. `reservations`
- Driver reservations for specific parking slots.
- Columns:
  - `id` (Integer, Primary Key, Index)
  - `user_id` (Integer, Foreign Key to `users.id`)
  - `slot_id` (Integer, Foreign Key to `parking_slots.id`)
  - `start_time` (DateTime)
  - `end_time` (DateTime)
  - `status` (Enum: `PENDING`, `CONFIRMED`, `CANCELLED`)
  - `created_at` (DateTime, Default: `CURRENT_TIMESTAMP`)

### 5. `parking_sessions`
- Realized parking events.
- Columns:
  - `id` (Integer, Primary Key, Index)
  - `reservation_id` (Integer, Foreign Key to `reservations.id`, Optional)
  - `slot_id` (Integer, Foreign Key to `parking_slots.id`)
  - `started_at` (DateTime, Default: `CURRENT_TIMESTAMP`)
  - `ended_at` (DateTime, Optional)
  - `fee` (Float, Optional)

### 6. `payments`
- Financial records of parking sessions.
- Columns:
  - `id` (Integer, Primary Key, Index)
  - `user_id` (Integer, Foreign Key to `users.id`)
  - `session_id` (Integer, Foreign Key to `parking_sessions.id`, Optional)
  - `amount` (Float)
  - `provider` (String(128))
  - `provider_reference` (String(255))
  - `created_at` (DateTime, Default: `CURRENT_TIMESTAMP`)

---

## AI Service Tables (Telemetry/Analytics Store)

### 1. `occupancy_history`
- Time-series log of facility occupancy for ML training.
- Indexes:
  - Composite Index `idx_occupancy_facility_collected` on `(facility_id, collected_at)`
  - Composite Index `idx_occupancy_facility_zone` on `(facility_id, zone_id)`

### 2. `reservation_history`
- Mirror/cache of reservations for analytics processing.

### 3. `parking_session_history`
- Mirror/cache of parking sessions including vehicle category logs.

---

## Safe Database Initialization & Migrations

### Running Alembic Migrations (Backend)
To initialize or migrate a clean PostgreSQL instance on the host machine or in the container:
```bash
# Navigate to the backend directory
cd backend

# Execute migrations to bring schema up-to-date
alembic upgrade head
```

### AI Service DB Initialization
The AI Service checks table status programmatically on startup using SQLAlchemy's `create_all`. It initializes missing tables safely:
```python
async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

### Database Health & Liveness Checks
We run a fast `SELECT 1` query to verify PostgreSQL connectivity during application readiness checks:
```sql
SELECT 1;
```
If this query fails or times out, the service is marked as `DEGRADED` (or `NOT_READY`), and operators/orchestrators receive a `503 Service Unavailable` status on the `/ready` HTTP endpoint.
