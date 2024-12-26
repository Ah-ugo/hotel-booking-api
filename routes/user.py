from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
from routes.auth import oauth2_scheme
from models.user import User, UpdateProfileInput
from dotenv import load_dotenv
import os

load_dotenv()

mongo_url = os.getenv("MONGO_URL")

client = MongoClient(mongo_url)
db = client['hotel_booking']
users_collection = db['users']

router = APIRouter()

class UpdateUserProfile(BaseModel):
    username: str
    email: str
    password: str


def str_objectid(id: ObjectId) -> str:
    return str(id)


@router.get("/profile")
async def get_user_profile(token: str = Depends(oauth2_scheme)):
    user = users_collection.find_one({"_id": ObjectId(token)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "username": user['username'],
        "email": user['email'],
        "is_admin": user.get('is_admin', False)
    }


# @router.put("/update-profile")
# async def update_user_profile(update_data: UpdateUserProfile, token: str = Depends(oauth2_scheme)):
#     user = users_collection.find_one({"_id": ObjectId(token)})
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     user['username'] = update_data.username
#     user['email'] = update_data.email
#     user['password'] = update_data.password
#     users_collection.update_one({"_id": ObjectId(user['_id'])}, {"$set": user})
#     return {"message": "Profile updated successfully"}

@router.put("/users/update-profile")
async def update_profile(profile_data: UpdateProfileInput, token: str = Depends(oauth2_scheme)):
    # Fetch the user data from the database
    user_data = User.find_by_id(token)

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Create a User object from the data
    user = User(**user_data)

    # Update the user fields if provided in the request
    if profile_data.username:
        user.username = profile_data.username

    if profile_data.email:
        user.email = profile_data.email

    if profile_data.password:
        user.hash_password()  # Use the hash_password method to update the password


    user.save()

    return {"message": "Profile updated successfully"}



@router.get("/users/{user_id}")
async def get_user_by_id(user_id: str):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user}


@router.delete("/delete-user/{user_id}")
async def delete_user(user_id: str):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    users_collection.delete_one({"_id": ObjectId(user_id)})
    return {"message": "User deleted successfully"}
