from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId

from config.settings import settings
from config.db import db
from models.newUser import TokenData, UserInDB
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(email: str) -> Optional[UserInDB]:
    user = db.users.find_one({"email": email})
    if user:
        user["_id"] = str(user["_id"])  # Convert ObjectId to string
        return UserInDB(**user)
    return None


def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    if ObjectId.is_valid(user_id):
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"]) # convert objectId to string
            return UserInDB(**user)
    return None


def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    user = get_user(email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id, is_admin=payload.get("is_admin", False))
    except JWTError:
        raise credentials_exception

    user = get_user_by_id(token_data.user_id)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_admin_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def create_reset_token() -> str:
    return secrets.token_urlsafe(32)