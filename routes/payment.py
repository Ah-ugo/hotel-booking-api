from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from models.payment import Payment, db
from models.booking import Booking
from models.user import User
from fastapi.security import OAuth2PasswordBearer
from routes.auth import oauth2_scheme, admin_required
from utils.email import send_email
from routes.booking import objectid_to_str
router = APIRouter()

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/signin")


class PaymentInput(BaseModel):
    booking_id: str
    amount_paid: float


@router.post("/payments")
async def create_payment(payment_data: PaymentInput, token: str = Depends(oauth2_scheme)):
    user = User.find_by_id(token)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    booking_instance = Booking.get_booking_by_id(payment_data.booking_id)
    if not booking_instance:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking_instance['user_id'] != user['_id']:
        raise HTTPException(status_code=403, detail="Not authorized to make this payment")

    payment_instance = Payment(**payment_data.dict(), user_id=user['_id'], payment_status="success")
    payment_id = payment_instance.save()

    subject = "Payment Confirmation"
    body = f"Dear {user['username']},\n\nYour payment of {payment_data.amount_paid} for the booking {payment_data.booking_id} was successful.\n\nThank you for using our service!"

    email_sent = send_email(user['email'], subject, body)
    if email_sent:
        return {"message": "Payment successful and email sent", "payment_id": payment_id}
    else:
        return {"message": "Payment successful, but failed to send email", "payment_id": payment_id}



@router.get("/payments/{user_id}")
async def get_user_payments(user_id: str):
    payments = Payment.get_user_payments(user_id)
    return {"payments": payments}


@router.get("/payments")
async def get_all_payments(user: dict = Depends(admin_required)):
    payments_collection = db['payments']
    all_payments = list(payments_collection.find())

    return {"payments": [objectid_to_str(payment) for payment in all_payments]}

