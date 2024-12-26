from fastapi import APIRouter, HTTPException, Depends
from models.booking import Booking
from models.user import User
from typing import List, Optional
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
from bson.objectid import ObjectId
from datetime import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from models.property import Property
from routes.auth import oauth2_scheme, admin_required
from bson import ObjectId

load_dotenv()

mongo_url = os.getenv("MONGO_URL")
client = MongoClient(mongo_url)
db = client['hotel_booking']

router = APIRouter()


# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/signin")


class BookingInput(BaseModel):
    property_id: str
    start_date: str  # Date format YYYY-MM-DD
    end_date: str  # Date format YYYY-MM-DD


class BookingResponse(BaseModel):
    booking_id: str
    property_id: str
    start_date: str
    end_date: str
    total_price: float
    property_type: str


class BookingUpdateInput(BaseModel):
    start_date: str  # Date format YYYY-MM-DD
    end_date: str


def objectid_to_str(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {key: objectid_to_str(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [objectid_to_str(item) for item in obj]
    return obj


@router.get("/bookings")
async def get_all_bookings(user: dict = Depends(admin_required)):
    bookings_collection = db['bookings']
    all_bookings = list(bookings_collection.find())
    return {"bookings": [objectid_to_str(booking) for booking in all_bookings]}


@router.post("/bookings")
async def create_booking(booking_data: BookingInput, token: str = Depends(oauth2_scheme)):
    user = User.find_by_id(token)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    property_instance = Property.find_by_id(booking_data.property_id)
    if not property_instance:
        raise HTTPException(status_code=404, detail="Property not found")

    # Calculate total price based on property type and dates
    start_date = datetime.strptime(booking_data.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(booking_data.end_date, "%Y-%m-%d")
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    days = (end_date - start_date).days
    if "price_per_night" in property_instance:
        total_price = days * property_instance["price_per_night"]
        property_type = "Hotel"
    elif "price_per_month" in property_instance:
        total_price = (days / 30) * property_instance["price_per_month"]
        property_type = "Apartment"
    else:
        raise HTTPException(status_code=400, detail="Invalid property pricing")

    booking_instance = Booking(
        user_id=str(user["_id"]),
        property_id=booking_data.property_id,
        start_date=booking_data.start_date,
        end_date=booking_data.end_date,
        total_price=total_price,
        property_type=property_type
    )
    booking_id = booking_instance.save()
    return {"message": "Booking successful", "booking_id": booking_id, "total_price": total_price}


@router.get("/bookings/{user_id}")
async def get_user_bookings(user_id: str, user: dict = Depends(oauth2_scheme)):
    bookings = Booking.get_user_bookings(user_id)
    return {"bookings": bookings}


@router.get("/bookings/details/{booking_id}")
async def get_booking_details(booking_id: str, user: dict = Depends(admin_required)):
    booking = Booking.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking_data = objectid_to_str(booking)

    return booking_data


@router.put("/bookings/{booking_id}")
async def update_booking(booking_id: str, booking_data: BookingUpdateInput, token: str = Depends(oauth2_scheme)):
    user = User.find_by_id(token)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    booking = Booking.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking["user_id"] != str(user["_id"]) and not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="You do not have permission to update this booking")

    start_date = datetime.strptime(booking_data.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(booking_data.end_date, "%Y-%m-%d")
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    bookings_collection = db['bookings']
    result = bookings_collection.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"start_date": booking_data.start_date, "end_date": booking_data.end_date}}
    )

    if result.modified_count == 1:
        return {"message": "Booking updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update booking")


@router.delete("/bookings/{booking_id}")
async def cancel_booking(booking_id: str, token: str = Depends(oauth2_scheme)):
    user = User.find_by_id(token)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    booking = Booking.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking["user_id"] != str(user["_id"]) and not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="You do not have permission to cancel this booking")

    bookings_collection = db['bookings']
    result = bookings_collection.delete_one({"_id": ObjectId(booking_id)})

    if result.deleted_count == 1:
        return {"message": "Booking cancelled successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to cancel booking")
