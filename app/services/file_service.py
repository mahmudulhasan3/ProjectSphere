import os
import uuid

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import settings

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".pptx",
    ".jpg",
    ".jpeg",
    ".png",
    ".docx",
    ".xlsx",
    ".zip",
    ".txt",
}
MAX_FILE_SIZE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


def validate_pdf(file_path: str) -> bool:
    try:
        reader = PdfReader(file_path)
        return len(reader.pages) > 0
    except PdfReadError:
        return False


def save_upload_file(file: UploadFile, subfolder: str) -> str:
    """Validates and saves an uploaded file. Returns the relative file path."""

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail="Only PDF, PPTX, JPG, or PNG files are allowed"
        )

    contents = file.file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {settings.MAX_FILE_SIZE_MB}MB)",
        )

    folder = os.path.join(settings.UPLOAD_DIR, subfolder)
    os.makedirs(folder, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    full_path = os.path.join(folder, filename)

    with open(full_path, "wb") as f:
        f.write(contents)

    if ext == ".pdf" and not validate_pdf(full_path):
        os.remove(full_path)
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")

    return full_path
