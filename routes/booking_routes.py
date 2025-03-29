from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime

from config.db import db
from models.newUser import UserInDB
from models.newBooking import (
    BookingCreate, BookingInDB, BookingUpdate,
    BookingResponse, BookingWithDetails, BookingStatus, PaymentStatus
)

# from models.newPayment import PaymentStatus
from utils.auth import get_current_active_user
from utils.email_util import send_booking_confirmation

router = APIRouter()


@router.post("/", response_model=BookingResponse)
def create_booking(
    booking_data: BookingCreate = Body(...),
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Check if accommodation exists
    if not ObjectId.is_valid(str(booking_data.accommodation_id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    accommodation = db.accommodations.find_one({"_id": ObjectId(booking_data.accommodation_id)})

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Check if room exists and is available
    if "rooms" not in accommodation or not accommodation["rooms"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rooms available for this accommodation"
        )

    # Find the room
    room_index = -1
    for i, room in enumerate(accommodation["rooms"]):
        if str(i) == booking_data.room_id:
            room_index = i
            break

    if room_index == -1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

    room = accommodation["rooms"][room_index]

    if not room.get("is_available", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room is not available"
        )

    # Check if room is already booked for the requested dates
    existing_booking = db.bookings.find_one({
        "accommodation_id": booking_data.accommodation_id,
        "room_id": booking_data.room_id,
        "booking_status": {"$in": ["pending", "confirmed"]},
        "$or": [
            {
                "check_in_date": {"$lte": booking_data.check_in_date},
                "check_out_date": {"$gte": booking_data.check_in_date}
            },
            {
                "check_in_date": {"$lte": booking_data.check_out_date},
                "check_out_date": {"$gte": booking_data.check_out_date}
            },
            {
                "check_in_date": {"$gte": booking_data.check_in_date},
                "check_out_date": {"$lte": booking_data.check_out_date}
            }
        ]
    })

    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room is already booked for the requested dates"
        )

    # Calculate total price
    days = (booking_data.check_out_date - booking_data.check_in_date).days
    total_price = days * room.get("price_per_night", 0)

    # Create booking
    booking_dict = booking_data.dict()
    booking_dict["user_id"] = current_user.id
    booking_dict["total_price"] = total_price
    booking_dict["booking_status"] = BookingStatus.PENDING
    booking_dict["payment_status"] = PaymentStatus.PENDING
    booking_dict["created_at"] = datetime.utcnow()

    # Insert booking into database
    result = db.bookings.insert_one(booking_dict)

    # Update accommodation booking count
    db.accommodations.update_one(
        {"_id": booking_data.accommodation_id},
        {"$inc": {"total_bookings": 1}}
    )

    # Get created booking
    created_booking = db.bookings.find_one({"_id": result.inserted_id})

    # Send booking confirmation email
    booking_with_details = BookingWithDetails(
        _id=str(created_booking["_id"]),
        user_id=str(created_booking["user_id"]),
        accommodation_id=str(created_booking["accommodation_id"]),
        total_price=created_booking["total_price"],
        booking_status=created_booking["booking_status"],
        payment_status=created_booking["payment_status"],
        created_at=created_booking["created_at"],
        accommodation_details=accommodation,
        user_details=current_user.dict(),
        check_in_date=created_booking["check_in_date"],
        check_out_date=created_booking["check_out_date"],
        guests=created_booking["guests"],
        room_id=created_booking["room_id"],
        special_requests=created_booking.get("special_requests"),

    )
    send_booking_confirmation(booking_with_details)

    return BookingResponse(**created_booking)

@router.get("/", response_model=List[BookingResponse])
def get_bookings(
    status: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Build query
    query = {"user_id": current_user.id}

    if status:
        query["booking_status"] = status

    # Get bookings
    bookings = list(db.bookings.find(query).sort("created_at", -1))

    # Convert ObjectId to string for each booking
    booking_responses = []
    for booking in bookings:
        booking_response = BookingResponse(
            _id=str(booking["_id"]),  # Convert ObjectId to string
            user_id=str(booking["user_id"]),
            accommodation_id=str(booking["accommodation_id"]),
            total_price=booking["total_price"],
            booking_status=booking["booking_status"],
            payment_status=booking["payment_status"],
            created_at=booking["created_at"],
            check_in_date=booking["check_in_date"],
            check_out_date=booking["check_out_date"],
            guests=booking["guests"],
            room_id=booking["room_id"],
            special_requests=booking.get("special_requests"),
        )
        booking_responses.append(booking_response)

    return booking_responses

@router.get("/{booking_id}", response_model=BookingWithDetails)
def get_booking(
    booking_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Check if booking exists
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid booking ID"
        )

    booking = db.bookings.find_one({
        "_id": ObjectId(booking_id),
        "user_id": current_user.id
    })

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Get accommodation details
    accommodation = db.accommodations.find_one({"_id": ObjectId(booking["accommodation_id"])})

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Function to convert ObjectId to string in dictionaries
    def convert_objectid_to_str(data: Dict[str, Any]) -> Dict[str, Any]:
        converted_data = {}
        for key, value in data.items():
            if isinstance(value, ObjectId):
                converted_data[key] = str(value)
            elif isinstance(value, dict):
                converted_data[key] = convert_objectid_to_str(value)
            elif isinstance(value, list):
                converted_data[key] = [
                    str(item) if isinstance(item, ObjectId) else (
                        convert_objectid_to_str(item) if isinstance(item, dict) else item
                    ) for item in value
                ]
            else:
                converted_data[key] = value
        return converted_data

    # Convert ObjectId to string in accommodation and user details
    converted_accommodation = convert_objectid_to_str(accommodation)
    converted_user_details = convert_objectid_to_str(current_user.dict())

    # Create response
    booking_with_details = BookingWithDetails(
        _id=str(booking["_id"]),
        user_id=str(booking["user_id"]),
        accommodation_id=str(booking["accommodation_id"]),
        total_price=booking["total_price"],
        booking_status=booking["booking_status"],
        payment_status=booking["payment_status"],
        created_at=booking["created_at"],
        accommodation_details=converted_accommodation,
        user_details=converted_user_details,
        check_in_date=booking["check_in_date"],
        check_out_date=booking["check_out_date"],
        guests=booking["guests"],
        room_id=booking["room_id"],
        special_requests=booking.get("special_requests"),
    )

    return booking_with_details

@router.put("/{booking_id}", response_model=BookingResponse)
def update_booking(
    booking_id: str,
    booking_update: BookingUpdate = Body(...),
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Check if booking exists
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid booking ID"
        )

    booking = db.bookings.find_one({
        "_id": ObjectId(booking_id),
        "user_id": current_user.id
    })

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Check if booking can be updated
    if booking["booking_status"] in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update a {booking['booking_status']} booking"
        )

    # Filter out None values
    update_data = {k: v for k, v in booking_update.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )

    # Update timestamp
    update_data["updated_at"] = datetime.utcnow()

    # Update booking in database
    db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": update_data}
    )

    # Get updated booking
    updated_booking = db.bookings.find_one({"_id": ObjectId(booking_id)})

    # Convert ObjectId to string
    booking_response = BookingResponse(
        _id=str(updated_booking["_id"]),
        user_id=str(updated_booking["user_id"]),
        accommodation_id=str(updated_booking["accommodation_id"]),
        total_price=updated_booking["total_price"],
        booking_status=updated_booking["booking_status"],
        payment_status=updated_booking["payment_status"],
        created_at=updated_booking["created_at"],
        check_in_date = updated_booking["check_in_date"],
        check_out_date = updated_booking["check_out_date"],
        guests = updated_booking["guests"],
        room_id = updated_booking["room_id"],
        special_requests = updated_booking.get("special_requests"),

    )

    return booking_response

@router.delete("/{booking_id}", response_model=BookingResponse)
def cancel_booking(
        booking_id: str,
        current_user: UserInDB = Depends(get_current_active_user)
):
    # Check if booking exists
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid booking ID"
        )

    booking = db.bookings.find_one({
        "_id": ObjectId(booking_id),
        "user_id": current_user.id
    })

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Check if booking can be cancelled
    if booking["booking_status"] in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a {booking['booking_status']} booking"
        )

    # Update booking in database
    db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {
            "$set": {
                "booking_status": BookingStatus.CANCELLED,
                "updated_at": datetime.utcnow()
            }
        }
    )

    # Get updated booking
    updated_booking = db.bookings.find_one({"_id": ObjectId(booking_id)})

    return BookingResponse(**updated_booking)

