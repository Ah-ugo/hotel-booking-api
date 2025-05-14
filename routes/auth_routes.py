from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from typing import Dict, Any
import requests
from bson import ObjectId

from config.db import db
from config.settings import settings
from models.newUser import UserCreate, UserInDB, UserResponse, Token, ResetPasswordRequest, ResetPasswordConfirm
from utils.auth import (
    authenticate_user, create_access_token, get_password_hash,
    get_current_active_user, create_reset_token
)
from utils.cloudinary_util import upload_image
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
# from utils.auth import create_reset_token
from utils.email_util import send_reset_email
templates = Jinja2Templates(directory="templates")

router = APIRouter()

RESET_TOKEN_EXPIRE_MINUTES = 30


@router.post("/register", response_model=UserResponse)
def register_user(user_data: UserCreate = Body(...)):
    # Check if user already exists
    if db.users.find_one({"email": user_data.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    user_dict = user_data.dict(exclude={"password"})
    user_dict["hashed_password"] = get_password_hash(user_data.password)
    user_dict["created_at"] = datetime.utcnow() #Add created at field

    # Insert user into database
    result = db.users.insert_one(user_dict)

    # Get created user
    created_user = db.users.find_one({"_id": result.inserted_id})

    created_user["_id"] = str(created_user["_id"]) # convert _id to string
    return UserResponse(**created_user)

@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "is_admin": user.is_admin},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/google", response_model=Token)
def login_with_google(token: str = Body(..., embed=True)):
    # Verify Google token
    google_response = requests.get(
        f"https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={token}"
    )

    if google_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )

    google_data = google_response.json()

    # Check if user exists
    user = db.users.find_one({"email": google_data["email"]})

    if not user:
        # Create new user
        user_dict = {
            "email": google_data["email"],
            "first_name": google_data.get("given_name", ""),
            "last_name": google_data.get("family_name", ""),
            "google_id": google_data["sub"],
            "profile_image_url": google_data.get("picture", ""),
            "is_active": True,
            "is_admin": False,
            "hashed_password": get_password_hash(ObjectId().hex)  # Random password
        }

        result = db.users.insert_one(user_dict)
        user = db.users.find_one({"_id": result.inserted_id})

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"]), "is_admin": user.get("is_admin", False)},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    user_dict = current_user.dict()
    user_dict["_id"] = current_user.id #add the id back into the dictionary
    return UserResponse(**user_dict)


@router.post("/request-password-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(request: ResetPasswordRequest):
    user = db.users.find_one({"email": request.email})
    if not user:
        # Security: Don't reveal whether user exists
        return {"message": "If this email exists, a reset link has been sent"}

    reset_token = create_reset_token()
    reset_token_expires = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

    # Update user in database
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "reset_token": reset_token,
            "reset_token_expires": reset_token_expires
        }}
    )

    # Send email
    try:
        success = await send_reset_email(request.email, reset_token)
        if not success:
            print("Failed to send password reset email")
    except Exception as e:
        print(f"Error sending email: {str(e)}")

    return {"message": "If this email exists, a reset link has been sent"}
# @router.post("/reset-password")
# async def reset_password(form_data: ResetPasswordConfirm):
#     # Find user with this token
#     user = db.users.find_one({
#         "reset_token": form_data.token,
#         "reset_token_expires": {"$gt": datetime.utcnow()}
#     })
#
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid or expired token"
#         )
#
#     # Update password and clear token
#     db.users.update_one(
#         {"_id": user["_id"]},
#         {"$set": {
#             "hashed_password": get_password_hash(form_data.new_password),
#             "reset_token": None,
#             "reset_token_expires": None
#         }}
#     )
#
#     return {"message": "Password updated successfully"}


@router.get("/reset-password", response_class=HTMLResponse)
async def render_reset_form(
        request: Request,
        token: str,
        message: str = None,
        error: str = None
):
    # Verify token is valid (but don't require it to be unexpired yet)
    user = db.users.find_one({"reset_token": token})

    if not user:
        # Token doesn't exist at all
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "error": "Invalid or expired reset link",
                "show_form": False
            }
        )

    # Token exists, check if expired
    is_expired = user["reset_token_expires"] < datetime.utcnow()

    return templates.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "token": token,
            "message": message,
            "error": error,
            "show_form": not is_expired,
            "is_expired": is_expired
        }
    )


@router.post("/reset-password")
async def reset_password(
        request: Request,
        form_data: ResetPasswordConfirm = Depends(ResetPasswordConfirm.as_form)
):
    try:
        # Find user with this token
        user = db.users.find_one({
            "reset_token": form_data.token,
            "reset_token_expires": {"$gt": datetime.utcnow()}
        })

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token"
            )

        # Update password and clear token
        db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "hashed_password": get_password_hash(form_data.new_password),
                "reset_token": None,
                "reset_token_expires": None
            }}
        )

        # Redirect to show success message
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url=f"/api/auth/reset-password?token={form_data.token}&message=Password updated successfully",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        return RedirectResponse(
            url=f"/api/auth/reset-password?token={form_data.token}&error={str(e)}",
            status_code=status.HTTP_303_SEE_OTHER
        )