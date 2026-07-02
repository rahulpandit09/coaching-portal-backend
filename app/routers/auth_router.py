# app/routers/auth_router.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.database import get_db

from app.schemas.user_schema import UserCreate

from app.schemas.auth_schema import (
    ForgotPasswordRequest,
    VerifyOtpRequest,
    ResetPasswordRequest
)

from app.services.auth_service import (
    register_service,
    login_service,
    forgot_password_service,
    verify_otp_service,
    reset_password_service,
    logout_service,
    refresh_token_service
)

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post("/register")
def register(
        user: UserCreate,
        db: Session = Depends(get_db)
):
    return register_service(
        db,
        user
    )


@router.post("/login")
def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    return login_service(
        db,
        form_data
    )


@router.post("/forgot-password")
def forgot_password(
        request: ForgotPasswordRequest,
        db: Session = Depends(get_db)
):
    return forgot_password_service(
        request.email,
        db
    )


@router.post("/verify-otp")
def verify_otp(
        request: VerifyOtpRequest,
        db: Session = Depends(get_db)
):
    return verify_otp_service(
        request.email,
        request.otp,
        db
    )


@router.post("/reset-password")
def reset_password(
        request: ResetPasswordRequest,
        db: Session = Depends(get_db)
):
    return reset_password_service(
        request.email,
        request.new_password,
        request.confirm_password,
        db
    )


@router.post("/logout")
def logout():
    return logout_service()


@router.post("/refresh")
def refresh():
    return refresh_token_service()