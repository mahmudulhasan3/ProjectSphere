from urllib.parse import urlparse

import cloudinary

from app.core.config import settings


def configure_cloudinary() -> None:
    parsed = urlparse(settings.CLOUDINARY_URL)
    cloudinary.config(
        cloud_name=parsed.hostname,
        api_key=parsed.username,
        api_secret=parsed.password,
        secure=True,
    )
