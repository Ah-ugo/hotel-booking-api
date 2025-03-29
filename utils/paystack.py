import requests
import json
import uuid
from typing import Dict, Any, Optional
from config.settings import settings

PAYSTACK_BASE_URL = "https://api.paystack.co"


def generate_reference():
    """Generate a unique reference for Paystack transactions"""
    return f"ACCOM-{uuid.uuid4().hex[:10].upper()}"


def initialize_payment(
        email: str,
        amount: float,
        callback_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Initialize a payment with Paystack

    Args:
        email: Customer's email
        amount: Amount in the smallest currency unit (kobo for NGN)
        callback_url: URL to redirect to after payment
        metadata: Additional data to store with the transaction

    Returns:
        Dict containing authorization_url, access_code, and reference
    """
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    # Convert amount to kobo (smallest currency unit)
    amount_in_kobo = int(amount * 100)

    payload = {
        "email": email,
        "amount": amount_in_kobo,
        "reference": generate_reference(),
    }

    if callback_url:
        payload["callback_url"] = callback_url

    if metadata:
        payload["metadata"] = metadata

    response = requests.post(
        f"{PAYSTACK_BASE_URL}/transaction/initialize",
        headers=headers,
        data=json.dumps(payload)
    )

    if response.status_code != 200:
        raise Exception(f"Failed to initialize payment: {response.text}")

    return response.json()["data"]


def verify_payment(reference: str) -> Dict[str, Any]:
    """
    Verify a payment with Paystack

    Args:
        reference: Transaction reference

    Returns:
        Dict containing transaction details
    """
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.get(
        f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
        headers=headers
    )

    if response.status_code != 200:
        raise Exception(f"Failed to verify payment: {response.text}")

    return response.json()["data"]

