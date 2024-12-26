from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime

from dotenv import load_dotenv
import os

load_dotenv()

mongo_url = os.getenv("MONGO_URL")

client = MongoClient(mongo_url)
db = client['hotel_booking']


class Payment(BaseModel):
    user_id: str
    booking_id: str
    amount_paid: float
    payment_date: datetime = datetime.now()
    payment_status: str  # "success" or "failed"

    def save(self):
        payments_collection = db['payments']
        payment_data = self.dict()
        result = payments_collection.insert_one(payment_data)
        return str(result.inserted_id)

    @staticmethod
    def get_user_payments(user_id: str):
        payments_collection = db['payments']
        return list(payments_collection.find({"user_id": user_id}))
