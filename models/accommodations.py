from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from config.db import PyObjectId
from bson import ObjectId
from models.newUser import GeoLocation


class AccommodationType(str, Enum):
    HOTEL = "hotel"
    APARTMENT = "apartment"
    HOSTEL = "hostel"
    LODGE = "lodge"


class Amenity(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None


class Room(BaseModel):
    name: str
    description: Optional[str] = None
    price_per_night: float
    capacity: int
    amenities: List[str] = []
    images: List[str] = []
    is_available: bool = True

class RoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_per_night: Optional[float] = None
    capacity: Optional[int] = None
    amenities: Optional[List[str]] = None
    images: Optional[List[str]] = None
    is_available: Optional[bool] = None


class AccommodationBase(BaseModel):
    name: str
    description: str
    accommodation_type: AccommodationType
    location: GeoLocation
    address: str
    city: str
    state: str
    country: str
    amenities: List[Amenity] = []
    rooms: List[Room] = []
    images: List[str] = []
    rating: Optional[float] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AccommodationCreate(AccommodationBase):
    pass


class AccommodationInDB(AccommodationBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_by: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    total_bookings: int = 0
    average_rating: float = 0.0
    reviews_count: int = 0


class AccommodationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    accommodation_type: Optional[AccommodationType] = None
    location: Optional[GeoLocation] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    amenities: Optional[List[Amenity]] = None
    rooms: Optional[List[Room]] = None
    images: Optional[List[str]] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AccommodationResponse(AccommodationBase):
    id: str = Field(..., alias="_id")
    created_at: Optional[datetime] = None
    average_rating: float = 0.0
    reviews_count: int = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AccommodationSearchParams(BaseModel):
    query: Optional[str] = None
    accommodation_type: Optional[AccommodationType] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    check_in_date: Optional[datetime] = None
    check_out_date: Optional[datetime] = None
    guests: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance: Optional[int] = 10000  # Default 10km radius
    sort_by: Optional[str] = "rating"  # rating, price, distance
    sort_order: Optional[str] = "desc"  # asc, desc
    page: int = 1
    limit: int = 10

