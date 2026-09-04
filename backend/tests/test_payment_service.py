import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from backend.app.models.base import Base
from backend.app.models.user import User
from backend.app.models.parking_slot import ParkingSlot, ParkingSlotStatus, VehicleType
from backend.app.models.parking_zone import ParkingZone
from backend.app.models.parking_facility import ParkingFacility
from backend.app.models.session import ParkingSession, ParkingSessionStatus
from backend.app.models.payment import PaymentMethod, PaymentStatus
from backend.app.services.payment_service import payment_service
from backend.app.schemas.session import SessionCreate
from backend.app.services.session_service import session_service

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

def test_fee_calculation():
    # Negative/Zero duration
    assert payment_service.calculate_fee(-10) == Decimal('0.00')
    assert payment_service.calculate_fee(0) == Decimal('0.00')
    
    # Below minimum
    assert payment_service.calculate_fee(10) == Decimal('2.00') # 10 mins = 0.16h * 5 = 0.83 < 2.00
    
    # 1 hour
    assert payment_service.calculate_fee(60) == Decimal('5.00')
    
    # 2.5 hours
    assert payment_service.calculate_fee(150) == Decimal('12.50')

@pytest.mark.asyncio
async def test_duplicate_payment_creation(db_session: AsyncSession):
    user = User(email="t1@example.com", password_hash="hash", full_name="User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 1. Create Payment
    payment1 = await payment_service.create_payment(db_session, 100, user.id, Decimal('5.00'))
    assert payment1.payment_status == PaymentStatus.PENDING
    
    # 2. Try to create again for same session
    payment2 = await payment_service.create_payment(db_session, 100, user.id, Decimal('5.00'))
    assert payment1.id == payment2.id # should return the existing pending payment

@pytest.mark.asyncio
async def test_payment_status_transitions(db_session: AsyncSession):
    user = User(email="t2@example.com", password_hash="hash", full_name="User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    payment = await payment_service.create_payment(db_session, 200, user.id, Decimal('5.00'))
    
    # Cannot process by wrong user
    with pytest.raises(HTTPException) as exc:
        await payment_service.process_payment(db_session, payment.id, user_id=999)
    assert exc.value.status_code == 403

    # Process normally
    processed = await payment_service.process_payment(db_session, payment.id, user.id, simulate_success=True)
    assert processed.payment_status == PaymentStatus.SUCCESS
    assert processed.transaction_id is not None
    
    # Cannot process already successful
    with pytest.raises(HTTPException) as exc:
        await payment_service.process_payment(db_session, payment.id, user.id)
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_end_session_payment_integration(db_session: AsyncSession):
    # Setup user, facility, zone, slot
    user = User(email="t3@example.com", password_hash="hash", full_name="User")
    db_session.add(user)
    
    fac = ParkingFacility(name="F1", address="A1", total_slots=10)
    db_session.add(fac)
    await db_session.flush()
    
    zone = ParkingZone(facility_id=fac.id, name="Z1", total_slots=10)
    db_session.add(zone)
    await db_session.flush()
    
    slot = ParkingSlot(zone_id=zone.id, slot_number="S1")
    db_session.add(slot)
    await db_session.commit()

    # Start session
    sess_in = SessionCreate(slot_id=slot.id)
    session = await session_service.start_session(db_session, user.id, sess_in)
    
    # Fast forward check-in time by 2 hours
    session.check_in_time = session.check_in_time - timedelta(hours=2)
    db_session.add(session)
    await db_session.commit()
    
    # End session
    ended = await session_service.end_session(db_session, session.id, user.id)
    assert ended.status == ParkingSessionStatus.COMPLETED
    assert ended.duration_minutes >= 120
    assert ended.fee_amount >= Decimal('10.00')
    
    # Verify payment was created
    payment = await payment_service.get_session_payment(db_session, session.id)
    assert payment is not None
    assert payment.amount == ended.fee_amount
    assert payment.payment_status == PaymentStatus.PENDING
