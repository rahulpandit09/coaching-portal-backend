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


def get_user_by_id(
        db: Session,
        user_id: int
):

    return db.query(User).filter(
        User.id == user_id
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