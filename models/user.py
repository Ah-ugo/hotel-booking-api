from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from typing import Optional
from bson import ObjectId
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

mongo_url = os.getenv("MONGO_URL")
client = MongoClient(mongo_url)
db = client['hotel_booking']
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseModel):
    email: str
    username: str
    password: Optional[str] = None
    google_id: Optional[str] = None
    is_admin: bool = False

    def hash_password(self):
        if self.password:
            self.password = pwd_context.hash(self.password)

    def verify_password(self, plain_password: str) -> bool:
        return pwd_context.verify(plain_password, self.password)

    def save(self):
        users_collection = db['users']
        user_data = self.dict()
        result = users_collection.insert_one(user_data)
        return str(result.inserted_id)

    @staticmethod
    def find_by_id(user_id: str):
        user = db['users'].find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
        return user

    @staticmethod
    def find_by_email(email: str):
        return db['users'].find_one({"email": email})

    @staticmethod
    def find_by_google_id(google_id: str):
        return db['users'].find_one({"google_id": google_id})


class UpdateProfileInput(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
