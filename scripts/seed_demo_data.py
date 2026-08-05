"""
ParkZenith Production-Like Synthetic Data Seeding Script.
Seeds both backend and AI service databases with realistic, privacy-compliant data.
Simulates high/low occupancy, peak/off-peak hours, reservation activity, and queue conditions.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext

# Database utilities
from sqlalchemy import delete, text

# Backend Database imports
from backend.app.database.base import Base as BackendBase
from backend.app.database.session import engine as backend_engine
from backend.app.database.session import AsyncSessionLocal as BackendSessionLocal
from backend.app.models.user import User as BackendUser
from backend.app.models.parking import ParkingFacility as BackendFacility, ParkingSlot as BackendSlot
from backend.app.models.reservation import Reservation as BackendReservation, ReservationStatus
from backend.app.models.session import ParkingSession as BackendSession
from backend.app.models.payment import Payment as BackendPayment

# AI Service Database imports
from ai_service.database.base import Base as AIBase
from ai_service.database.session import engine as ai_engine
from ai_service.database.session import AsyncSessionFactory as AISessionLocal
from ai_service.models.occupancy import OccupancyHistory as AIOccupancyHistory
from ai_service.models.reservation import ReservationHistory as AIReservationHistory
from ai_service.models.session import ParkingSessionHistory as AISessionHistory

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_demo_data")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 7 days of time-series occupancy data
DAYS_TO_SEED = 7
FACILITY_SLOT_COUNT = 50


def get_occupancy_pattern(hour: int, is_weekend: bool) -> float:
    """
    Returns a realistic occupancy multiplier based on hour of day and weekend status.
    - Morning peak: 8:00 - 10:00 AM (80% - 95%)
    - Evening peak: 5:00 - 7:00 PM (85% - 98%)
    - Middle of day: 11:00 AM - 4:00 PM (60% - 80%)
    - Night / Off-peak: 10:00 PM - 6:00 AM (10% - 30%)
    """
    if is_weekend:
        # Weekends have more spread out afternoon occupancy
        if 12 <= hour <= 19:
            return random.uniform(0.70, 0.90)
        elif 20 <= hour <= 23:
            return random.uniform(0.40, 0.65)
        else:
            return random.uniform(0.10, 0.30)
    else:
        # Weekdays have standard commute spikes
        if 8 <= hour <= 10:
            return random.uniform(0.80, 0.95)
        elif 17 <= hour <= 19:
            return random.uniform(0.85, 0.98)
        elif 11 <= hour <= 16:
            return random.uniform(0.60, 0.80)
        else:
            return random.uniform(0.10, 0.35)


async def init_tables():
    """Ensure database tables exist in both targets."""
    logger.info("Initializing backend database tables...")
    async with backend_engine.begin() as conn:
        await conn.run_sync(BackendBase.metadata.create_all)

    logger.info("Initializing AI service database tables...")
    async with ai_engine.begin() as conn:
        await conn.run_sync(AIBase.metadata.create_all)


async def clear_databases():
    """Clear all records from backend and AI service tables."""
    logger.info("Clearing existing backend database tables...")
    async with BackendSessionLocal() as session:
        await session.execute(delete(BackendPayment))
        await session.execute(delete(BackendSession))
        await session.execute(delete(BackendReservation))
        await session.execute(delete(BackendSlot))
        await session.execute(delete(BackendFacility))
        await session.execute(delete(BackendUser))
        await session.commit()

    logger.info("Clearing existing AI service database tables...")
    async with AISessionLocal() as session:
        await session.execute(delete(AIOccupancyHistory))
        await session.execute(delete(AIReservationHistory))
        await session.execute(delete(AISessionHistory))
        await session.commit()


async def seed_backend():
    """Seed the core backend tables."""
    logger.info("Seeding backend tables...")
    async with BackendSessionLocal() as session:
        # 1. Create Users
        hashed_password = pwd_context.hash("strongpassword123")
        users = [
            BackendUser(
                email="admin@parkzenith.com",
                full_name="Zenith Administrator",
                phone="+15550100",
                vehicle_number="KA-01-Admin",
                password_hash=hashed_password,
                is_active=True,
                is_superuser=True,
            ),
            BackendUser(
                email="driver1@example.com",
                full_name="John Doe",
                phone="+15550101",
                vehicle_number="KA-01-JD-1234",
                password_hash=hashed_password,
                is_active=True,
                is_superuser=False,
            ),
            BackendUser(
                email="driver2@example.com",
                full_name="Jane Smith",
                phone="+15550102",
                vehicle_number="KA-01-JS-5678",
                password_hash=hashed_password,
                is_active=True,
                is_superuser=False,
            )
        ]
        session.add_all(users)
        await session.flush()  # populate IDs

        # 2. Create Facilities
        facilities = [
            BackendFacility(id=1, name="Zenith Plaza Lot", address="100 AI Blvd", city="Tech City", is_active=True),
            BackendFacility(id=2, name="City Mall Parking", address="250 Galleria Way", city="Tech City", is_active=True),
            BackendFacility(id=3, name="North Station Garage", address="50 Express Rd", city="Tech City", is_active=True),
        ]
        session.add_all(facilities)
        await session.flush()

        # 3. Create Slots
        slots = []
        for facility in facilities:
            prefix = "A" if facility.id == 1 else ("B" if facility.id == 2 else "C")
            for i in range(1, FACILITY_SLOT_COUNT + 1):
                # Mark ~20% of slots as occupied (is_available=False) by default in backend
                is_avail = random.random() > 0.20
                slot = BackendSlot(
                    facility_id=facility.id,
                    slot_number=f"{prefix}-{i:02d}",
                    is_available=is_avail
                )
                slots.append(slot)
        session.add_all(slots)
        await session.flush()

        # 4. Create Historical and Upcoming Reservations
        now = datetime.now(timezone.utc)
        reservations = []
        sessions = []
        payments = []

        # Create some completed reservations/sessions for the past 2 days
        for day_offset in range(1, 3):
            for u in users[1:]:
                res_time = now - timedelta(days=day_offset, hours=random.randint(1, 10))
                # Choose random slot
                slot = random.choice([s for s in slots if s.facility_id == 1])
                
                res = BackendReservation(
                    user_id=u.id,
                    slot_id=slot.id,
                    start_time=res_time,
                    end_time=res_time + timedelta(hours=2),
                    status=ReservationStatus.CONFIRMED,
                    created_at=res_time - timedelta(minutes=30),
                )
                reservations.append(res)
                await session.flush()

                # Session mapping to that reservation
                p_sess = BackendSession(
                    reservation_id=res.id,
                    slot_id=slot.id,
                    started_at=res_time + timedelta(minutes=5),
                    ended_at=res_time + timedelta(hours=2, minutes=5),
                    fee=10.0,
                )
                sessions.append(p_sess)
                await session.flush()

                # Payment record
                pay = BackendPayment(
                    user_id=u.id,
                    session_id=p_sess.id,
                    amount=10.0,
                    provider="stripe",
                    provider_reference=f"ch_{random.randint(100000, 999999)}",
                    created_at=res_time + timedelta(hours=2, minutes=10),
                )
                payments.append(pay)

        # Seed 1 upcoming reservation
        upcoming_res = BackendReservation(
            user_id=users[1].id,
            slot_id=slots[0].id,
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=4),
            status=ReservationStatus.CONFIRMED,
            created_at=now - timedelta(minutes=10),
        )
        reservations.append(upcoming_res)

        session.add_all(reservations)
        session.add_all(sessions)
        session.add_all(payments)
        await session.commit()
    logger.info("Core backend seeding completed successfully.")


async def seed_ai_service():
    """Seed the AI service analytics/history tables."""
    logger.info("Seeding AI Service tables...")
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=DAYS_TO_SEED)

    async with AISessionLocal() as session:
        # 1. Seed Occupancy History (Every 15 minutes for 7 days)
        current_time = start_time
        occupancy_records = []
        
        facilities = ["1", "2", "3"]
        zones = ["ZONE-A", "ZONE-B"]

        logger.info("Generating time-series occupancy logs for %d days...", DAYS_TO_SEED)
        while current_time <= now:
            is_wknd = current_time.weekday() >= 5
            hour = current_time.hour
            
            for fac in facilities:
                # Add overall facility occupancy
                multiplier = get_occupancy_pattern(hour, is_wknd)
                occ_slots = int(FACILITY_SLOT_COUNT * multiplier)
                occ_slots = min(max(occ_slots, 0), FACILITY_SLOT_COUNT)
                avail_slots = FACILITY_SLOT_COUNT - occ_slots
                occ_percentage = (occ_slots / FACILITY_SLOT_COUNT) * 100.0

                rec = AIOccupancyHistory(
                    facility_id=fac,
                    zone_id=None,
                    total_slots=FACILITY_SLOT_COUNT,
                    occupied_slots=occ_slots,
                    available_slots=avail_slots,
                    occupancy_percentage=occ_percentage,
                    collected_at=current_time,
                )
                occupancy_records.append(rec)

                # Add some zone occupancy
                for zone in zones:
                    zone_slots = FACILITY_SLOT_COUNT // 2
                    z_occ = int(zone_slots * get_occupancy_pattern(hour, is_wknd))
                    z_occ = min(max(z_occ, 0), zone_slots)
                    z_perc = (z_occ / zone_slots) * 100.0

                    z_rec = AIOccupancyHistory(
                        facility_id=fac,
                        zone_id=zone,
                        total_slots=zone_slots,
                        occupied_slots=z_occ,
                        available_slots=zone_slots - z_occ,
                        occupancy_percentage=z_perc,
                        collected_at=current_time,
                    )
                    occupancy_records.append(z_rec)

            current_time += timedelta(minutes=15)

        # Batch insert to avoid database performance limitations
        logger.info("Writing %d occupancy records to database...", len(occupancy_records))
        batch_size = 500
        for i in range(0, len(occupancy_records), batch_size):
            session.add_all(occupancy_records[i : i + batch_size])
            await session.flush()
        
        # 2. Seed Reservation History (AI telemetry copy)
        logger.info("Generating reservation telemetry records...")
        reservation_records = []
        for i in range(1, 30):
            res_start = now - timedelta(days=random.randint(0, DAYS_TO_SEED), hours=random.randint(0, 23))
            res_end = res_start + timedelta(hours=random.randint(1, 4))
            rec = AIReservationHistory(
                reservation_id=f"RES-{10000 + i}",
                facility_id=random.choice(facilities),
                slot_id=f"SLOT-{random.randint(1, FACILITY_SLOT_COUNT)}",
                reservation_status=random.choice(["COMPLETED", "CANCELLED", "NO_SHOW"]),
                reservation_start=res_start,
                reservation_end=res_end,
                duration_minutes=float((res_end - res_start).total_seconds() / 60.0),
            )
            reservation_records.append(rec)
        session.add_all(reservation_records)

        # 3. Seed Session History (AI telemetry copy)
        logger.info("Generating session telemetry records...")
        session_records = []
        for i in range(1, 40):
            sess_start = now - timedelta(days=random.randint(0, DAYS_TO_SEED), hours=random.randint(0, 23))
            sess_end = sess_start + timedelta(hours=random.randint(1, 4))
            rec = AISessionHistory(
                session_id=f"SESS-{90000 + i}",
                facility_id=random.choice(facilities),
                vehicle_type=random.choice(["CAR", "EV", "SUV", "BIKE"]),
                check_in_time=sess_start,
                check_out_time=sess_end,
                duration_minutes=float((sess_end - sess_start).total_seconds() / 60.0),
                parking_fee=random.uniform(5.0, 25.0),
            )
            session_records.append(rec)
        session.add_all(session_records)

        await session.commit()
    logger.info("AI Service telemetry database seeding completed successfully.")


async def main():
    logger.info("Starting ParkZenith database seeding...")
    await init_tables()
    await clear_databases()
    await seed_backend()
    await seed_ai_service()
    logger.info("ParkZenith database seeding run completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
