from fastapi import APIRouter, HTTPException, Depends, UploadFile, Form, File
from models.property import Hotel, db, Apartment, UpdateHotel, UpdateApartment
from typing import Optional, List
from bson import ObjectId
from routes.auth import admin_required, oauth2_scheme, get_user_from_token
import logging
from utils.cloudinary_upload import UploadToCloudinary

logging.basicConfig(level=logging.DEBUG)

router = APIRouter()


# oauth2_scheme q   = OAuth2PasswordBearer(tokenUrl="auth/signin")

@router.post("/admin/hotels")
async def add_hotel(
        name: str = Form(...),
        description: str = Form(...),
        price_per_night: float = Form(...),
        location: str = Form(...),
        facilities: List[str] = Form(...),
        rooms: List[str] = Form(...),
        available_dates: List[str] = Form(...),
        images: List[UploadFile] = File(...),
        user: dict = Depends(admin_required),
):
    hotels_collection = db['hotels']

    image_urls = UploadToCloudinary(images)

    hotel_data = {
        "name": name,
        "description": description,
        "price_per_night": price_per_night,
        "location": location,
        "facilities": facilities,
        "rooms": rooms,
        "available_dates": available_dates,
        "images": image_urls,
    }

    # Insert into database
    result = hotels_collection.insert_one(hotel_data)
    return {"message": "Hotel added successfully", "hotel_id": str(result.inserted_id)}


@router.post("/admin/apartments")
async def add_apartment(
        name: str = Form(...),
        description: str = Form(...),
        price_per_month: float = Form(...),
        price_per_annum: Optional[float] = Form(None),
        location: str = Form(...),
        features: List[str] = Form(...),  # e.g., ["WiFi", "Furnished", "Parking"]
        facilities: List[str] = Form(...),
        available_dates: List[str] = Form(...),
        images: List[UploadFile] = File(...),
        user: dict = Depends(admin_required),
):
    apartments_collection = db['apartments']

    # Upload images to Cloudinary
    image_urls = UploadToCloudinary(images)

    # Prepare apartment data
    apartment_data = {
        "name": name,
        "description": description,
        "price_per_month": price_per_month,
        "price_per_annum": price_per_annum,
        "location": location,
        "features": features,
        "facilities": facilities,
        "available_dates": available_dates,
        "images": image_urls,
    }

    # Insert into database
    result = apartments_collection.insert_one(apartment_data)
    return {"message": "Apartment added successfully", "apartment_id": str(result.inserted_id)}


