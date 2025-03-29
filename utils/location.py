import requests
from typing import Dict, Any, Tuple, Optional
from config.settings import settings

GOOGLE_MAPS_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def geocode_address(address: str) -> Optional[Dict[str, Any]]:
    """
    Convert an address to coordinates using Google Maps Geocoding API

    Args:
        address: Full address string

    Returns:
        Dict containing location data or None if geocoding failed
    """
    params = {
        "address": address,
        "key": settings.GOOGLE_MAPS_API_KEY
    }

    response = requests.get(GOOGLE_MAPS_API_URL, params=params)

    if response.status_code != 200:
        return None

    data = response.json()

    if data["status"] != "OK" or not data["results"]:
        return None

    result = data["results"][0]
    location = result["geometry"]["location"]

    return {
        "type": "Point",
        "coordinates": [location["lng"], location["lat"]],
        "address": result["formatted_address"]
    }


def reverse_geocode(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """
    Convert coordinates to an address using Google Maps Geocoding API

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        Dict containing address data or None if reverse geocoding failed
    """
    params = {
        "latlng": f"{lat},{lng}",
        "key": settings.GOOGLE_MAPS_API_KEY
    }

    response = requests.get(GOOGLE_MAPS_API_URL, params=params)

    if response.status_code != 200:
        return None

    data = response.json()

    if data["status"] != "OK" or not data["results"]:
        return None

    result = data["results"][0]

    address_components = result["address_components"]
    formatted_address = result["formatted_address"]

    # Extract address components
    address_data = {
        "formatted_address": formatted_address,
        "location": {
            "type": "Point",
            "coordinates": [lng, lat],
            "address": formatted_address
        }
    }

    # Extract specific address components
    for component in address_components:
        types = component["types"]
        if "country" in types:
            address_data["country"] = component["long_name"]
            address_data["country_code"] = component["short_name"]
        elif "administrative_area_level_1" in types:
            address_data["state"] = component["long_name"]
        elif "locality" in types:
            address_data["city"] = component["long_name"]
        elif "postal_code" in types:
            address_data["postal_code"] = component["long_name"]

    return address_data


def calculate_distance(
        lat1: float, lng1: float,
        lat2: float, lng2: float
) -> float:
    """
    Calculate the distance between two points using the Haversine formula

    Args:
        lat1: Latitude of point 1
        lng1: Longitude of point 1
        lat2: Latitude of point 2
        lng2: Longitude of point 2

    Returns:
        Distance in meters
    """
    from math import radians, sin, cos, sqrt, atan2

    # Earth radius in meters
    R = 6371000

    # Convert latitude and longitude from degrees to radians
    lat1_rad = radians(lat1)
    lng1_rad = radians(lng1)
    lat2_rad = radians(lat2)
    lng2_rad = radians(lng2)

    # Differences
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad

    # Haversine formula
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c

    return distance

