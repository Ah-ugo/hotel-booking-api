from typing import Any
import requests
from dotenv import load_dotenv
import os
import logging

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_API_URL = os.getenv("GOOGLE_API_URL", "https://oauth2.googleapis.com/tokeninfo")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_google_token(token: str) -> Any | None:
    try:
        response = requests.get(f"{GOOGLE_API_URL}?id_token={token}")
        user_info = response.json()

        if 'error' in user_info:
            logger.error(f"Google token verification failed: {user_info['error']}")
            return None

        if user_info.get("aud") != GOOGLE_CLIENT_ID:
            logger.error("Token audience does not match GOOGLE_CLIENT_ID")
            return None

        return user_info
    except Exception as e:
        logger.exception("An error occurred while verifying the Google token")
        return None
