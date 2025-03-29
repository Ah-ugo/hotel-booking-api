from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File, Form, Query
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
import logging
from config.db import db
from models.newUser import UserInDB, UserResponse
from models.accommodations import (
    AccommodationCreate, AccommodationInDB, AccommodationUpdate,
    AccommodationResponse, Room, Amenity, RoomUpdate
)
from models.newBooking import BookingResponse, BookingWithDetails
from utils.auth import get_current_admin_user, get_current_user
from utils.cloudinary_util import upload_image, delete_image
from utils.location import geocode_address

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


@router.get("/", response_model=List[AccommodationResponse])
def get_all_accommodations(
    current_user: Optional[UserInDB] = Depends(get_current_user) # Optional user dependency
):
    """Get all accommodations."""
    accommodations = list(db.accommodations.find())
    for accommodation in accommodations:
        accommodation["_id"] = str(accommodation["_id"])

        # Check if created_at exists, if not, create a dummy value.
        if "created_at" not in accommodation:
            accommodation["created_at"] = datetime.utcnow() # or some other default value

    return accommodations


@router.get("/{accommodation_id}", response_model=AccommodationResponse)
def get_accommodation_by_id(accommodation_id: str, current_user: Optional[UserInDB] = Depends(get_current_user)):
    logger.info(f"Fetching accommodation with ID: {accommodation_id}")

    if not ObjectId.is_valid(accommodation_id):
        logger.warning("Invalid accommodation ID provided")
        raise HTTPException(status_code=400, detail="Invalid accommodation ID")

    accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if not accommodation:
        logger.error("Accommodation not found")
        raise HTTPException(status_code=404, detail="Accommodation not found")

    logger.info(f"Accommodation found: {accommodation}")

    accommodation["_id"] = str(accommodation["_id"])
    return accommodation


