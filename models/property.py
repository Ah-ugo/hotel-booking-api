from pydantic import BaseModel
from pymongo import MongoClient
from typing import Optional, List
from bson import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()

mongo_url = os.getenv("MONGO_URL")

client = MongoClient(mongo_url)
db = client['hotel_booking']

class Hotel(BaseModel):
    name: str
    description: str
    price_per_night: float
    location: str
    facilities: List[str]
    rooms: dict  # e.g., {"Deluxe": 150.0, "Executive": 200.0}
    available_dates: List[str]
    images: Optional[List[str]] = []  # List of image URLs

class Apartment(BaseModel):
    name: str
    description: str
    price_per_month: float
    price_per_annum: Optional[float] = None
    location: str
    features: List[str]  # e.g., ["WiFi", "Furnished", "Parking"]
    facilities: List[str]
    available_dates: List[str]
    images: Optional[List[str]] = []  # List of image URLs

class UpdateHotel(BaseModel):
    name: Optional[str]
    description: Optional[str]
    price_per_night: Optional[float]
    location: Optional[str]
    facilities: Optional[List[str]]
    rooms: Optional[dict]
    available_dates: Optional[List[str]]
    images: Optional[List[str]] = None

class UpdateApartment(BaseModel):
    name: Optional[str]
    description: Optional[str]
    price_per_month: Optional[float]
    price_per_annum: Optional[float] = None
    location: Optional[str]
    features: Optional[List[str]]
    facilities: Optional[List[str]]
    available_dates: Optional[List[str]]
    images: Optional[List[str]] = None

class Property:
    @staticmethod
    def find_by_id(property_id: str):
        hotels_collection = db['hotels']
        apartments_collection = db['apartments']

        hotel_data = hotels_collection.find_one({"_id": ObjectId(property_id)})
        if hotel_data:
            return hotel_data

        apartment_data = apartments_collection.find_one({"_id": ObjectId(property_id)})
        if apartment_data:
            return apartment_data

        return None
