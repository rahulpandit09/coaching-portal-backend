# import random
# from datetime import datetime, timedelta
# from fastapi import HTTPException
# from sqlalchemy.orm import Session
# from app.utils.email import send_otp_email
# from app.models.user import User
# from app.utils.hashing import hash_password

# def forgot_password_crud(email: str, db: Session):

#     user = db.query(User).filter(
#         User.email == email
#     ).first()

#     if not user:
#         raise HTTPException(
#             status_code=404,
#             detail="Email not found"
#         )

#     otp = "".join(random.choices("0123456789", k=6))

#     user.otp_code = otp
#     user.otp_expiry = datetime.utcnow() + timedelta(seconds=60)
#     user.otp_verified = False

#     db.commit()
#     #Send email for otp
#     send_otp_email(email, otp)
    
#     return {
#         "message": "OTP sent successfully",
#         "expires_in": 60
#     }


# def verify_otp_crud(email: str, otp: str, db: Session):

#     user = db.query(User).filter(
#         User.email == email
#     ).first()

#     if not user:
#         raise HTTPException(
#             status_code=404,
#             detail="User not found"
#         )

#     if user.otp_code != otp:
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid OTP"
#         )

#     if not user.otp_expiry:
#         raise HTTPException(
#             status_code=400,
#             detail="No OTP found"
#         )

#     if user.otp_expiry < datetime.utcnow():
#         raise HTTPException(
#             status_code=400,
#             detail="OTP expired"
#         )

#     user.otp_verified = True

#     db.commit()

#     return {
#         "message": "OTP verified successfully"
#     }



# def reset_password_crud(
#     email: str,
#     new_password: str,
#     confirm_password: str,
#     db: Session
# ):

#     user = db.query(User).filter(
#         User.email == email
#     ).first()

#     if not user:
#         raise HTTPException(
#             status_code=404,
#             detail="User not found"
#         )

#     if not user.otp_code:
#         raise HTTPException(
#             status_code=400,
#             detail="No active OTP found"
#         )

#     if not user.otp_verified:
#         raise HTTPException(
#             status_code=400,
#             detail="OTP not verified"
#         )

#     if not user.otp_expiry:
#         raise HTTPException(
#             status_code=400,
#             detail="OTP session not found"
#         )

#     if user.otp_expiry < datetime.utcnow():
#         raise HTTPException(
#             status_code=400,
#             detail="OTP session expired"
#         )

#     if new_password != confirm_password:
#         raise HTTPException(
#             status_code=400,
#             detail="Passwords do not match"
#         )

#     user.password = hash_password(new_password)

#     user.otp_code = None
#     user.otp_expiry = None
#     user.otp_verified = False

#     db.commit()

#     return {
#         "message": "Password reset successful"
#     }

# app/crud/auth_crud.py
# app/crud/auth_crud.py

from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.role import Role
from app.models.user import User
from datetime import datetime


def get_user_by_email(db: Session, email: str):

    return db.query(User).filter(
        User.email == email
    ).first()


def get_user_by_username(db: Session, username: str):

    return db.query(User).filter(
        User.username == username
    ).first()


def get_user_by_email_or_username(
        db: Session,
        username: str
):

    return db.query(User).filter(
        or_(
            User.email == username,
            User.username == username
        )
    ).first()


def create_new_user(
        db: Session,
        user_data: dict
):

    user = User(**user_data)

    db.add(user)

    db.commit()

    db.refresh(user)

    return user


def update_last_login(
        db: Session,
        user: User
):

    user.last_login = datetime.utcnow()

    db.commit()

    db.refresh(user)

    return user


def save_otp(
        db: Session,
        user: User,
        otp: str,
        expiry
):

    user.otp_code = otp
    user.otp_expiry = expiry
    user.otp_verified = False

    db.commit()

    db.refresh(user)

    return user


def verify_otp_db(
        db: Session,
        user: User
):

    user.otp_verified = True

    db.commit()

    db.refresh(user)

    return user


def update_password(
        db: Session,
        user: User,
        hashed_password: str
):

    user.password = hashed_password

    db.commit()

    db.refresh(user)

    return user


def clear_otp(
        db: Session,
        user: User
):

    user.otp_code = None
    user.otp_expiry = None
    user.otp_verified = False

    db.commit()

    db.refresh(user)

    return user

def get_role_by_name(
        db: Session,
        name: str
):

    return db.query(Role).filter(
        Role.name == name
    ).first()