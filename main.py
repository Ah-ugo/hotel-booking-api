# from fastapi import FastAPI
# from routes.auth import router as auth_router
# from routes.booking import router as booking_router
# from routes.payment import router as payment_router
# from routes.email import router as email_router
# from routes.location import router as location_router
# from routes.user import router as user_router
# from routes.property import router as property_router
#
# app = FastAPI()
#
# app.include_router(auth_router, prefix="/auth", tags=["auth"])
# app.include_router(property_router, prefix="/property", tags=["property"])
# app.include_router(booking_router, prefix="/bookings", tags=["bookings"])
# app.include_router(payment_router, prefix="/payments", tags=["payments"])
# app.include_router(email_router, prefix="/emails", tags=["emails"])
# app.include_router(location_router, prefix="/locations", tags=["locations"])
# app.include_router(user_router, prefix="/users", tags=["users"])
#
#
# @app.get("/")
# def read_root():
#     return {"message": "Welcome to the Hotel Booking API"}

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from routes import auth_routes, user_routes, admin_routes, booking_routes, payment_routes, accommodation_routes
from config.db import init_db

app = FastAPI(
    title="Accommodation Booking API",
    description="API for booking hotels, apartments, hostels and lodges",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database connection
@app.on_event("startup")
def startup_db_client():
    init_db()

# Include routers
app.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(user_routes.router, prefix="/api/users", tags=["Users"])
app.include_router(admin_routes.router, prefix="/api/admin", tags=["Admin"])
app.include_router(booking_routes.router, prefix="/api/bookings", tags=["Bookings"])
app.include_router(payment_routes.router, prefix="/api/payments", tags=["Payments"])
app.include_router(accommodation_routes.router, prefix="/api/accommodations", tags=["Accommodations"])

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Accommodation Booking API"}





