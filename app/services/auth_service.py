import random
from app.crud.auth_crud import get_user_by_id
from app.utils.token import verify_refresh_token
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.user_schema import UserCreate

from app.crud.auth_crud import (
    get_user_by_email,
    get_user_by_email_or_username,
    create_new_user,
    update_last_login,
    save_otp,
    verify_otp_db,
    update_password,
    clear_otp,
    get_role_by_name,
    get_user_by_username,
    get_all_users
)

from app.utils.hashing import (
    hash_password,
    verify_password
)

from app.utils.token import (
    create_access_token,
    create_refresh_token
)

from app.utils.email import send_otp_email

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES


def register_service(
        db: Session,
        user: UserCreate
):

    email_exists = get_user_by_email(
        db,
        user.email
    )

    if email_exists:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )


    username_exists = get_user_by_username(
        db,
        user.username
    )

    if username_exists:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )


    target_role_name = user.role_name or "Student"
    assigned_role = get_role_by_name(
        db,
        target_role_name
    )

    if not assigned_role:
        raise HTTPException(
            status_code=404,
            detail=f"Role '{target_role_name}' Not Found"
        )

    user_data = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "phone_number": user.phone_number,
        "password": hash_password(
            user.password
        ),
        "role_id": assigned_role.id
    }



    create_new_user(
        db,
        user_data
    )

    return {
        "message": "User registered successfully"
    }


def login_service(
        db: Session,
        form_data: OAuth2PasswordRequestForm
):

    user = get_user_by_email_or_username(
        db,
        form_data.username
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not verify_password(
            form_data.password,
            user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    update_last_login(
        db,
        user
    )

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
        "token_type": "bearer",
        "user": user
    }


def forgot_password_service(
        email: str,
        db: Session
):

    user = get_user_by_email(
        db,
        email
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Email not found"
        )

    otp = "".join(
        random.choices(
            "0123456789",
            k=6
        )
    )

    expiry = datetime.utcnow() + timedelta(
        minutes=5
    )

    save_otp(
        db,
        user,
        otp,
        expiry
    )

    send_otp_email(
        email,
        otp
    )

    return {
        "message": "OTP sent successfully"
    }


def verify_otp_service(
        email: str,
        otp: str,
        db: Session
):

    user = get_user_by_email(
        db,
        email
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user.otp_code != otp:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )

    if user.otp_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="OTP expired"
        )

    verify_otp_db(
        db,
        user
    )

    return {
        "message": "OTP verified"
    }


def reset_password_service(
        email: str,
        new_password: str,
        confirm_password: str,
        db: Session
):

    user = get_user_by_email(
        db,
        email
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if not user.otp_verified:
        raise HTTPException(
            status_code=400,
            detail="OTP not verified"
        )

    if new_password != confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )

    hashed = hash_password(
        new_password
    )

    update_password(
        db,
        user,
        hashed
    )

    clear_otp(
        db,
        user
    )

    return {
        "message": "Password reset successful"
    }


def logout_service(current_user):

    return {
        "message": "Logout successful"
    }


def get_me_service(current_user):
    return current_user


def get_all_users_service(db: Session):
    return get_all_users(db)



def refresh_token_service(
        refresh_token: str,
        db: Session
):

    payload = verify_refresh_token(
        refresh_token
    )

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )


    user_id = payload.get(
        "user_id"
    )

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload"
        )


    user = get_user_by_id(
        db,
        user_id
    )

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