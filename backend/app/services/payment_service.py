from decimal import Decimal
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException

from ..models.payment import Payment, PaymentStatus, PaymentMethod

class PaymentService:
    BASE_HOURLY_RATE = Decimal('5.00')
    MINIMUM_CHARGE = Decimal('2.00')
    
    def __init__(self):
        self._processing_lock = asyncio.Lock()

    def calculate_fee(self, duration_minutes: int) -> Decimal:
        """Calculate the parking fee based on duration."""
        if duration_minutes <= 0:
            return Decimal('0.00')
            
        hours = duration_minutes / 60.0
        fee = Decimal(str(hours)) * self.BASE_HOURLY_RATE
        
        # Round to 2 decimal places
        fee = fee.quantize(Decimal('0.01'))
        
        # Apply minimum charge if fee is less than minimum but duration is > 0
        if fee < self.MINIMUM_CHARGE:
            return self.MINIMUM_CHARGE
            
        return fee

    async def create_payment(
        self, 
        db: AsyncSession, 
        session_id: int, 
        user_id: int, 
        amount: Decimal, 
        method: PaymentMethod = PaymentMethod.ONLINE
    ) -> Payment:
        """Create a new pending payment."""
        # Check if payment already exists for this session
        existing_stmt = select(Payment).where(Payment.session_id == session_id)
        existing = (await db.execute(existing_stmt)).scalars().first()
        if existing:
            return existing
            
        payment = Payment(
            session_id=session_id,
            user_id=user_id,
            amount=amount,
            payment_method=method,
            payment_status=PaymentStatus.PENDING
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        return payment

    async def get_payment(self, db: AsyncSession, payment_id: int) -> Optional[Payment]:
        stmt = select(Payment).where(Payment.id == payment_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_session_payment(self, db: AsyncSession, session_id: int) -> Optional[Payment]:
        stmt = select(Payment).where(Payment.session_id == session_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_user_payments(self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Payment]:
        stmt = select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc()).offset(skip).limit(limit)
        return list((await db.execute(stmt)).scalars().all())
        
    async def process_payment(
        self, 
        db: AsyncSession, 
        payment_id: int, 
        user_id: int, 
        simulate_success: bool = True,
        transaction_id: Optional[str] = None,
        payment_method: Optional[PaymentMethod] = None
    ) -> Payment:
        async with self._processing_lock:
            # We must use with_for_update if possible, but asyncio.Lock protects local concurrency
            payment = await self.get_payment(db, payment_id)
            if not payment:
                raise HTTPException(status_code=404, detail="Payment not found")
                
            if payment.user_id != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to process this payment")
                
            if payment.payment_status == PaymentStatus.SUCCESS:
                raise HTTPException(status_code=400, detail="Payment is already successful")
                
            if payment.payment_status == PaymentStatus.REFUNDED:
                raise HTTPException(status_code=400, detail="Cannot process a refunded payment")
                
            # Update payment method if provided
            if payment_method:
                payment.payment_method = payment_method
    
            if simulate_success:
                payment.payment_status = PaymentStatus.SUCCESS
                payment.paid_at = datetime.now(timezone.utc)
                payment.transaction_id = transaction_id or f"TXN-{uuid.uuid4().hex[:8].upper()}"
            else:
                payment.payment_status = PaymentStatus.FAILED
                
            db.add(payment)
            await db.commit()
            await db.refresh(payment)
            return payment

payment_service = PaymentService()
