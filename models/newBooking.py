from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from config.db import PyObjectId
from bson import ObjectId


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class BookingBase(BaseModel):
    accommodation_id: PyObjectId
    room_id: str  # This would be the index or ID of the room in the accommodation
    check_in_date: datetime
    check_out_date: datetime
    guests: int
    special_requests: Optional[str] = None

    @validator('check_out_date')
    def check_dates(cls, v, values):
        if 'check_in_date' in values and v <= values['check_in_date']:
            raise ValueError('Check-out date must be after check-in date')
        return v

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class BookingCreate(BookingBase):
    pass


class BookingInDB(BookingBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    total_price: float
    booking_status: BookingStatus = BookingStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payment_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BookingUpdate(BaseModel):
    booking_status: Optional[BookingStatus] = None
    payment_status: Optional[PaymentStatus] = None
    payment_id: Optional[str] = None
    special_requests: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class BookingResponse(BookingBase):
    id: str = Field(..., alias="_id")
    user_id: str
    accommodation_id: str
    total_price: float
    booking_status: BookingStatus
    payment_status: PaymentStatus
    created_at: datetime

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class BookingWithDetails(BookingResponse):
    accommodation_details: Dict[str, Any]
    user_details: Dict[str, Any]

