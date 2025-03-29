from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from config.db import PyObjectId
from bson import ObjectId
from models.newBooking import PaymentStatus


class PaymentMethod(str, Enum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    USSD = "ussd"
    QR = "qr"
    MOBILE_MONEY = "mobile_money"


class PaymentBase(BaseModel):
    booking_id: PyObjectId
    amount: float
    payment_method: PaymentMethod

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class PaymentCreate(PaymentBase):
    pass


class PaymentInDB(PaymentBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    reference: str
    paystack_reference: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    response_data: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    paystack_reference: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class PaymentResponse(PaymentBase):
    id: str = Field(..., alias="_id")
    user_id: str
    booking_id: str
    reference: str
    status: PaymentStatus
    created_at: datetime

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class PaymentInitiateRequest(BaseModel):
    booking_id: str
    payment_method: PaymentMethod
    email: Optional[str] = None
    callback_url: Optional[str] = None


class PaymentVerifyRequest(BaseModel):
    reference: str

