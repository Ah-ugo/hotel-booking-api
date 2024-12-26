from fastapi import APIRouter, HTTPException
from models.location import Location
from pydantic import BaseModel

router = APIRouter()


class LocationInput(BaseModel):
    state: str
    lgas: list


@router.post("/add-location")
async def add_location(location_data: LocationInput):
    # Check if the location already exists
    existing_location = Location.get_all_locations()
    for loc in existing_location:
        if loc['state'].lower() == location_data.state.lower():
            raise HTTPException(status_code=400, detail="Location already exists")

    location_instance = Location(**location_data.dict())
    location_id = location_instance.save()
    return {"message": "Location added successfully", "location_id": location_id}


@router.get("/locations")
async def get_all_locations():
    locations = Location.get_all_locations()
    return {"locations": locations}


@router.get("/location/{state}")
async def get_location_by_state(state: str):
    locations = Location.get_all_locations()
    location = [loc for loc in locations if loc['name'].lower() == state.lower()]
    if location:
        return {"location": location[0]}
    else:
        raise HTTPException(status_code=404, detail="Location not found")

