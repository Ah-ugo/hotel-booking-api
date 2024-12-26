from fastapi import FastAPI
from routes.auth import router as auth_router
from routes.booking import router as booking_router
from routes.payment import router as payment_router
from routes.email import router as email_router
from routes.location import router as location_router
from routes.user import router as user_router
from routes.property import router as property_router

app = FastAPI()

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(property_router, prefix="/property", tags=["property"])
app.include_router(booking_router, prefix="/bookings", tags=["bookings"])
app.include_router(payment_router, prefix="/payments", tags=["payments"])
app.include_router(email_router, prefix="/emails", tags=["emails"])
app.include_router(location_router, prefix="/locations", tags=["locations"])
app.include_router(user_router, prefix="/users", tags=["users"])


@app.get("/")
def read_root():
    return {"message": "Welcome to the Hotel Booking API"}
