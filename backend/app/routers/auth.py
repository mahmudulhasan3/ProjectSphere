import jwt
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.models.student_profile import StudentProfile
from backend.app.schemas.user import SetPasswordRequest
from backend.app.db.database import get_db
from backend.app.models.user import User
from backend.app.schemas.user import (
    UserRegister,
    UserResponse,
    VerifyEmailRequest,
    ResendVerificationRequest,
    UserLogin,
    TokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_purpose_token,
    verify_purpose_token,
    generate_verification_code,
)
from backend.app.core.email import (
    send_verification_code_email,
    send_welcome_email,
    send_password_reset_email,
)
from backend.app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

VERIFICATION_CODE_EXPIRE_MINUTES = 10


from backend.app.models.student_profile import StudentProfile


@router.post("/register", response_model=UserResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    if not user_data.email.endswith("@" + settings.ALLOWED_EMAIL_DOMAIN):
        raise HTTPException(
            status_code=400,
            detail=f"Only {settings.ALLOWED_EMAIL_DOMAIN} email allowed",
        )

    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_student_id = (
        db.query(StudentProfile)
        .filter(StudentProfile.student_id == user_data.student_id)
        .first()
    )
    if existing_student_id:
        raise HTTPException(
            status_code=400, detail="This Student ID is already registered"
        )

    code = generate_verification_code()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=VERIFICATION_CODE_EXPIRE_MINUTES
    )

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role="student",
        is_verified=False,
        verification_code=code,
        verification_code_expires_at=expires_at,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    student_profile = StudentProfile(
        user_id=new_user.id,
        student_id=user_data.student_id,
        department=user_data.department,
        level=user_data.level,
        term=user_data.term,
        section=user_data.section,
    )
    db.add(student_profile)
    db.commit()

    send_verification_code_email(new_user.email, code)

    return new_user


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    if not user.verification_code or user.verification_code != payload.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    if user.verification_code_expires_at is None or datetime.now(
        timezone.utc
    ) > user.verification_code_expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=400, detail="Verification code expired")

    # Mark verified and clear the used code
    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires_at = None
    db.commit()

    # Send welcome email
    send_welcome_email(user.email, user.name)

    return MessageResponse(message="Email verified successfully. You can now log in.")


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    payload: ResendVerificationRequest, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == payload.email).first()

    # Same generic message whether or not the account exists — avoids leaking which emails are registered
    generic_message = MessageResponse(
        message="If that email is registered and not yet verified, a new code has been sent."
    )

    if not user or user.is_verified:
        return generic_message

    code = generate_verification_code()
    user.verification_code = code
    user.verification_code_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=VERIFICATION_CODE_EXPIRE_MINUTES
    )
    db.commit()

    send_verification_code_email(user.email, code)

    return generic_message


@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(
            status_code=403, detail="Please verify your email before logging in"
        )

    access_token = create_access_token(data={"user_id": user.id, "role": user.role})
    return TokenResponse(access_token=access_token)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    # Always return the same message, whether or not the email exists
    if user:
        token = create_purpose_token(user.id, purpose="password_reset")
        send_password_reset_email(user.email, token)

    return MessageResponse(
        message="If that email is registered, a reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        user_id = verify_purpose_token(payload.token, expected_purpose="password_reset")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Reset link expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid reset link")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    db.commit()

    return MessageResponse(message="Password reset successfully. You can now log in.")


@router.post("/set-password", response_model=MessageResponse)
def set_password(payload: SetPasswordRequest, db: Session = Depends(get_db)):
    try:
        user_id = verify_purpose_token(
            payload.token, expected_purpose="supervisor_invite"
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Invite link expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid invite link")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(payload.password)
    user.is_verified = True
    db.commit()

    return MessageResponse(message="Password set successfully. You can now log in.")
