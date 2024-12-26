import json
from typing import List

class Location:
    locations = []

    def __init__(self, name: str, lgas: List[str]):
        self.name = name
        self.lgas = lgas

    @staticmethod
    def get_all_locations() -> List[dict]:
        with open("locations.json") as f:
            return json.load(f)

    @staticmethod
    def get_lgas_by_state(state_name: str) -> List[str]:
        locations = Location.get_all_locations()
        for state in locations:
            if state["name"].lower() == state_name.lower():
                return state["lgas"]
        return []

    def save(self):
        # Example logic for saving location (can be adjusted as needed)
        Location.locations.append({
            "name": self.name,
            "lgas": self.lgas
        })
        # Optionally, you can save it to a file or database here
        with open("locations.json", "w") as f:
            json.dump(Location.locations, f)
        return self.name  # or return an ID or whatever you prefer
