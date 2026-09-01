# 🚗 ParkZenith: Smart Parking Management & AI Prediction System

### Find it. Reserve it. Predict it.

ParkZenith is an AI-powered smart parking platform that enables users to discover nearby parking spaces, reserve slots, navigate to parking facilities, and make informed parking decisions through real-time occupancy tracking and machine learning-driven predictions.
It provides real-time parking management, reservations, navigation, and predictive insights to help users find the best parking option efficiently.
The platform combines smart parking management with predictive analytics to forecast parking demand, estimate future availability, generate occupancy heat maps, predict queue times, and recommend the best parking options before users begin their journey.

---

## 🌟 Key Features

- 🔍 Nearby Parking Discovery
- 🅿️ Live Parking Slot Visualization
- 📅 Smart Slot Reservation
- 🧭 Navigation to Parking Facilities
- ✅ Check-In / Check-Out Management
- 💳 Pay-After-Occupancy Billing.
- 📡 Real-Time Occupancy Tracking
- 🔥 Parking Occupancy Heat Maps
- 🤖 AI Occupancy Forecasting.
- 📈 Arrival Availability Prediction
- 🎯 Smart Parking Recommendations
- ⏱ Queue & Entry Time Prediction
- 🎪 Event-Aware Demand Forecasting
- 🚗 Return-to-Car Navigation
- 📊 Admin  Dashboard

---

## 🛠 Tech Stack

### Frontend

- React.js
- HTML5
- CSS3
- JavaScript

### Backend

- FastAPI (Python)

### Database

- PostgreSQL
- Firebase Firestore

### Real-Time Communication

- Firebase Realtime Database
- WebSockets

### Maps & Navigation

- Leaflet.js
- OpenStreetMap
- Google Maps API

### AI & Machine Learning

- Python
- Pandas
- NumPy
- Scikit-learn

### Visualization

- Chart.js
- Recharts

---

## 🎯 Project Objectives

- Reduce parking search time
- Improve parking space utilization
- Minimize urban traffic congestion
- Lower fuel consumption and emissions
- Provide predictive parking intelligence
- Enhance user convenience through AI-driven recommendations

---

## 🚀 What Makes ParkZenith Different?

Unlike traditional parking applications that only show current availability, ParkZenith predicts future parking conditions and helps users answer:

> **"Will parking still be available when I arrive, and which parking option is best for me?"**

By combining real-time parking operations with intelligent forecasting and recommendation systems, ParkZenith transforms parking into a smarter, faster, and more efficient experience.

---

## 📂 Project Structure

```text
ParkZenith/
├── backend/
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── ai_service/
├── scripts/
├── docs/
│   ├── architecture.md
│   ├── api_design.md
│   └── database_schema.md
├── docker-compose.yml
├── README.md
└── .gitignore
```

---

## 📌 Status

🚀 Phase 2 – Core Backend & AI Service Implementation

Current Progress:

- **Backend core features implemented**: Auth, Parking Facilities, Slots, Reservations, Payments, and Sessions.
- **Advanced Parking Schema**: Refactored core parking models to support a robust hierarchy (Facilities, Zones, and Slots).
- **AI Service integrated**: Predictive pipelines for availability, queue time, and smart recommendations updated for new parking schema.
- **Database schemas and migrations defined**: PostgreSQL via SQLAlchemy & Alembic (including core parking schema migration).
- **Real-time communication set up**: WebSocket support for live occupancy updates.
- **Admin Dashboard**: Updated Admin Analytics Dashboard entry.
- **E2E Testing & Data Sync APIs built**: Seeding scripts, comprehensive database tests for parking model relationships, and sync endpoints ready for frontend integration.

---

## 👨‍💻 Developed As

Academic Smart City Project focusing on:

- Smart Parking Management
- Real-Time Systems
- Artificial Intelligence
- Predictive Analytics
- Smart Mobility Solutions

---

## 📊 Seeding and Resetting Demo Data

To populate the local SQLite databases (or production PostgreSQL instances) with realistic, privacy-compliant synthetic data for testing:

1. **Reset and Seed**:
   Run the seeding script from the project root directory:
   ```bash
   python -m scripts.seed_demo_data
   ```
   This script will automatically:
   - Create any missing tables in both the backend and AI service databases.
   - Delete all existing records (resetting the environment).
   - Generate realistic user accounts, facilities, slots, reservations, payments, and 7 days of time-series occupancy/session telemetry logs (incorporating diurnal commuting peaks, off-peaks, and queue congestion conditions).

2. **Database URLs**:
   The script loads configuration dynamically using the `DATABASE_URL` settings. To run it against a production PostgreSQL container or local cluster, verify that the environment variables are set correctly (e.g. `DATABASE_URL=postgresql+asyncpg://...`).

---

## 📜 License

This project is being developed for educational and research purposes.
