import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
import os
from config.settings import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUD_NAME,
    api_key=settings.API_KEY,
    api_secret=settings.API_SECRET
)


def upload_image(file: UploadFile, folder: str = "accommodation_booking") -> str:
    """
    Upload an image to Cloudinary and return the URL
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Create a temporary file
        file_content = file.file.read()
        with open(f"temp_{file.filename}", "wb") as buffer:
            buffer.write(file_content)

        # Reset file pointer
        file.file.seek(0)

        # Upload to cloudinary
        result = cloudinary.uploader.upload(
            f"temp_{file.filename}",
            folder=folder,
            resource_type="image"
        )

        # Remove the temporary file
        os.remove(f"temp_{file.filename}")

        return result["secure_url"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


def delete_image(url: str) -> bool:
    """
    Delete an image from Cloudinary
    """
    try:
        # Extract public_id from URL
        parts = url.split("/")
        filename = parts[-1].split(".")[0]
        folder = parts[-2]
        public_id = f"{folder}/{filename}"

        # Delete from cloudinary
        result = cloudinary.uploader.destroy(public_id)
        return result["result"] == "ok"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete image: {str(e)}")

