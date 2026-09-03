from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ...schemas.payment import PaymentResponse, PaymentProcess, PaymentCreate
from ...services.payment_service import payment_service
from ...core.dependencies import get_current_user
from ...database.session import get_async_session as get_db
from ...models.user import User

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.get("/me", response_model=List[PaymentResponse])
async def get_my_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve payment history for the current user."""
    return await payment_service.get_user_payments(db, current_user.id, skip, limit)

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get details for a specific payment."""
    payment = await payment_service.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to view this payment")
    return payment

@router.get("/session/{session_id}", response_model=PaymentResponse)
async def get_session_payment(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the payment for a specific session."""
    payment = await payment_service.get_session_payment(db, session_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found for this session")
    if payment.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to view this payment")
    return payment

@router.post("/{payment_id}/process", response_model=PaymentResponse)
async def process_payment(
    payment_id: int,
    process_data: PaymentProcess,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Process a pending payment."""
    return await payment_service.process_payment(
        db=db,
        payment_id=payment_id,
        user_id=current_user.id,
        simulate_success=process_data.simulate_success,
        transaction_id=process_data.transaction_id,
        payment_method=process_data.payment_method
    )
