from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from models.user import User
from bson import ObjectId

# Define the token URL
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/auth/login")
router = APIRouter()

# Password hashing utility
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


def get_user_from_token(token: str = Depends(oauth2_scheme)):
    user = User.find_by_id(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def admin_required(user: dict = Depends(get_user_from_token)):
    if not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/auth/signup", response_model=LoginResponse)
async def user_signup(user_data: SignupRequest):
    """User signup endpoint (Normal users)."""
    existing_user = User.find_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = pwd_context.hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        password=hashed_password,
        is_admin=False  # Default to normal user
    )
    user_id = new_user.save()

    token = str(ObjectId(user_id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "username": new_user.username,
            "email": new_user.email,
            "is_admin": new_user.is_admin
        }
    }


@router.post("/auth/admin/signup", response_model=LoginResponse)
async def admin_signup(user_data: SignupRequest):
    """Admin signup endpoint."""
    existing_user = User.find_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = pwd_context.hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        password=hashed_password,
        is_admin=True  # Mark as admin
    )
    user_id = new_user.save()

    token = str(ObjectId(user_id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "username": new_user.username,
            "email": new_user.email,
            "is_admin": new_user.is_admin
        }
    }


@router.post("/auth/login", response_model=LoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Common login endpoint for users and admins."""
    user = User.find_by_email(form_data.username)  # OAuth2PasswordRequestForm uses 'username' for email
    if not user or not pwd_context.verify(form_data.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = str(ObjectId(user['_id']))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user['_id']),
            "username": user['username'],
            "email": user['email'],
            "is_admin": user.get("is_admin", False)
        }
    }


@router.get("/auth/profile")
async def get_profile(user: dict = Depends(get_user_from_token)):
    """Retrieve user profile."""
    return {
        "id": str(user['_id']),
        "username": user['username'],
        "email": user['email'],
        "is_admin": user.get("is_admin", False)
    }


@router.get("/admin/dashboard")
async def admin_dashboard(user: dict = Depends(admin_required)):
    """Admin-only dashboard."""
    return {"message": "Welcome to the admin dashboard", "user": user}
