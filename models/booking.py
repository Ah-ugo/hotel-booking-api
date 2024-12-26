from pydantic import BaseModel
from pymongo import MongoClient
from typing import List
from datetime import datetime
from bson.objectid import ObjectId

from dotenv import load_dotenv
import os

load_dotenv()

mongo_url = os.getenv("MONGO_URL")

client = MongoClient(mongo_url)
db = client['hotel_booking']


class Booking(BaseModel):
    user_id: str
    property_id: str
    start_date: str  # Date format YYYY-MM-DD
    end_date: str
    total_price: float
    property_type: str

    def save(self):
        bookings_collection = db['bookings']
        booking_data = self.dict()
        result = bookings_collection.insert_one(booking_data)
        return str(result.inserted_id)

    @staticmethod
    def get_user_bookings(user_id: str):
        bookings_collection = db['bookings']
        return list(bookings_collection.find({"user_id": user_id}))

    @staticmethod
    def get_booking_by_id(booking_id: str):
        bookings_collection = db['bookings']
        return bookings_collection.find_one({"_id": ObjectId(booking_id)})

    class Config:
        json_encoders = {
            ObjectId: str
        }