@router.get("/{accommodation_id}/rooms", response_model=List[Room])
def get_accommodation_rooms(
        accommodation_id: str,
        current_user: Optional[UserInDB] = Depends(get_current_user)  # Optional user dependency
):
    """Get rooms for a specific accommodation."""
    if not ObjectId.is_valid(accommodation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    if "rooms" not in accommodation:
        return []  # Return empty list if no rooms are found

    return accommodation["rooms"]

@router.post("/accommodations", response_model=AccommodationResponse)
def create_accommodation(
    accommodation_data: AccommodationCreate = Body(...),
    current_user: UserInDB = Depends(get_current_admin_user)
):
    # Create accommodation
    accommodation_dict = accommodation_data.dict()
    accommodation_dict["created_by"] = current_user.id
    accommodation_dict["created_at"] = datetime.utcnow()  # Add created_at

    # Insert accommodation into database
    result = db.accommodations.insert_one(accommodation_dict)

    # Get created accommodation
    created_accommodation = db.accommodations.find_one({"_id": result.inserted_id})

    if created_accommodation:
        created_accommodation["_id"] = str(created_accommodation["_id"])  # Convert _id to string
        return AccommodationResponse(**created_accommodation)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create accommodation")

@router.put("/accommodations/{accommodation_id}", response_model=AccommodationResponse)
def update_accommodation(
    accommodation_id: str,
    accommodation_update: AccommodationUpdate = Body(...),
    current_user: UserInDB = Depends(get_current_admin_user)
):
    # Check if accommodation exists
    if not ObjectId.is_valid(accommodation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Filter out None values
    update_data = {k: v for k, v in accommodation_update.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )

    # Update timestamp
    update_data["updated_at"] = datetime.utcnow()

    # Update accommodation in database
    db.accommodations.update_one(
        {"_id": ObjectId(accommodation_id)},
        {"$set": update_data}
    )

    # Get updated accommodation
    updated_accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if updated_accommodation:
        updated_accommodation["_id"] = str(updated_accommodation["_id"])  # Convert _id to string
        return AccommodationResponse(**updated_accommodation)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated accommodation")

@router.post("/accommodations/{accommodation_id}/images", response_model=AccommodationResponse)
def upload_accommodation_images(
    accommodation_id: str,
    files: List[UploadFile] = File(...),
    current_user: UserInDB = Depends(get_current_admin_user)
):
    # Check if accommodation exists
    if not ObjectId.is_valid(accommodation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Upload images to Cloudinary
    image_urls = []
    for file in files:
        image_url = upload_image(file, folder="accommodation_images")
        image_urls.append(image_url)

    # Update accommodation in database
    db.accommodations.update_one(
        {"_id": ObjectId(accommodation_id)},
        {
            "$push": {"images": {"$each": image_urls}},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    # Get updated accommodation
    updated_accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if updated_accommodation:
        updated_accommodation["_id"] = str(updated_accommodation["_id"])  # Convert _id to string
        return AccommodationResponse(**updated_accommodation)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated accommodation")

@router.delete("/accommodations/{accommodation_id}/images/{image_index}", response_model=AccommodationResponse)
def delete_accommodation_image(
    accommodation_id: str,
    image_index: int,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    # Check if accommodation exists
    if not ObjectId.is_valid(accommodation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Check if image exists
    if "images" not in accommodation or image_index >= len(accommodation["images"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    # Get image URL
    image_url = accommodation["images"][image_index]

    # Delete image from Cloudinary
    delete_image(image_url)

    # Update accommodation in database
    db.accommodations.update_one(
        {"_id": ObjectId(accommodation_id)},
        {
            "$pull": {"images": image_url},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    # Get updated accommodation
    updated_accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if updated_accommodation:
        updated_accommodation["_id"] = str(updated_accommodation["_id"])  # Convert _id to string
        return AccommodationResponse(**updated_accommodation)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated accommodation")


@router.post("/accommodations/{accommodation_id}/rooms", response_model=AccommodationResponse)
def add_room(
    accommodation_id: str,
    room: Room = Body(...),
    current_user: UserInDB = Depends(get_current_admin_user)
):
    # Check if accommodation exists
    if not ObjectId.is_valid(accommodation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Update accommodation in database
    db.accommodations.update_one(
        {"_id": ObjectId(accommodation_id)},
        {
            "$push": {"rooms": room.dict()},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    # Get updated accommodation
    updated_accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if updated_accommodation:
        updated_accommodation["_id"] = str(updated_accommodation["_id"])  # Convert _id to string
        return AccommodationResponse(**updated_accommodation)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated accommodation")


@router.put("/accommodations/{accommodation_id}/rooms/{room_index}", response_model=AccommodationResponse)
def update_room(
        accommodation_id: str,
        room_index: int,
        room: RoomUpdate = Body(...),  # Use RoomUpdate
        current_user: UserInDB = Depends(get_current_admin_user)
):
    # Check if accommodation exists
    if not ObjectId.is_valid(accommodation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Check if room exists
    if "rooms" not in accommodation or room_index >= len(accommodation["rooms"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

    room_data = room.dict(exclude_unset=True)  # get only the set values from the request.

    # Update room
    db.accommodations.update_one(
        {"_id": ObjectId(accommodation_id)},
        {
            "$set": {
                f"rooms.{room_index}.{key}": value for key, value in room_data.items()
            },
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    # Get updated accommodation
    updated_accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if updated_accommodation:
        updated_accommodation["_id"] = str(updated_accommodation["_id"])
        return AccommodationResponse(**updated_accommodation)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to retrieve updated accommodation")


@router.delete("/accommodations/{accommodation_id}/rooms/{room_index}", response_model=AccommodationResponse)
def delete_room(
    accommodation_id: str,
    room_index: int,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    # Check if accommodation exists
    if not ObjectId.is_valid(accommodation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Check if room exists
    if "rooms" not in accommodation or room_index >= len(accommodation["rooms"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

    # Get room
    room = accommodation["rooms"][room_index]

    # Update accommodation in database
    db.accommodations.update_one(
        {"_id": ObjectId(accommodation_id)},
        {
            "$pull": {"rooms": room},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    # Get updated accommodation
    updated_accommodation = db.accommodations.find_one({"_id": ObjectId(accommodation_id)})

    if updated_accommodation:
        updated_accommodation["_id"] = str(updated_accommodation["_id"])  # Convert _id to string
        return AccommodationResponse(**updated_accommodation)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated accommodation")


@router.get("/all/bookings", response_model=List[BookingResponse])
def get_all_bookings(
        status: Optional[str] = Query(None),
        accommodation_id: Optional[str] = Query(None),
        current_user: UserInDB = Depends(get_current_admin_user)
):
    logger.info(f"Received accommodation_id: {accommodation_id}")
    print(f"Received accommodation_id: {accommodation_id}")

    # Build query
    query = {}

    if status:
        query["booking_status"] = status

    if accommodation_id:
        query["accommodation_id"] = accommodation_id

    logger.info(f"Final Query: {query}")

    # Get bookings
    bookings = list(db.bookings.find(query))
    logger.info(f"Bookings found: {len(bookings)} records")

    # Convert ObjectId to string for response
    booking_responses = []
    for booking in bookings:
        try:
            booking_responses.append(
                BookingResponse(
                    _id=str(booking["_id"]),
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
            )
        except (TypeError, ValueError) as e:
            logger.error(f"Error creating BookingResponse: {e}, Booking data: {booking}")
            # Consider how to handle the error. You might want to skip the booking, return an error, etc.
            # Example:
            # continue
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    return booking_responses

# @router.get("/me/bookings", response_model=Dict[str, Any])
# def get_bookings(
#         status: Optional[str] = Query(None),
#         accommodation_id: Optional[str] = Query(None)
# ):
#     bookings_collection = db.bookings
#     query = {}
#
#     # Validate and convert accommodation_id if provided
#     if accommodation_id:
#         if not ObjectId.is_valid(accommodation_id):
#             raise HTTPException(status_code=400, detail="Invalid accommodation ID")
#         query["accommodation_id"] = ObjectId(accommodation_id)
#
#     # Add status filter if provided
#     if status:
#         query["booking_status"] = status.lower()
#
#     # Fetch bookings from the database
#     bookings = list(bookings_collection.find(query))
#
#     # Convert ObjectId fields to strings for JSON serialization
#     for booking in bookings:
#         booking["_id"] = str(booking["_id"])
#         booking["accommodation_id"] = str(booking["accommodation_id"])
#         booking["user_id"] = str(booking["user_id"])
#
#     return {"status": "success", "data": bookings}



@router.get("/all/users", response_model=List[UserResponse])
def get_all_users(
        current_user: UserInDB = Depends(get_current_admin_user)
):
    # Get users
    users = list(db.users.find().sort("created_at", -1))

    # Convert ObjectId to string for response
    user_responses = []
    for user in users:
        user["_id"] = str(user["_id"])  # Convert ObjectId to string
        user_responses.append(UserResponse(**user))

    return user_responses


@router.get("/dashboard/stats")
def get_dashboard_stats(
        current_user: UserInDB = Depends(get_current_admin_user)
):
    # Get stats
    total_users = db.users.count_documents({})
    total_accommodations = db.accommodations.count_documents({})
    total_bookings = db.bookings.count_documents({})
    total_confirmed_bookings = db.bookings.count_documents({"booking_status": "confirmed"})
    total_pending_bookings = db.bookings.count_documents({"booking_status": "pending"})

    # Get recent bookings
    recent_bookings = list(db.bookings.find().sort("created_at", -1).limit(5))

    # Convert ObjectId to string in recent_bookings
    for booking in recent_bookings:
        booking["_id"] = str(booking["_id"])
        booking["user_id"] = str(booking["user_id"])
        booking["accommodation_id"] = str(booking["accommodation_id"])

    # Get top accommodations
    pipeline = [
        {"$group": {"_id": "$accommodation_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_accommodations_data = list(db.bookings.aggregate(pipeline))

    top_accommodations = []
    for item in top_accommodations_data:
        accommodation = db.accommodations.find_one({"_id": item["_id"]})
        if accommodation:
            top_accommodations.append({
                "id": str(accommodation["_id"]),
                "name": accommodation["name"],
                "bookings_count": item["count"]
            })

    return {
        "total_users": total_users,
        "total_accommodations": total_accommodations,
        "total_bookings": total_bookings,
        "total_confirmed_bookings": total_confirmed_bookings,
        "total_pending_bookings": total_pending_bookings,
        "recent_bookings": recent_bookings,
        "top_accommodations": top_accommodations
    }