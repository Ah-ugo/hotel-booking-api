from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File, Form, Query
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from config.db import db
from models.newUser import UserInDB, UserUpdate, UserResponse
from models.newBooking import BookingResponse, BookingWithDetails
from models.accommodations import AccommodationResponse
from utils.auth import get_current_active_user
from utils.cloudinary_util import upload_image

router = APIRouter()


@router.put("/profile", response_model=UserResponse)
def update_profile(
        user_update: UserUpdate = Body(...),
        current_user: UserInDB = Depends(get_current_active_user)
):
    # Filter out None values
    update_data = {k: v for k, v in user_update.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )

    # Update timestamp
    update_data["updated_at"] = datetime.utcnow()

    # Update user in database
    update_result = db.users.update_one(
        {"_id": ObjectId(current_user.id)}, #convert id to objectId
        {"$set": update_data}
    )

    if update_result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Get updated user
    updated_user = db.users.find_one({"_id": ObjectId(current_user.id)}) #convert id to objectId

    if updated_user:
        updated_user["_id"] = str(updated_user["_id"]) #convert ObjectId to string
        return UserResponse(**updated_user)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated user")


@router.post("/profile/image", response_model=UserResponse)
def upload_profile_image(
        file: UploadFile = File(...),
        current_user: UserInDB = Depends(get_current_active_user)
):
    # Upload image to Cloudinary
    image_url = upload_image(file, folder="profile_images")

    # Update user in database
    update_result = db.users.update_one(
        {"_id": ObjectId(current_user.id)}, #convert id to objectId
        {
            "$set": {
                "profile_image_url": image_url,
                "updated_at": datetime.utcnow()
            }
        }
    )

    if update_result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Get updated user
    updated_user = db.users.find_one({"_id": ObjectId(current_user.id)}) #convert id to objectId

    if updated_user:
        updated_user["_id"] = str(updated_user["_id"]) #convert objectId to string
        return UserResponse(**updated_user)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated user")



@router.post("/location", response_model=UserResponse)
def update_user_location(
        latitude: float = Form(...),
        longitude: float = Form(...),
        address: Optional[str] = Form(None),
        current_user: UserInDB = Depends(get_current_active_user)
):
    # Create location object
    location = {
        "type": "Point",
        "coordinates": [longitude, latitude],
        "address": address
    }

    # Update user in database
    update_result = db.users.update_one(
        {"_id": ObjectId(current_user.id)}, #convert id to objectId
        {
            "$set": {
                "location": location,
                "updated_at": datetime.utcnow()
            }
        }
    )

    if update_result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Get updated user
    updated_user = db.users.find_one({"_id": ObjectId(current_user.id)}) #convert id to objectId

    if updated_user:
        updated_user["_id"] = str(updated_user["_id"]) #convert ObjectId to string
        return UserResponse(**updated_user)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated user")


@router.get("/bookings", response_model=List[BookingResponse])
def get_user_bookings(
        status: Optional[str] = Query(None),
        current_user: UserInDB = Depends(get_current_active_user)
):
    # Build query
    query = {"user_id": current_user.id}

    if status:
        query["booking_status"] = status

    # Get bookings
    bookings = list(db.bookings.find(query).sort("created_at", -1))

    return [BookingResponse(**booking) for booking in bookings]


@router.get("/bookings/{booking_id}", response_model=BookingWithDetails)
def get_booking_details(
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
    accommodation = db.accommodations.find_one({"_id": booking["accommodation_id"]})

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Get user details
    user = db.users.find_one({"_id": booking["user_id"]})

    # Create response
    booking_with_details = BookingWithDetails(
        **booking,
        accommodation_details=accommodation,
        user_details=user
    )

    return booking_with_details


@router.get("/favorites", response_model=List[AccommodationResponse])
def get_user_favorites(
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Get user favorites
    user = db.users.find_one({"_id": ObjectId(current_user.id)}) #convert to objectId

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    favorite_ids = user.get("favorites", [])

    if not favorite_ids:
        return []

    # Convert to ObjectId
    favorite_object_ids = [ObjectId(id) for id in favorite_ids]

    # Get accommodations
    accommodations = list(db.accommodations.find({"_id": {"$in": favorite_object_ids}}))

    # Convert ObjectId to string and create AccommodationResponse objects
    response_accommodations = []
    for accommodation in accommodations:
        accommodation["_id"] = str(accommodation["_id"]) #convert ObjectId to string
        response_accommodations.append(AccommodationResponse(**accommodation))

    return response_accommodations

@router.post("/favorites/{accommodation_id}", response_model=UserResponse)
def add_to_favorites(
    accommodation_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
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

    # Add to favorites
    db.users.update_one(
        {"_id": ObjectId(current_user.id)}, #convert user id to objectId
        {
            "$addToSet": {"favorites": accommodation_id},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    # Get updated user
    updated_user = db.users.find_one({"_id": ObjectId(current_user.id)}) #convert user id to objectId

    if updated_user:
        updated_user["_id"] = str(updated_user["_id"]) #convert ObjectId to string
        return UserResponse(**updated_user)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated user")

@router.delete("/favorites/{accommodation_id}", response_model=UserResponse)
def remove_from_favorites(
    accommodation_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Remove from favorites
    update_result = db.users.update_one(
        {"_id": ObjectId(current_user.id)}, #convert user id to objectId
        {
            "$pull": {"favorites": accommodation_id},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    if update_result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Get updated user
    updated_user = db.users.find_one({"_id": ObjectId(current_user.id)}) #convert user id to objectId

    if updated_user:
        updated_user["_id"] = str(updated_user["_id"]) #convert ObjectId to string
        return UserResponse(**updated_user)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated user")
