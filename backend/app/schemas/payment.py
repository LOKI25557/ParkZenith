from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from decimal import Decimal
from ..models.payment import PaymentMethod, PaymentStatus

class PaymentBase(BaseModel):
    amount: Decimal
    payment_method: PaymentMethod

class PaymentCreate(PaymentBase):
    session_id: int

class PaymentProcess(BaseModel):
    simulate_success: bool = True
    transaction_id: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None

class PaymentResponse(PaymentBase):
    id: int
    session_id: int
    user_id: int
    payment_status: PaymentStatus
    transaction_id: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
