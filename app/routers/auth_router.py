from sqlalchemy import or_
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.schemas.user_schema import UserCreate

from app.schemas.auth_schema import (
    TokenSchema,
    ForgotPasswordSchema,
    VerifyOtpSchema,
    ResetPasswordSchema,
    RefreshTokenSchema,
    RefreshResponseSchema
)

from app.crud.auth_crud import (
    forgot_password_crud,
    verify_otp_crud,
    reset_password_crud
)

from app.utils.hashing import hash_password, verify_password

from app.utils.token import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token
)

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.security import get_current_user


router = APIRouter(prefix="/auth", tags=["Auth"])


# Register
@router.post("/register")
def register(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    new_user = User(
        full_name=user.full_name,
        username=user.username,
        email=user.email,
        password=hash_password(user.password),
        role_id=4
    )

    db.add(new_user)
    db.commit()

    return {
        "message": "Student registered successfully"
    }


# Login
@router.post("/login", response_model=TokenSchema)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        or_(
            User.email == form_data.username,
            User.username == form_data.username
        )
    ).first()

    if not user or not verify_password(
        form_data.password,
        user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    user.last_login = datetime.now()
    db.commit()

    access_token = create_access_token(
        {
            "user_id": user.id,
            "role_id": user.role_id
        },
        ACCESS_TOKEN_EXPIRE_MINUTES
    )

    refresh_token = create_refresh_token(
        {
            "user_id": user.id
        }
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# Refresh Token
@router.post("/refresh", response_model=RefreshResponseSchema)
def refresh_token(
    data: RefreshTokenSchema,
    db: Session = Depends(get_db)
):

    payload = verify_refresh_token(
        data.refresh_token
    )

    user_id = payload.get("user_id")

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    new_access_token = create_access_token(
        {
            "user_id": user.id,
            "role_id": user.role_id
        },
        ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


# Logout
@router.post("/logout")
def logout(
    current_user: dict = Depends(get_current_user)
):
    return {
        "message": "Logged out successfully"
    }


# Forgot Password → send OTP
@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordSchema,
    db: Session = Depends(get_db)
):

    return forgot_password_crud(
        data.email,
        db
    )


# Verify OTP
@router.post("/verify-otp")
def verify_otp(
    data: VerifyOtpSchema,
    db: Session = Depends(get_db)
):

    return verify_otp_crud(
        data.email,
        data.otp,
        db
    )


# Reset Password
@router.post("/reset-password")
def reset_password(
    data: ResetPasswordSchema,
    db: Session = Depends(get_db)
):

    return reset_password_crud(
        data.email,
        data.new_password,
        data.confirm_password,
        db
    )