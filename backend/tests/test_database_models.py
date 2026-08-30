import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
import pytest_asyncio

from app.models.base import Base
from app.models.user import User
from app.models.admin import Admin, AdminRole
from app.models.parking_facility import ParkingFacility
from app.models.parking_zone import ParkingZone
from app.models.parking_slot import ParkingSlot, ParkingSlotStatus, VehicleType
from app.models.reservation import Reservation, ReservationStatus
from app.models.session import ParkingSession, ParkingSessionStatus
from app.models.payment import Payment, PaymentStatus, PaymentMethod

DATABASE_URL_TEST = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    DATABASE_URL_TEST,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

AsyncSessionLocalTest = async_sessionmaker(
    bind=engine_test,
    expire_on_commit=False,
    class_=AsyncSession,
)

@pytest_asyncio.fixture
async def db_session():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocalTest() as session:
        yield session
        
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_database_model_relationships(db_session: AsyncSession):
    # 1. Create User
    user = User(
        email="test_rel@example.com",
        password_hash="hashed_password",
        full_name="Test Rel"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 2. Create Admin
    admin = Admin(
        user_id=user.id,
        role=AdminRole.ADMIN
    )
    db_session.add(admin)

    # 3. Create Facility
    facility = ParkingFacility(
        name="Test Facility",
        address="123 Test St",
        total_slots=100
    )
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    # 4. Create Zone
    zone = ParkingZone(
        facility_id=facility.id,
        name="Zone A",
        total_slots=50
    )
    db_session.add(zone)
    await db_session.commit()
    await db_session.refresh(zone)

    # 5. Create Slot
    slot = ParkingSlot(
        zone_id=zone.id,
        slot_number="A1",
        status=ParkingSlotStatus.AVAILABLE,
        vehicle_type=VehicleType.CAR
    )
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(slot)

    # 6. Create Reservation
    start_time = datetime.now(timezone.utc) + timedelta(hours=1)
    end_time = datetime.now(timezone.utc) + timedelta(hours=3)
    reservation = Reservation(
        user_id=user.id,
        slot_id=slot.id,
        reservation_start=start_time,
        reservation_end=end_time,
        status=ReservationStatus.CONFIRMED
    )
    db_session.add(reservation)
    await db_session.commit()
    await db_session.refresh(reservation)

    # 7. Create Session
    session = ParkingSession(
        user_id=user.id,
        slot_id=slot.id,
        reservation_id=reservation.id,
        check_in_time=start_time,
        duration_minutes=120,
        status=ParkingSessionStatus.COMPLETED,
        fee_amount=15.00
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # 8. Create Payment
    payment = Payment(
        session_id=session.id,
        user_id=user.id,
        amount=15.00,
        payment_method=PaymentMethod.CARD,
        payment_status=PaymentStatus.SUCCESS,
        transaction_id="TXN123456"
    )
    db_session.add(payment)
    await db_session.commit()
    await db_session.refresh(payment)

    # Queries to verify relationships
    from sqlalchemy.orm import selectinload
    stmt = select(User).options(
        selectinload(User.admin),
        selectinload(User.reservations),
        selectinload(User.sessions),
        selectinload(User.payments)
    ).where(User.id == user.id)
    result = await db_session.execute(stmt)
    db_user = result.scalar_one()

    assert db_user.admin is not None
    assert db_user.admin.role == AdminRole.ADMIN
    assert len(db_user.reservations) > 0
    assert len(db_user.sessions) > 0
    assert len(db_user.payments) > 0

    stmt_fac = select(ParkingFacility).options(selectinload(ParkingFacility.zones)).where(ParkingFacility.id == facility.id)
    result_fac = await db_session.execute(stmt_fac)
    db_fac = result_fac.scalar_one()
    assert db_fac.zones[0].name == "Zone A"

    stmt_zone = select(ParkingZone).options(selectinload(ParkingZone.slots)).where(ParkingZone.id == zone.id)
    result_zone = await db_session.execute(stmt_zone)
    db_zone = result_zone.scalar_one()
    assert db_zone.slots[0].slot_number == "A1"

    stmt_slot = select(ParkingSlot).options(selectinload(ParkingSlot.reservations)).where(ParkingSlot.id == slot.id)
    result_slot = await db_session.execute(stmt_slot)
    db_slot = result_slot.scalar_one()
    assert db_slot.reservations[0].status == ReservationStatus.CONFIRMED

    stmt_session = select(ParkingSession).options(selectinload(ParkingSession.payment)).where(ParkingSession.id == session.id)
    result_session = await db_session.execute(stmt_session)
    db_session_obj = result_session.scalar_one()
    assert db_session_obj.payment.transaction_id == "TXN123456"
