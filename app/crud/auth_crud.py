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
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise e


def update_last_login(
        db: Session,
        user: User
):
    user.last_login = datetime.utcnow()
    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise e


def save_otp(
        db: Session,
        user: User,
        otp: str,
        expiry
):
    user.otp_code = otp
    user.otp_expiry = expiry
    user.otp_verified = False
    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise e


def verify_otp_db(
        db: Session,
        user: User
):
    user.otp_verified = True
    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise e


def update_password(
        db: Session,
        user: User,
        hashed_password: str
):
    user.password = hashed_password
    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise e


def clear_otp(
        db: Session,
        user: User
):
    user.otp_code = None
    user.otp_expiry = None
    user.otp_verified = False
    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise e

def get_role_by_name(
        db: Session,
        name: str
):

    return db.query(Role).filter(
        Role.name == name
    ).first()


def get_all_users(db: Session):
    return db.query(User).all()