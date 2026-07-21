# ParkZenith AI Service - Phase 1: Data Collection Pipeline

The **ParkZenith AI Service** is an autonomous microservice responsible for ingesting historical parking data (occupancy metrics, reservations, and parking sessions) from the main backend API, storing it in an async relational database, and preparing exported CSV datasets for future machine learning and analytics pipelines.

---

## 🏗️ Tech Stack

- **Python 3.12+**
- **FastAPI**: Modern, high-performance web framework.
- **SQLAlchemy 2.0 (Async)**: Async ORM for PostgreSQL (`asyncpg`) and SQLite (`aiosqlite`).
- **Pydantic v2 & Pydantic Settings**: Data validation and type-safe environment configuration.
- **httpx**: Asynchronous HTTP client with retry backoff for backend API integration.
- **APScheduler**: Periodic background job execution (`AsyncIOScheduler`).
- **Pandas**: Efficient CSV dataset export generator.
- **Alembic**: Database schema migration framework.

---

## 📁 Directory Structure

```text
ai_service/
│
├── api/                  # FastAPI routers and dependency injection providers
│   ├── deps.py
│   ├── routes.py
│   └── __init__.py
│
├── collectors/           # Data collection pipeline logic & deduplication
│   ├── base.py
│   ├── occupancy_collector.py
│   ├── reservation_collector.py
│   ├── session_collector.py
│   └── __init__.py
│
├── config/               # Pydantic BaseSettings environment configuration
│   ├── settings.py
│   └── __init__.py
│
├── core/                 # Centralized exceptions, handlers, and logging
│   ├── exceptions.py
│   ├── exception_handlers.py
│   ├── logging.py
│   └── __init__.py
│
├── database/             # Async database connection, engine, and base ORM
│   ├── base.py
│   ├── session.py
│   └── __init__.py
│
├── models/               # SQLAlchemy ORM database models
│   ├── occupancy.py
│   ├── reservation.py
│   ├── session.py
│   └── __init__.py
│
├── repositories/         # Async data access repositories (CRUD, queries, bulk save)
│   ├── base.py
│   ├── occupancy_repository.py
│   ├── reservation_repository.py
│   ├── session_repository.py
│   └── __init__.py
│
├── schemas/              # Pydantic request/response schemas
│   ├── collector.py
│   ├── occupancy.py
│   ├── reservation.py
│   ├── session.py
│   └── __init__.py
│
├── services/             # Orchestration service layer
│   ├── collector_service.py
│   ├── exporter_service.py
│   └── __init__.py
│
├── scheduler/            # APScheduler background tasks manager
│   ├── scheduler.py
│   └── __init__.py
│
├── datasets/             # Directory where exported CSV datasets are saved
│   └── .gitkeep
│
├── utils/                # HTTP client & CSV exporter utilities
│   ├── backend_client.py
│   ├── dataset_exporter.py
│   └── __init__.py
│
├── alembic/              # DB Migration scripts
│   ├── env.py
│   └── versions/
│
├── alembic.ini           # Alembic configuration
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
└── main.py               # FastAPI entrypoint & lifespan lifecycle
```

---

## ⚙️ Environment Configuration

Set environment variables in `.env` or system environment:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./ai_service.db` | Async DB connection URL (`postgresql+asyncpg://...` or `sqlite+aiosqlite://...`) |
| `BACKEND_API_URL` | `http://localhost:8000/api/v1` | Base URL of the main ParkZenith backend |
| `EXPORT_PATH` | `./datasets` | Target directory path for exported CSV datasets |
| `OCCUPANCY_COLLECTION_INTERVAL_SECONDS` | `60` | Schedule interval for occupancy collector (1 min) |
| `RESERVATION_COLLECTION_INTERVAL_SECONDS` | `300` | Schedule interval for reservation collector (5 min) |
| `SESSION_COLLECTION_INTERVAL_SECONDS` | `300` | Schedule interval for session collector (5 min) |
| `HTTP_TIMEOUT_SECONDS` | `10.0` | Timeout in seconds for backend HTTP calls |
| `HTTP_MAX_RETRIES` | `3` | Maximum retry attempts for failed backend HTTP calls |

---

## 🚀 Getting Started

### 1. Install Dependencies

```bash
cd ai_service
pip install -r requirements.txt
```

### 2. Run the Service

```bash
uvicorn ai_service.main:app --port 8001 --reload
```

---

## 📡 API Endpoints

### 1. Status Monitoring

```http
GET /collector/status
```
Returns total stored records per model, scheduler running status, and last collection summary.

### 2. Manual Trigger

```http
GET /collector/run
```
Triggers all 3 collectors immediately on demand.

### 3. Export Datasets

```http
GET /collector/export
```
Exports `OccupancyHistory`, `ReservationHistory`, and `ParkingSessionHistory` into CSV files under `./datasets/`:
- `occupancy_history.csv`
- `reservation_history.csv`
- `parking_sessions.csv`

---

## 🧪 Verification & Testing

Run the included verification test suite:

```bash
python -m unittest tests/test_pipeline.py
```
