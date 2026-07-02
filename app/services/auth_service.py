# # app/services/auth_service.py

# from fastapi import HTTPException
# from datetime import datetime
# from sqlalchemy.orm import Session
# from fastapi.security import OAuth2PasswordRequestForm
# from app.schemas.user_schema import UserCreate

# from app.crud.auth_crud import (
#     get_user_by_email_or_username,
#     create_new_user,
#     get_role_by_name
# )

# from app.utils.hashing import (
#     hash_password,
#     verify_password
# )

# from app.utils.token import (
#     create_access_token,
#     create_refresh_token
# )

# from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES


# def register_service(
#         db: Session,
#         user: UserCreate
# ):

#     student_role = get_role_by_name(
#         db,
#         "Student"
#     )

#     existing_user = get_user_by_email_or_username(
#         db,
#         user.email
#     )
#     role_id = student_role.id

#     if existing_user:
#         raise HTTPException(
#             status_code=400,
#             detail="User already exists"
#         )

#     user_data = {
#         "first_name": user.first_name,
#         "last_name": user.last_name,
#         "username": user.username,
#         "email": user.email,
#         "password": hash_password(user.password),
#         "role_id": role_id
#     }

#     new_user = create_new_user(
#         db,
#         user_data
#     )

#     return {
#     "message": "User registered successfully",
#     "user": {
#         "id": new_user.id,
#         "first_name": new_user.first_name,
#         "last_name": new_user.last_name,
#         "email": new_user.email
#     }
# }


# def login_service(
#         db: Session,
#         form_data: OAuth2PasswordRequestForm
# ):

#     user = get_user_by_email_or_username(
#         db,
#         form_data.username
#     )

#     if not user:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid credentials"
#         )

#     if not verify_password(
#             form_data.password,
#             user.password
#     ):
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid credentials"
#         )

#     user.last_login = datetime.now()
#     db.commit()

#     access_token = create_access_token(
#         {
#             "user_id": user.id,
#             "role_id": user.role_id
#         },
#         ACCESS_TOKEN_EXPIRE_MINUTES
#     )

#     refresh_token = create_refresh_token(
#         {
#             "user_id": user.id
#         }
#     )

#     return {
#     "statusCode": 200,
#     "statusMessage": "Login successful",
#     "user": {
#         "id": user.id,
#         "first_name": user.first_name,
#         "last_name": user.last_name,
#         "full_name": f"{user.first_name} {user.last_name}",
#         "email": user.email,
#         "role_id": user.role_id
#     },
#     "tokens": {
#         "access_token": access_token,
#         "refresh_token": refresh_token
#     }
# }



# app/services/auth_service.py

import random

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
    get_user_by_username
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


    student_role = get_role_by_name(
        db,
        "Student"
    )

    if not student_role:
        raise HTTPException(
            status_code=500,
            detail="Student role not found"
        )


    user_data = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "password": hash_password(
            user.password
        ),
        "role_id": student_role.id
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
        "token_type": "bearer"
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


def logout_service():

    return {
        "message": "Logout successful"
    }


def refresh_token_service():

    return {
        "message": "Refresh token logic here"
    }