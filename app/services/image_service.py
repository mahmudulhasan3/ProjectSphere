import os

import cloudinary.uploader
from fastapi import HTTPException, UploadFile

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PHOTO_SIZE_BYTES = 10 * 1024 * 1024  # 5MB


def _public_id(user_id: int) -> str:
    # প্রতি user-এর জন্য fixed id, তাই DB-তে আলাদা column লাগে না
    return f"profile_photos/user_{user_id}"


def upload_profile_photo(file: UploadFile, user_id: int) -> str:
    """ছবি validate করে Cloudinary-তে upload করে, permanent https URL ফেরত দেয়।"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only JPG, PNG or WEBP allowed")

    data = file.file.read()
    if len(data) > MAX_PHOTO_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Photo too large (max 10MB)")

    try:
        result = cloudinary.uploader.upload(
            data,
            public_id=_public_id(user_id),
            overwrite=True,  # নতুন ছবি পুরনোটা replace করবে
            invalidate=True,  # CDN cache refresh
            resource_type="image",
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Photo upload failed, try again")

    return result["secure_url"]


def delete_profile_photo(user_id: int) -> None:
    try:
        cloudinary.uploader.destroy(
            _public_id(user_id), invalidate=True, resource_type="image"
        )
    except Exception:
        pass  # Cloudinary-তে না থাকলেও DB পরিষ্কার করা যাবে
