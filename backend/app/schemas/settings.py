from pydantic import BaseModel


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    name: str | None = None


class ThemeUpdateRequest(BaseModel):
    theme: str  # "light" or "dark"


class ProfileResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    photo_url: str | None
    theme_preference: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str
