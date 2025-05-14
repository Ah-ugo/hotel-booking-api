from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timedelta
import math

from config.db import db
from models.newUser import UserInDB
from models.accommodations import (
    AccommodationResponse, AccommodationType,
    AccommodationSearchParams, Room
)
from models.review import ReviewCreate, ReviewResponse, ReviewUpdate
from utils.auth import get_current_active_user, get_current_user
from utils.location import calculate_distance

import logging

logging.basicConfig(level=logging.INFO)

router = APIRouter()


@router.get("/", response_model=Dict[str, Any])
def get_accommodations(
    accommodation_type: Optional[AccommodationType] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_rating: Optional[float] = Query(None),
    amenities: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("rating", regex="^(rating|price|created_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: Optional[UserInDB] = Depends(lambda: None)  # Optional user dependency
):
    """
    Get a paginated list of accommodations with various filtering options.
    """
    # Build query
    query = {} #removed "is_active": True

    if accommodation_type:
        query["accommodation_type"] = accommodation_type

    if city:
        query["city"] = {"$regex": city, "$options": "i"}

    if state:
        query["state"] = {"$regex": state, "$options": "i"}

    if country:
        query["country"] = {"$regex": country, "$options": "i"}

    if min_rating is not None:
        query["average_rating"] = {"$gte": min_rating}

    # Price filtering requires a more complex query since price is in rooms
    price_query = []
    if min_price is not None or max_price is not None:
        if min_price is not None:
            price_query.append({"rooms.price_per_night": {"$gte": min_price}})
        if max_price is not None:
            price_query.append({"rooms.price_per_night": {"$lte": max_price}})

    # Amenities filtering
    if amenities:
        query["amenities.name"] = {"$all": amenities}

    # Combine price query with main query if needed
    if price_query:
        query["$and"] = price_query

    # Determine sort direction
    sort_direction = -1 if sort_order == "desc" else 1

    # Map sort_by to the actual field
    sort_field_map = {
        "rating": "average_rating",
        "price": "rooms.price_per_night",  # This is approximate since price is in rooms
        "created_at": "created_at"
    }
    sort_field = sort_field_map.get(sort_by, "average_rating")

    # Count total documents for pagination
    total_count = db.accommodations.count_documents(query)
    total_pages = math.ceil(total_count / limit)

    # Get accommodations
    skip = (page - 1) * limit
    accommodations = list(
        db.accommodations.find(query)
        .sort(sort_field, sort_direction)
        .skip(skip)
        .limit(limit)
    )

    # Process accommodations before creating AccommodationResponse objects
    processed_accommodations = []
    for accommodation in accommodations:
        accommodation["_id"] = str(accommodation["_id"])  # Convert _id to string
        if "created_at" not in accommodation:
            accommodation["created_at"] = datetime.utcnow() #Add created_at if missing
        processed_accommodations.append(accommodation)

    # Add favorite flag if user is logged in
    if current_user:
        user = db.users.find_one({"_id": current_user.id})
        if user: # Check if user exists before accessing it
            favorites = user.get("favorites", [])

            for accommodation in processed_accommodations:
                accommodation["is_favorite"] = str(accommodation["_id"]) in favorites
        else:
            # If user does not exist, do not set is_favorite.
            pass

    # Format response
    results = [AccommodationResponse(**accommodation) for accommodation in processed_accommodations]

    return {
        "results": results,
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "total_pages": total_pages
    }

@router.get("/hotels", response_model=Dict[str, Any])
def get_hotels(
        city: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        country: Optional[str] = Query(None),
        min_price: Optional[float] = Query(None),
        max_price: Optional[float] = Query(None),
        min_rating: Optional[float] = Query(None),
        amenities: Optional[List[str]] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
        sort_by: str = Query("rating", regex="^(rating|price|created_at)$"),
        sort_order: str = Query("desc", regex="^(asc|desc)$"),
        # current_user: Optional[UserInDB] = Depends(get_current_user)
):
    """
    Get a paginated list of hotels with various filtering options.
    """
    return get_accommodations(
        accommodation_type=AccommodationType.HOTEL,
        city=city,
        state=state,
        country=country,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        amenities=amenities,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        # current_user=current_user
    )


@router.get("/apartments", response_model=Dict[str, Any])
def get_apartments(
        city: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        country: Optional[str] = Query(None),
        min_price: Optional[float] = Query(None),
        max_price: Optional[float] = Query(None),
        min_rating: Optional[float] = Query(None),
        amenities: Optional[List[str]] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
        sort_by: str = Query("rating", regex="^(rating|price|created_at)$"),
        sort_order: str = Query("desc", regex="^(asc|desc)$"),
        # current_user: Optional[UserInDB] = Depends(get_current_user)
):
    """
    Get a paginated list of apartments with various filtering options.
    """
    return get_accommodations(
        accommodation_type=AccommodationType.APARTMENT,
        city=city,
        state=state,
        country=country,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        amenities=amenities,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        # current_user=current_user
    )


@router.get("/hostels", response_model=Dict[str, Any])
def get_hostels(
        city: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        country: Optional[str] = Query(None),
        min_price: Optional[float] = Query(None),
        max_price: Optional[float] = Query(None),
        min_rating: Optional[float] = Query(None),
        amenities: Optional[List[str]] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
        sort_by: str = Query("rating", regex="^(rating|price|created_at)$"),
        sort_order: str = Query("desc", regex="^(asc|desc)$"),
        # current_user: Optional[UserInDB] = Depends(get_current_user)
):
    """
    Get a paginated list of hostels with various filtering options.
    """
    return get_accommodations(
        accommodation_type=AccommodationType.HOSTEL,
        city=city,
        state=state,
        country=country,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        amenities=amenities,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        # current_user=current_user
    )


@router.get("/lodges", response_model=Dict[str, Any])
def get_lodges(
        city: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        country: Optional[str] = Query(None),
        min_price: Optional[float] = Query(None),
        max_price: Optional[float] = Query(None),
        min_rating: Optional[float] = Query(None),
        amenities: Optional[List[str]] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
        sort_by: str = Query("rating", regex="^(rating|price|created_at)$"),
        sort_order: str = Query("desc", regex="^(asc|desc)$"),
        # current_user: Optional[UserInDB] = Depends(get_current_user)
):
    """
    Get a paginated list of lodges with various filtering options.
    """
    return get_accommodations(
        accommodation_type=AccommodationType.LODGE,
        city=city,
        state=state,
        country=country,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        amenities=amenities,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        # current_user=current_user
    )


@router.get("/near-me", response_model=Dict[str, Any])
def get_accommodations_near_me(
    latitude: float = Query(...),
    longitude: float = Query(...),
    distance: int = Query(10000, description="Distance in meters"),
    accommodation_type: Optional[AccommodationType] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_rating: Optional[float] = Query(None),
    amenities: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: Optional[UserInDB] = Depends(get_current_user)
):
    """
    Get accommodations near a specific location within a given distance.
    """
    # Build geospatial query using $geoWithin instead of $near
    query = {
        "location": {
            "$geoWithin": {
                "$centerSphere": [
                    [longitude, latitude],
                    distance / 6378100  # Convert meters to radians (Earth radius in meters)
                ]
            }
        }
    }

    # Add filters
    if accommodation_type:
        query["accommodation_type"] = accommodation_type

    if min_rating is not None:
        query["average_rating"] = {"$gte": min_rating}

    # Price filtering
    price_query = []
    if min_price is not None or max_price is not None:
        if min_price is not None:
            price_query.append({"rooms.price_per_night": {"$gte": min_price}})
        if max_price is not None:
            price_query.append({"rooms.price_per_night": {"$lte": max_price}})

    # Amenities filtering
    if amenities:
        query["amenities.name"] = {"$all": amenities}

    # Combine price query with main query if needed
    if price_query:
        query["$and"] = price_query

    # Count total documents for pagination
    total_count = db.accommodations.count_documents(query)
    total_pages = math.ceil(total_count / limit)

    # Get accommodations
    skip = (page - 1) * limit
    accommodations = list(
        db.accommodations.find(query)
        .skip(skip)
        .limit(limit)
    )

    # Add distance to each accommodation
    for accommodation in accommodations:
        if "location" in accommodation and "coordinates" in accommodation["location"]:
            accommodation_coords = accommodation["location"]["coordinates"]
            accommodation["distance"] = calculate_distance(
                latitude, longitude,
                accommodation_coords[1], accommodation_coords[0]
            )
        else:
            accommodation["distance"] = float("inf")

    # Sort by distance
    accommodations.sort(key=lambda x: x.get("distance", float("inf")))

    # Add favorite flag if user is logged in
    if current_user:
        user = db.users.find_one({"_id": current_user.id})
        if user:
            favorites = user.get("favorites", [])

            for accommodation in accommodations:
                accommodation["is_favorite"] = str(accommodation["_id"]) in favorites
        else:
            pass

    # Format response
    results = []
    for accommodation in accommodations:
        accommodation["_id"] = str(accommodation["_id"]) #convert ObjectId to string
        if "created_at" not in accommodation:
          accommodation["created_at"] = datetime.utcnow() #or some default datetime value.
        results.append(AccommodationResponse(**accommodation))

    return {
        "results": results,
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "total_pages": total_pages
    }

@router.get("/in-area", response_model=Dict[str, Any])
def get_accommodations_in_area(
    min_lat: float = Query(..., description="Minimum latitude (bottom)"),
    min_lng: float = Query(..., description="Minimum longitude (left)"),
    max_lat: float = Query(..., description="Maximum latitude (top)"),
    max_lng: float = Query(..., description="Maximum longitude (right)"),
    accommodation_type: Optional[AccommodationType] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_rating: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: Optional[UserInDB] = Depends(get_current_user)
):
    """
    Get accommodations within a specific area defined by a bounding box.
    """
    # Build geospatial query using $geoWithin and $box
    query = {
        "location.coordinates": {
            "$geoWithin": {
                "$box": [
                    [min_lng, min_lat],  # Bottom left
                    [max_lng, max_lat]  # Top right
                ]
            }
        }
    }

    # Add filters
    if accommodation_type:
        query["accommodation_type"] = accommodation_type

    if min_rating is not None:
        query["average_rating"] = {"$gte": min_rating}

    # Price filtering
    price_query = []
    if min_price is not None or max_price is not None:
        if min_price is not None:
            price_query.append({"rooms.price_per_night": {"$gte": min_price}})
        if max_price is not None:
            price_query.append({"rooms.price_per_night": {"$lte": max_price}})

    # Combine price query with main query if needed
    if price_query:
        query["$and"] = price_query

    # Count total documents for pagination
    total_count = db.accommodations.count_documents(query)
    total_pages = math.ceil(total_count / limit)

    # Get accommodations
    skip = (page - 1) * limit
    accommodations = list(
        db.accommodations.find(query)
        .skip(skip)
        .limit(limit)
    )

    # Calculate center point of the bounding box
    center_lat = (min_lat + max_lat) / 2
    center_lng = (min_lng + max_lng) / 2

    # Add distance from center to each accommodation
    for accommodation in accommodations:
        if "location" in accommodation and "coordinates" in accommodation["location"]:
            accommodation_coords = accommodation["location"]["coordinates"]
            accommodation["distance"] = calculate_distance(
                center_lat, center_lng,
                accommodation_coords[1], accommodation_coords[0]
            )
        else:
            accommodation["distance"] = float("inf")

    # Sort by distance
    accommodations.sort(key=lambda x: x.get("distance", float("inf")))

    # Add favorite flag if user is logged in
    if current_user:
        user = db.users.find_one({"_id": current_user.id})
        if user:
            favorites = user.get("favorites", [])

            for accommodation in accommodations:
                accommodation["is_favorite"] = str(accommodation["_id"]) in favorites
        else:
            pass

    # Format response
    results = []
    for accommodation in accommodations:
        accommodation["_id"] = str(accommodation["_id"]) #convert ObjectId to string
        if "created_at" not in accommodation:
          accommodation["created_at"] = datetime.utcnow() #or some default datetime value.
        results.append(AccommodationResponse(**accommodation))

    return {
        "results": results,
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "total_pages": total_pages
    }

@router.get("/search", response_model=Dict[str, Any])
def search_accommodations(
        query: str = Query(..., min_length=1),
        accommodation_type: Optional[AccommodationType] = Query(None),
        city: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        country: Optional[str] = Query(None),
        min_price: Optional[float] = Query(None),
        max_price: Optional[float] = Query(None),
        min_rating: Optional[float] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
        current_user: Optional[UserInDB] = Depends(get_current_user)
):
    """
    Search for accommodations by name, description, or address.
    """
    # Build text search query
    search_query = {
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}},
            {"address": {"$regex": query, "$options": "i"}},
            {"city": {"$regex": query, "$options": "i"}},
            {"state": {"$regex": query, "$options": "i"}},
            {"country": {"$regex": query, "$options": "i"}}
        ]
    }

    # Add filters
    if accommodation_type:
        search_query["accommodation_type"] = accommodation_type

    if city:
        search_query["city"] = {"$regex": city, "$options": "i"}

    if state:
        search_query["state"] = {"$regex": state, "$options": "i"}

    if country:
        search_query["country"] = {"$regex": country, "$options": "i"}

    if min_rating is not None:
        search_query["average_rating"] = {"$gte": min_rating}

    # Price filtering
    price_query = []
    if min_price is not None or max_price is not None:
        if min_price is not None:
            price_query.append({"rooms.price_per_night": {"$gte": min_price}})
        if max_price is not None:
            price_query.append({"rooms.price_per_night": {"$lte": max_price}})

    # Combine price query with main query if needed
    if price_query:
        search_query["$and"] = price_query

    # Count total documents for pagination
    total_count = db.accommodations.count_documents(search_query)
    total_pages = math.ceil(total_count / limit)

    # Get accommodations
    skip = (page - 1) * limit
    accommodations = list(
        db.accommodations.find(search_query)
        .sort("average_rating", -1)
        .skip(skip)
        .limit(limit)
    )

    # Add favorite flag if user is logged in
    if current_user:
        user = db.users.find_one({"_id": current_user.id})
        if user:
            favorites = user.get("favorites", [])

            for accommodation in accommodations:
                accommodation["is_favorite"] = str(accommodation["_id"]) in favorites
        else:
            pass

    # Format response
    results = [AccommodationResponse(**{**accommodation, "_id": str(accommodation["_id"])}) for accommodation in accommodations] #convert object id to string

    return {
        "results": results,
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "total_pages": total_pages
    }

