from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    student_id: str
    department: str
    level: str
    term: str
    section: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_verified: bool

    class Config:
        from_attributes = True


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


class SetPasswordRequest(BaseModel):
    token: str
    password: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr
