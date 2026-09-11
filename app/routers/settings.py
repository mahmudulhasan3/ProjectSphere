from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.core.security import hash_password, verify_password
from app.services.file_service import save_upload_file
from app.schemas.settings import (
    ChangePasswordRequest,
    UpdateProfileRequest,
    ThemeUpdateRequest,
    ProfileResponse,
    MessageResponse,
)

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/profile", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.name is not None:
        current_user.name = payload.name

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/profile/photo", response_model=ProfileResponse)
def update_photo(
    photo: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    photo_url = save_upload_file(photo, subfolder=f"profile_photos/{current_user.id}")
    current_user.photo_url = photo_url

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()

    return MessageResponse(message="Password changed successfully")


@router.patch("/theme", response_model=MessageResponse)
def update_theme(
    payload: ThemeUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.theme not in ("light", "dark"):
        raise HTTPException(status_code=400, detail="Theme must be 'light' or 'dark'")

    current_user.theme_preference = payload.theme
    db.commit()

    return MessageResponse(message=f"Theme set to {payload.theme}")
