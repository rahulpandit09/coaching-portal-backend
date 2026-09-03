from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.database import get_db
from app.core.security import get_current_user

from app.schemas.user_schema import UserCreate, UserOut

from app.schemas.auth_schema import (
    ForgotPasswordRequest,
    VerifyOtpRequest,
    ResetPasswordRequest,
    RefreshTokenRequest,
    TokenResponse
)

from app.services.auth_service import (
    register_service,
    login_service,
    forgot_password_service,
    verify_otp_service,
    reset_password_service,
    logout_service,
    refresh_token_service,
    get_me_service,
    get_all_users_service
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


@router.post("/login", response_model=TokenResponse)
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
def logout(current_user=Depends(get_current_user)):
    return logout_service(current_user)


@router.post("/refresh")
def refresh(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    return refresh_token_service(
        request.refresh_token,
        db
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user=Depends(get_current_user)):
    return get_me_service(current_user)


@router.get("/get-all-users", response_model=List[UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_all_users_service(db)

