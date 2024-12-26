from fastapi import APIRouter, HTTPException
from utils.email import send_email

router = APIRouter()


@router.post("/send-confirmation")
async def send_confirmation_email(to_email: str, subject: str, body: str):
    success = send_email(to_email, subject, body)
    if success:
        return {"message": "Email sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")


@router.post("/send-booking-confirmation")
async def send_booking_confirmation(to_email: str, booking_id: str):
    # Here, you can customize the email body and subject as needed
    subject = f"Booking Confirmation for Booking ID {booking_id}"
    body = f"Your booking with ID {booking_id} has been confirmed. Enjoy your stay!"

    success = send_email(to_email, subject, body)
    if success:
        return {"message": "Booking confirmation email sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send booking confirmation email")
