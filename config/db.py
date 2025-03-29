import pymongo
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from pydantic import GetJsonSchemaHandler
from pydantic_core import core_schema

load_dotenv()

MONGO_URI = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "hotel_booking")

client = MongoClient(MONGO_URI)
db = client["hotel_booking"]
db.accommodations.create_index([("location", pymongo.GEOSPHERE)])
db.users.create_index([("location", pymongo.GEOSPHERE)])

db.users.create_index("email", unique=True)
db.accommodations.create_index("name")
db.bookings.create_index("user_id")
db.bookings.create_index("accommodation_id")

def init_db():
    global client, db
    try:
        client = MongoClient(MONGO_URI)
        db = client["hotel_booking"]

        # Create indexes for geospatial queries
        # db.accommodations.create_index([("location", pymongo.GEOSPHERE)])
        # db.users.create_index([("location", pymongo.GEOSPHERE)])
        #
        # db.accommodations.create_index([("location", "2dsphere")])
        #
        # # Create other indexes
        # db.users.create_index("email", unique=True)
        # db.accommodations.create_index("name")
        # db.bookings.create_index("user_id")
        # db.bookings.create_index("accommodation_id")

        try:
            db.accommodations.create_index([("location.coordinates", pymongo.GEOSPHERE)])
            db.users.create_index([("location.coordinates", pymongo.GEOSPHERE)])
        except Exception as e:
            print(f"Error creating geospatial indexes: {e}")

            # Create other indexes
        db.users.create_index("email", unique=True)
        db.accommodations.create_index("name")
        db.bookings.create_index("user_id")
        db.bookings.create_index("accommodation_id")

        print(db)

        print("Database initialized successfully.") #Add success message
    except Exception as e:
        print(f"Error initializing database: {e}") #Add error message
        client = None
        db = None

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source: type, handler: GetJsonSchemaHandler):
        return core_schema.str_schema()

    @classmethod
    def __get_pydantic_json_schema__(cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler):
        return {"type": "string", "title": "PyObjectId"}