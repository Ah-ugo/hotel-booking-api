from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from typing import Dict, Any
from bson import ObjectId
from datetime import datetime

from config.db import db
from models.newUser import UserInDB
from models.newBooking import BookingStatus, BookingWithDetails
from models.newPayment import (
    PaymentInitiateRequest, PaymentVerifyRequest,
    PaymentInDB, PaymentResponse, PaymentStatus
)
from utils.auth import get_current_active_user
from utils.paystack import initialize_payment, verify_payment
from utils.email_util import send_payment_receipt

router = APIRouter()


@router.post("/initiate", response_model=Dict[str, Any])
def initiate_payment(
        payment_data: PaymentInitiateRequest = Body(...),
        current_user: UserInDB = Depends(get_current_active_user)
):
    # Check if booking exists
    if not ObjectId.is_valid(payment_data.booking_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid booking ID"
        )

    booking = db.bookings.find_one({
        "_id": ObjectId(payment_data.booking_id),
        "user_id": current_user.id
    })

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Check if booking is already paid
    if booking["payment_status"] == PaymentStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already paid"
        )

    # Check if booking is cancelled
    if booking["booking_status"] == BookingStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot pay for a cancelled booking"
        )

    # Get accommodation details
    accommodation = db.accommodations.find_one({"_id": booking["accommodation_id"]})

    if not accommodation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found"
        )

    # Initialize payment with Paystack
    email = payment_data.email or current_user.email

    metadata = {
        "booking_id": payment_data.booking_id,
        "user_id": str(current_user.id),
        "accommodation_id": str(booking["accommodation_id"]),
        "accommodation_name": accommodation["name"]
    }

    try:
        paystack_response = initialize_payment(
            email=email,
            amount=booking["total_price"],
            callback_url=payment_data.callback_url,
            metadata=metadata
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize payment: {str(e)}"
        )

    # Create payment record
    payment_dict = {
        "booking_id": ObjectId(payment_data.booking_id),
        "user_id": current_user.id,
        "amount": booking["total_price"],
        "payment_method": payment_data.payment_method,
        "reference": paystack_response["reference"],
        "status": PaymentStatus.PENDING,
        "response_data": paystack_response
    }

    # Insert payment into database
    db.payments.insert_one(payment_dict)

    # Update booking payment status
    db.bookings.update_one(
        {"_id": ObjectId(payment_data.booking_id)},
        {
            "$set": {
                "payment_id": paystack_response["reference"],
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "payment_reference": paystack_response["reference"],
        "authorization_url": paystack_response["authorization_url"],
        "access_code": paystack_response["access_code"]
    }


@router.post("/verify", response_model=PaymentResponse)
def verify_payment_status(
        verify_data: PaymentVerifyRequest = Body(...),
        current_user: UserInDB = Depends(get_current_active_user)
):
    # Check if payment exists
    payment = db.payments.find_one({
        "reference": verify_data.reference,
        "user_id": current_user.id
    })

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    # Verify payment with Paystack
    try:
        paystack_response = verify_payment(verify_data.reference)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify payment: {str(e)}"
        )

    # Update payment status
    payment_status = PaymentStatus.PAID if paystack_response["status"] == "success" else PaymentStatus.FAILED

    db.payments.update_one(
        {"reference": verify_data.reference},
        {
            "$set": {
                "status": payment_status,
                "paystack_reference": paystack_response.get("reference"),
                "response_data": paystack_response,
                "updated_at": datetime.utcnow()
            }
        }
    )

    # Update booking status
    booking = db.bookings.find_one({"_id": payment["booking_id"]})

    if booking:
        booking_status = BookingStatus.CONFIRMED if payment_status == PaymentStatus.PAID else BookingStatus.PENDING

        db.bookings.update_one(
            {"_id": payment["booking_id"]},
            {
                "$set": {
                    "payment_status": payment_status,
                    "booking_status": booking_status,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        # Send payment receipt if payment was successful
        if payment_status == PaymentStatus.PAID:
            # Get accommodation details
            accommodation = db.accommodations.find_one({"_id": booking["accommodation_id"]})

            # Create booking with details
            booking_with_details = BookingWithDetails(
                **booking,
                accommodation_details=accommodation,
                user_details=current_user.dict()
            )

            # Get updated payment
            updated_payment = db.payments.find_one({"reference": verify_data.reference})

            # Send receipt
            send_payment_receipt(
                PaymentResponse(**updated_payment),
                booking_with_details
            )

    # Get updated payment
    updated_payment = db.payments.find_one({"reference": verify_data.reference})

    return PaymentResponse(**updated_payment)


@router.get("/{payment_reference}", response_model=PaymentResponse)
def get_payment(
        payment_reference: str,
        current_user: UserInDB = Depends(get_current_active_user)
):
    # Check if payment exists
    payment = db.payments.find_one({
        "reference": payment_reference,
        "user_id": current_user.id
    })

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    return PaymentResponse(**payment)