@router.patch("/admin/hotels/{hotel_id}")
async def update_hotel(
        hotel_id: str,
        update_data: UpdateHotel,
        user: dict = Depends(admin_required)
):
    hotels_collection = db['hotels']
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    result = hotels_collection.update_one({"_id": ObjectId(hotel_id)}, {"$set": update_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return {"message": "Hotel updated successfully"}


@router.patch("/admin/apartments/{apartment_id}")
async def update_apartment(
        apartment_id: str,
        update_data: UpdateApartment,
        user: dict = Depends(admin_required)
):
    apartments_collection = db['apartments']
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    result = apartments_collection.update_one({"_id": ObjectId(apartment_id)}, {"$set": update_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return {"message": "Apartment updated successfully"}


@router.delete("/admin/hotels/{hotel_id}")
async def delete_hotel(hotel_id: str, user: dict = Depends(admin_required)):
    hotels_collection = db['hotels']
    result = hotels_collection.delete_one({"_id": ObjectId(hotel_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return {"message": "Hotel deleted successfully"}


@router.delete("/admin/apartments/{apartment_id}")
async def delete_apartment(apartment_id: str, user: dict = Depends(admin_required)):
    apartments_collection = db['apartments']
    result = apartments_collection.delete_one({"_id": ObjectId(apartment_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return {"message": "Apartment deleted successfully"}


# User Routes
def get_accommodations(collection_name: str, location: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        collection: Collection = db[collection_name]
        filter_query = {"location": location} if location else {}
        accommodations = list(collection.find(filter_query))
        
        # Convert ObjectId to string for JSON serialization
        for accommodation in accommodations:
            accommodation["_id"] = str(accommodation["_id"])
            
        return accommodations
    except Exception as e:
        # Log the error (optional)
        print(f"Error fetching accommodations from {collection_name}: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while fetching accommodations.")

@router.get("/hotels")
async def get_hotels(location: Optional[str] = None):
    hotels = get_accommodations("hotels", location)
    return {"hotels": hotels}

@router.get("/apartments")
async def get_apartments(location: Optional[str] = None):
    apartments = get_accommodations("apartments", location)
    return {"apartments": apartments}


# @router.get("/hotels/{hotel_id}")
# async def get_hotel_by_id(hotel_id: str):
#     hotels_collection = db['hotels']
#
#
#     if not ObjectId.is_valid(hotel_id):
#         raise HTTPException(status_code=400, detail="Invalid hotel ID format")
#
#
#     hotel = hotels_collection.find_one({"_id": ObjectId(hotel_id)})
#     if not hotel:
#         raise HTTPException(status_code=404, detail="Hotel not found")
#
#     hotel["_id"] = str(hotel["_id"])
#     return hotel


@router.get("/hotels/{hotel_id}")
async def get_hotel_by_id(hotel_id: str):
    hotels_collection = db['hotels']
    hotel = hotels_collection.find_one({"_id": ObjectId(hotel_id)})
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    hotel["_id"] = str(hotel["_id"])
    return hotel


@router.get("/apartments/{apartment_id}")
async def get_apartment_by_id(apartment_id: str):
    apartments_collection = db['apartments']
    apartment = apartments_collection.find_one({"_id": ObjectId(apartment_id)})
    apartment["_id"] = str(apartment["_id"])
    if not apartment:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return apartment


@router.put("/hotels/{hotel_id}/nights")
async def update_hotel_nights(hotel_id: str, nights: int, token: str = Depends(oauth2_scheme)):
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if nights < 1:
        raise HTTPException(status_code=400, detail="Nights must be at least 1")
    hotels_collection = db['hotels']
    hotel = hotels_collection.find_one({"_id": ObjectId(hotel_id)})
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    hotels_collection.update_one({"_id": ObjectId(hotel_id)}, {"$set": {"nights": nights}})
    return {"message": "Number of nights updated successfully"}


@router.post("/hotels/{hotel_id}/reviews")
async def add_hotel_review(hotel_id: str, rating: int, comment: str, token: str = Depends(oauth2_scheme)):
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    hotels_collection = db['hotels']
    result = hotels_collection.update_one(
        {"_id": ObjectId(hotel_id)},
        {"$push": {"reviews": {"user_id": user['_id'], "rating": rating, "comment": comment}}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return {"message": "Review added successfully"}


@router.post("/apartments/{apartment_id}/reviews")
async def add_apartment_review(apartment_id: str, rating: int, comment: str, token: str = Depends(oauth2_scheme)):
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    apartments_collection = db['apartments']
    result = apartments_collection.update_one(
        {"_id": ObjectId(apartment_id)},
        {"$push": {"reviews": {"user_id": user['_id'], "rating": rating, "comment": comment}}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return {"message": "Review added successfully"}


@router.put("/hotels/{hotel_id}/reviews/{review_id}")
async def edit_hotel_review(hotel_id: str, review_id: str, rating: Optional[int] = None, comment: Optional[str] = None,
                            token: str = Depends(oauth2_scheme)):
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if rating and (rating < 1 or rating > 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    hotels_collection = db['hotels']
    result = hotels_collection.update_one(
        {"_id": ObjectId(hotel_id), "reviews.user_id": user['_id'], "reviews._id": ObjectId(review_id)},
        {"$set": {"reviews.$.rating": rating, "reviews.$.comment": comment}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review updated successfully"}


@router.delete("/hotels/{hotel_id}/reviews/{review_id}")
async def delete_hotel_review(hotel_id: str, review_id: str, token: str = Depends(oauth2_scheme)):
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    hotels_collection = db['hotels']
    result = hotels_collection.update_one(
        {"_id": ObjectId(hotel_id)},
        {"$pull": {"reviews": {"_id": ObjectId(review_id), "user_id": user['_id']}}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review deleted successfully"}


@router.post("/hotels/{hotel_id}/likes")
async def like_hotel(hotel_id: str, token: str = Depends(oauth2_scheme)):
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    hotels_collection = db['hotels']
    result = hotels_collection.update_one(
        {"_id": ObjectId(hotel_id)},
        {"$addToSet": {"likes": user['_id']}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return {"message": "Hotel liked successfully"}


@router.delete("/hotels/{hotel_id}/likes")
async def unlike_hotel(hotel_id: str, token: str = Depends(oauth2_scheme)):
    user = get_user_from_token(token)
    hotels_collection = db['hotels']
    result = hotels_collection.update_one(
        {"_id": hotel_id},
        {"$pull": {"likes": user["_id"]}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Hotel not found or not liked")
    return {"message": "Hotel unliked successfully"}


@router.post("/apartments/{apartment_id}/likes")
async def like_apartment(apartment_id: str, token: str = Depends(oauth2_scheme)):
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    hotels_collection = db['apartments']
    result = hotels_collection.update_one(
        {"_id": ObjectId(apartment_id)},
        {"$addToSet": {"likes": user['_id']}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return {"message": "Apartment liked successfully"}


@router.delete("/apartments/{apartment_id}/likes")
async def unlike_apartment(apartment_id: str, token: str = Depends(oauth2_scheme)):
    user = get_user_from_token(token)
    apartments_collection = db['apartments']
    result = apartments_collection.update_one(
        {"_id": apartment_id},
        {"$pull": {"likes": user["_id"]}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Apartment not found or not liked")
    return {"message": "Apartment unliked successfully"}


# @router.get("/hotels/liked")
# async def get_liked_hotels(user: dict = Depends(get_user_from_token)):
#     hotels_collection = db['hotels']
#
#     logging.debug(f"User object received: {user}")
#
#     try:
#         liked_hotels_cursor = hotels_collection.find({"likes": {"$in": [user["_id"]]}})
#         logging.debug(f"MongoDB query executed for user ID: {user['_id']}")
#     except Exception as e:
#         logging.error(f"Error querying hotels collection: {e}")
#         raise HTTPException(status_code=500, detail="Error querying hotels collection")
#
#     liked_hotels = []
#     for hotel in liked_hotels_cursor:
#         try:
#             hotel["_id"] = str(hotel["_id"])  # Convert ObjectId to string
#             liked_hotels.append(hotel)
#         except Exception as e:
#             logging.error(f"Error formatting hotel data: {e}")
#             raise HTTPException(status_code=500, detail="Error formatting hotel data")
#
#     logging.debug(f"Liked hotels response: {liked_hotels}")
#
#     return {"liked_hotels": liked_hotels}


@router.get("/hotels/liked/")
async def get_liked_hotels(user: dict = Depends(get_user_from_token)):
    hotels_collection = db['hotels']

    if not user or "_id" not in user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        liked_hotels_cursor = hotels_collection.find({"likes": {"$in": [user["_id"]]}})
        liked_hotels = [
            {**hotel, "_id": str(hotel["_id"])} for hotel in liked_hotels_cursor
        ]
        return {"liked_hotels": liked_hotels}
    except Exception as e:
        logging.error(f"Error querying hotels: {e}")
        raise HTTPException(status_code=500, detail="Error fetching liked hotels")


@router.get("/apartments/liked/")
async def get_liked_apartments(token: str = Depends(oauth2_scheme)):
    hotels_collection = db['apartments']

    if not token:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        liked_hotels_cursor = hotels_collection.find({"likes": {"$in": [token]}})
        liked_hotels = [
            {**hotel, "_id": str(hotel["_id"])} for hotel in liked_hotels_cursor
        ]
        return {"liked_hotels": liked_hotels}
    except Exception as e:
        logging.error(f"Error querying hotels: {e}")
        raise HTTPException(status_code=500, detail="Error fetching liked hotels")


@router.put("/hotels/{hotel_id}/reviews")
async def edit_hotel_review(hotel_id: str, review: str, rating: int, token: str = Depends(oauth2_scheme)):
    user = get_user_from_token(token)
    hotels_collection = db['hotels']
    if not (1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    result = hotels_collection.update_one(
        {"_id": hotel_id, "reviews.user_id": user["_id"]},
        {"$set": {"reviews.$.review": review, "reviews.$.rating": rating}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Review not found for this hotel")
    return {"message": "Hotel review updated successfully"}


@router.put("/apartments/{apartment_id}/reviews")
async def edit_apartment_review(apartment_id: str, review: str, rating: int, token: str = Depends(oauth2_scheme)):
    user = get_user_from_token(token)
    apartments_collection = db['apartments']
    if not (1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    result = apartments_collection.update_one(
        {"_id": apartment_id, "reviews.user_id": user["_id"]},
        {"$set": {"reviews.$.review": review, "reviews.$.rating": rating}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Review not found for this apartment")
    return {"message": "Apartment review updated successfully"}
