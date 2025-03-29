import os
from dotenv import load_dotenv
# from pydantic import BaseSettings
from pydantic_settings import BaseSettings
load_dotenv()


# class Settings(BaseSettings):
#     # App settings
#     APP_NAME: str = "Accommodation Booking API"
#
#     # JWT settings
#     SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
#     ALGORITHM: str = "HS256"
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
#
#     # Cloudinary settings
#     CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
#     CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
#     CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
#
#     # Email settings
#     SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
#     SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
#     SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
#     SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
#     EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")
#
#     # Paystack settings
#     PAYSTACK_SECRET_KEY: str = os.getenv("PAYSTACK_SECRET_KEY", "")
#     PAYSTACK_PUBLIC_KEY: str = os.getenv("PAYSTACK_PUBLIC_KEY", "")
#
#     # Google OAuth settings
#     GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
#     GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
#
#     # Google Maps API Key
#     GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

class Settings(BaseSettings):
    CLOUD_NAME: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_API_URL: str
    GMAIL_PASS: str
    GMAIL_ADDRESS: str
    API_KEY: str
    API_SECRET: str
    MONGO_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1000
    SECRET_KEY: str = "asdfghgjhtryuyhkjghv"
    ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()

