# Hotel Booking API for PrimeHands

This project is a hotel booking API for Primehands built using FastAPI for the backend, with MongoDB as the database. It provides functionality for managing hotels, creating bookings, and managing user data. The app allows users to book hotels, select categories (such as standard and deluxe), and calculate booking costs based on dates and selected categories.

## Features

- **Hotel Management**: Admins can create hotels with different categories and pricing.
- **Booking System**: Users can select a hotel and category, and make a booking.
- **User Authentication**: Users can sign up, log in, and manage bookings.
- **Booking Calculation**: Booking prices are calculated based on the selected category and booking duration.

## Tech Stack

- **Backend**: FastAPI
- **Database**: MongoDB
- **Authentication**: JWT (JSON Web Tokens)
- **File Storage**: Cloudinary (for hotel image uploads)
- **Python Libraries**: Pydantic, Pymongo (MongoDB), etc.

## Installation

Follow these steps to set up and run the project locally:

### 1. Clone the Repository

```bash
git clone https://github.com/Ah-ugo/hotel-booking-api.git
cd hotel-booking-api
```

### 2. Set Up a Virtual Environment

Create a virtual environment to manage project dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

Install required Python libraries using `pip`:

```bash
pip install -r requirements.txt
```

### 4. Set Up MongoDB

Make sure you have MongoDB running locally or use a cloud MongoDB service like [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).

If you're using MongoDB locally, ensure the server is running on the default port (27017).

### 5. Set Up Environment Variables

Create a `.env` file in the root of the project and add the following environment variables:

```
DATABASE_URL=mongodb://localhost:27017
SECRET_KEY=your_jwt_secret_key
CLOUDINARY_URL=your_cloudinary_url
```

### 6. Run the Application

After setting up everything, you can run the FastAPI server with the following command:

```bash
uvicorn main:app
```

The API will be available at `http://localhost:8000`.

## API Endpoints

### 1. User Authentication

- **POST /auth/signup**: Register a new user.
- **POST /auth/login**: Login an existing user and receive a JWT token.

### 2. Hotel Management (Admin)

- **POST /admin/hotels**: Add a new hotel with categories and prices (admin only).
  - Example Request:
    ```json
    {
      "name": "Hotel Paradise",
      "description": "A luxury hotel in the city center.",
      "location": "City Center, State",
      "categories": {
        "standard": 100,
        "deluxe": 200
      }
    }
    ```
  
- **GET /admin/hotels**: Get a list of all hotels (admin only).

### 3. Hotel Booking

- **POST /bookings**: Create a booking for a hotel. Requires a JWT token.
  - Example Request:
    ```json
    {
      "property_id": "hotel_id_12345",
      "user_id": "user_id_12345",
      "start_date": "2024-12-28",
      "end_date": "2024-12-30"
    }
    ```

  - Example Response:
    ```json
    {
      "booking_id": "booking_id_67890",
      "property_id": "hotel_id_12345",
      "category": "deluxe",
      "start_date": "2024-12-28",
      "end_date": "2024-12-30",
      "total_price": 400,
      "property_type": "Hotel"
    }
    ```

- **GET /bookings**: Get a list of bookings for the logged-in user.

### 4. File Upload (Cloudinary Integration)

For hotel images, you can use Cloudinary to upload images. Admins can upload images when creating or updating hotels. The Cloudinary URL would be included in the hotel data when adding a new hotel.

### 5. Error Handling

If an error occurs, the API will return a response in the following format:

```json
{
  "detail": "Error message"
}
```