def add_created_at_if_missing(accommodations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Helper function to add created_at if missing."""
    for accommodation in accommodations:
        if "created_at" not in accommodation:
            accommodation["created_at"] = datetime.utcnow()
    return accommodations

@router.get("/popular", response_model=List[AccommodationResponse])
def get_popular_accommodations(
        limit: int = Query(10, ge=1, le=50),
        current_user: Optional[UserInDB] = Depends(get_current_user)
):
    """
    Get the most popular accommodations based on bookings and ratings.
    """
    accommodations = list(
        db.accommodations.find()
        .sort([("total_bookings", -1), ("average_rating", -1)])
        .limit(limit)
    )

    accommodations = add_created_at_if_missing(accommodations) #add created_at

    if current_user:
        user = db.users.find_one({"_id": current_user.id})
        if user:
            favorites = user.get("favorites", [])
            for accommodation in accommodations:
                accommodation["is_favorite"] = str(accommodation["_id"]) in favorites
        else:
            pass

    results = [AccommodationResponse(**{**accommodation, "_id": str(accommodation["_id"])}) for accommodation in accommodations]
    return results

@router.get("/trending", response_model=List[AccommodationResponse])
def get_trending_accommodations(
        days: int = Query(30, ge=1, le=90),
        limit: int = Query(10, ge=1, le=50),
        current_user: Optional[UserInDB] = Depends(get_current_user)
):
    """
    Get trending accommodations based on recent bookings.
    """
    threshold_date = datetime.utcnow() - timedelta(days=days)
    recent_bookings = list(
        db.bookings.find({"created_at": {"$gte": threshold_date}})
        .sort("created_at", -1)
    )

    booking_counts = {}
    for booking in recent_bookings:
        acc_id = booking["accommodation_id"]
        booking_counts[acc_id] = booking_counts.get(acc_id, 0) + 1

    sorted_acc_ids = sorted(booking_counts.keys(), key=lambda x: booking_counts[x], reverse=True)[:limit]

    accommodations = []
    for acc_id in sorted_acc_ids:
        accommodation = db.accommodations.find_one({"_id": acc_id})
        if accommodation:
            accommodation["recent_bookings"] = booking_counts[acc_id]
            accommodations.append(accommodation)

    accommodations = add_created_at_if_missing(accommodations) #add created_at

    if current_user:
        user = db.users.find_one({"_id": current_user.id})
        if user:
            favorites = user.get("favorites", [])
            for accommodation in accommodations:
                accommodation["is_favorite"] = str(accommodation["_id"]) in favorites
        else:
            pass

    results = [AccommodationResponse(**{**accommodation, "_id": str(accommodation["_id"])}) for accommodation in accommodations]
    return results

@router.get("/recommended", response_model=List[AccommodationResponse])
def get_recommended_accommodations(
        limit: int = Query(10, ge=1, le=50),
        current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Get personalized accommodation recommendations for the current user.
    """
    user_bookings = list(db.bookings.find({"user_id": current_user.id}))
    if not user_bookings:
        return get_popular_accommodations(limit=limit, current_user=current_user)

    booked_acc_ids = [booking["accommodation_id"] for booking in user_bookings]
    booked_accommodations = list(db.accommodations.find({"_id": {"$in": booked_acc_ids}}))

    preferred_types = set()
    preferred_cities = set()
    preferred_amenities = set()

    for acc in booked_accommodations:
        preferred_types.add(acc.get("accommodation_type"))
        preferred_cities.add(acc.get("city"))
        for amenity in acc.get("amenities", []):
            preferred_amenities.add(amenity.get("name"))

    query = {
        # "is_active": True,
        "_id": {"$nin": booked_acc_ids}
    }

    if preferred_types:
        query["accommodation_type"] = {"$in": list(preferred_types)}
    if preferred_cities:
        query["city"] = {"$in": list(preferred_cities)}

    recommendations = list(
        db.accommodations.find(query)
        .sort("average_rating", -1)
        .limit(limit)
    )

    recommendations = add_created_at_if_missing(recommendations) #add created_at

    user = db.users.find_one({"_id": current_user.id})
    if user:
      favorites = user.get("favorites", [])
      for accommodation in recommendations:
          accommodation["is_favorite"] = str(accommodation["_id"]) in favorites

    results = [AccommodationResponse(**{**accommodation, "_id": str(accommodation["_id"])}) for accommodation in recommendations]
    return results



@router.get("/by-amenities", response_model=Dict[str, Any])
def get_accommodations_by_amenities(
        amenities: List[str] = Query(...),
        accommodation_type: Optional[AccommodationType] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
        current_user: Optional[UserInDB] = Depends(get_current_user)
):
    """
    Get accommodations that have specific amenities.
    """
    # Build query
    query = {
        # "is_active": True,
        "amenities.name": {"$all": amenities}
    }

    if accommodation_type:
        query["accommodation_type"] = accommodation_type

    # Count total documents for pagination
    total_count = db.accommodations.count_documents(query)
    total_pages = math.ceil(total_count / limit)

    # Get accommodations
    skip = (page - 1) * limit
    accommodations = list(
        db.accommodations.find(query)
        .sort("average_rating", -1)
        .skip(skip)
        .limit(limit)
    )

    # Add created_at if missing
    for accommodation in accommodations:
        if "created_at" not in accommodation:
            accommodation["created_at"] = datetime.utcnow()

    # Add favorite flag if user is logged in
    if current_user:
        user = db.users.find_one({"_id": current_user.id})
        if user:
            favorites = user.get("favorites", [])
            for accommodation in accommodations:
                accommodation["is_favorite"] = str(accommodation["_id"]) in favorites
        else:
            pass

    # Format response
    results = [AccommodationResponse(**{**accommodation, "_id": str(accommodation["_id"])}) for accommodation in accommodations]

    return {
        "results": results,
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "total_pages": total_pages
    }

@router.get("/{accommodation_id}", response_model=AccommodationResponse)
def get_accommodation_details(
        accommodation_id: str = Path(...),
        current_user: Optional[UserInDB] = Depends(get_current_user)
):
    """
    Get detailed information about a specific accommodation.
    """
    # Check if accommodation exists
    if not ObjectId.is_valid(accommodation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    accommodation = db.accommodations.find_one({
        "_id": ObjectId(accommodation_id),
        # "is_active": True
    })

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Add created_at if missing
    if "created_at" not in accommodation:
        accommodation["created_at"] = datetime.utcnow()

    # Add favorite flag if user is logged in
    if current_user:
        user = db.users.find_one({"_id": current_user.id})
        if user:
            favorites = user.get("favorites", [])
            accommodation["is_favorite"] = accommodation_id in favorites
        else:
            pass

    return AccommodationResponse(**{**accommodation, "_id": str(accommodation["_id"])})


@router.get("/{accommodation_id}/reviews", response_model=Dict[str, Any])
def get_accommodation_reviews(
        accommodation_id: str = Path(...),
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
        sort_by: str = Query("created_at", regex="^(created_at|rating)$"),
        sort_order: str = Query("desc", regex="^(asc|desc)$")
):
    """
    Get reviews for a specific accommodation.
    """
    # Check if accommodation exists
    if not ObjectId.is_valid(accommodation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    accommodation = db.accommodations.find_one({
        "_id": ObjectId(accommodation_id),
        # "is_active": True
    })

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Build query
    query = {"accommodation_id": ObjectId(accommodation_id)}

    # Count total documents for pagination
    total_count = db.reviews.count_documents(query)
    total_pages = math.ceil(total_count / limit)

    # Determine sort direction
    sort_direction = -1 if sort_order == "desc" else 1

    # Get reviews
    skip = (page - 1) * limit
    reviews = list(
        db.reviews.find(query)
        .sort(sort_by, sort_direction)
        .skip(skip)
        .limit(limit)
    )

    # Get user details for each review
    for review in reviews:
        user = db.users.find_one({"_id": review["user_id"]})
        if user:
            review["user"] = {
                "id": str(user["_id"]),
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "profile_image_url": user.get("profile_image_url")
            }

    # Format response
    results = [ReviewResponse(**review) for review in reviews]

    return {
        "results": results,
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "total_pages": total_pages,
        "average_rating": accommodation.get("average_rating", 0),
        "reviews_count": accommodation.get("reviews_count", 0)
    }


@router.post("/{accommodation_id}/reviews", response_model=ReviewResponse)
def create_review(
        accommodation_id: str = Path(...),
        review_data: ReviewCreate = Body(...),
        current_user: UserInDB = Depends(get_current_active_user)
):
    logging.info(f"Current User ID: {current_user.id}")
    logging.info(f"Accommodation ID: {accommodation_id}")

    if not ObjectId.is_valid(accommodation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    accommodation = db.accommodations.find_one({
        "_id": ObjectId(accommodation_id),
    })

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Modify the booking query to use strings
    booking = db.bookings.find_one({
        "user_id": str(current_user.id),  # Convert current_user.id to string
        "accommodation_id": accommodation_id,  # Use accommodation_id as string
        "booking_status": {"$in": ["confirmed", "completed", "pending"]}
    })

    if not booking:
        logging.info("Booking not found")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only review accommodations you have booked"
        )
    else:
        logging.info("Booking found")

    existing_review = db.reviews.find_one({
        "user_id": str(current_user.id),
        "accommodation_id": accommodation_id
    })

    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this accommodation"
        )

    review_dict = review_data.dict()
    review_dict["user_id"] = str(current_user.id)
    review_dict["accommodation_id"] = accommodation_id
    review_dict["created_at"] = datetime.utcnow()

    result = db.reviews.insert_one(review_dict)

    all_reviews = list(db.reviews.find({"accommodation_id": accommodation_id}))
    total_rating = sum(review.get("rating", 0) for review in all_reviews)
    average_rating = total_rating / len(all_reviews) if all_reviews else 0

    db.accommodations.update_one(
        {"_id": ObjectId(accommodation_id)},
        {
            "$set": {
                "average_rating": average_rating,
                "reviews_count": len(all_reviews)
            }
        }
    )

    created_review = db.reviews.find_one({"_id": result.inserted_id})
    created_review["user"] = {
        "id": str(current_user.id),
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "profile_image_url": current_user.profile_image_url
    }

    # Convert ObjectId to string
    created_review["_id"] = str(created_review["_id"])
    created_review["accommodation_id"] = str(created_review["accommodation_id"])

    return ReviewResponse(**created_review)


@router.put("/{accommodation_id}/reviews/{review_id}", response_model=ReviewResponse)
def update_review(
        accommodation_id: str = Path(...),
        review_id: str = Path(...),
        review_update: ReviewUpdate = Body(...),
        current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Update a review for a specific accommodation.
    """
    # Check if accommodation exists
    if not ObjectId.is_valid(accommodation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    # Check if review exists
    if not ObjectId.is_valid(review_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review ID"
        )

    # Modify the review query to use strings
    review = db.reviews.find_one({
        "_id": ObjectId(review_id),
        "accommodation_id": accommodation_id, #uses string
        "user_id": str(current_user.id) #uses string
    })

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or you don't have permission to update it"
        )

    # Update review
    update_data = {k: v for k, v in review_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()

    db.reviews.update_one(
        {"_id": ObjectId(review_id)},
        {"$set": update_data}
    )

    # Update accommodation rating
    all_reviews = list(db.reviews.find({"accommodation_id": accommodation_id})) #Uses String.

    # Calculate average rating
    total_rating = sum(review.get("rating", 0) for review in all_reviews)
    average_rating = total_rating / len(all_reviews) if all_reviews else 0

    # Update accommodation
    db.accommodations.update_one(
        {"_id": ObjectId(accommodation_id)},
        {
            "$set": {
                "average_rating": average_rating
            }
        }
    )

    # Get updated review
    updated_review = db.reviews.find_one({"_id": ObjectId(review_id)})

    # Add user details
    updated_review["user"] = {
        "id": str(current_user.id),
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "profile_image_url": current_user.profile_image_url
    }

    updated_review["_id"] = str(updated_review["_id"])
    updated_review["accommodation_id"] = str(updated_review["accommodation_id"])

    return ReviewResponse(**updated_review)


@router.delete("/{accommodation_id}/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
        accommodation_id: str = Path(...),
        review_id: str = Path(...),
        current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Delete a review for a specific accommodation.
    """
    # Check if accommodation exists
    if not ObjectId.is_valid(accommodation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accommodation ID"
        )

    # Check if review exists
    if not ObjectId.is_valid(review_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review ID"
        )

    # Modify the review query to use strings
    review = db.reviews.find_one({
        "_id": ObjectId(review_id),
        "accommodation_id": accommodation_id, #Uses string
        "user_id": str(current_user.id) #Uses String
    })

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or you don't have permission to delete it"
        )

    # Delete review
    db.reviews.delete_one({"_id": ObjectId(review_id)})

    # Update accommodation rating
    all_reviews = list(db.reviews.find({"accommodation_id": accommodation_id})) #Uses String

    # Calculate average rating
    total_rating = sum(review.get("rating", 0) for review in all_reviews)
    average_rating = total_rating / len(all_reviews) if all_reviews else 0

    # Update accommodation
    db.accommodations.update_one(
        {"_id": ObjectId(accommodation_id)},
        {
            "$set": {
                "average_rating": average_rating,
                "reviews_count": len(all_reviews)
            }
        }
    )

    return None


@router.get("/amenities/list", response_model=List[str])
def get_available_amenities():
    """
    Get a list of all available amenities across all accommodations.
    """
    # Aggregate all unique amenity names
    pipeline = [
        {"$unwind": "$amenities"},
        {"$group": {"_id": "$amenities.name"}},
        {"$sort": {"_id": 1}}
    ]

    amenities = list(db.accommodations.aggregate(pipeline))
    return [amenity["_id"] for amenity in amenities]


@router.get("/cities/list", response_model=List[str])
def get_available_cities(
        country: Optional[str] = Query(None)
):
    """
    Get a list of all available cities, optionally filtered by country.
    """
    # Build query
    match_stage = {}
    if country:
        match_stage["country"] = {"$regex": country, "$options": "i"}

    # Aggregate all unique cities
    pipeline = [
        {"$match": match_stage} if match_stage else {"$match": {}},
        {"$group": {"_id": "$city"}},
        {"$sort": {"_id": 1}}
    ]

    cities = list(db.accommodations.aggregate(pipeline))
    return [city["_id"] for city in cities if city["_id"]]


@router.get("/countries/list", response_model=List[str])
def get_available_countries():
    """
    Get a list of all available countries.
    """
    # Aggregate all unique countries
    pipeline = [
        {"$group": {"_id": "$country"}},
        {"$sort": {"_id": 1}}
    ]

    countries = list(db.accommodations.aggregate(pipeline))
    return [country["_id"] for country in countries if country["_id"]]


@router.get("/price-range", response_model=Dict[str, float])
def get_price_range(
        accommodation_type: Optional[AccommodationType] = Query(None), current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Get the minimum and maximum price across all accommodations.
    """
    logging.info(f"Finding price range for accommodation type: {accommodation_type}")

    # Build query
    match_stage = {}
    if accommodation_type:
        match_stage["accommodation_type"] = accommodation_type

    # Aggregate min and max prices
    pipeline = [
        {"$match": match_stage} if match_stage else {"$match": {}},
        {"$unwind": "$rooms"},
        {"$group": {
            "_id": None,
            "min_price": {"$min": "$rooms.price_per_night"},
            "max_price": {"$max": "$rooms.price_per_night"}
        }}
    ]

    result = list(db.accommodations.aggregate(pipeline))

    logging.info(f"Aggregation result: {result}")

    if not result:
        logging.info("No matching accommodations found.")
        return {"min_price": 0.0, "max_price": 0.0}

    return {
        "min_price": float(result[0]["min_price"]), #explicit float conversion.
        "max_price": float(result[0]["max_price"]) #explicit float conversion.
    }