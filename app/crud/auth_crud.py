import random
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.utils.email import send_otp_email
from app.models.user import User
from app.utils.hashing import hash_password

def forgot_password_crud(email: str, db: Session):

    user = db.query(User).filter(
        User.email == email
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Email not found"
        )

    otp = "".join(random.choices("0123456789", k=6))

    user.otp_code = otp
    user.otp_expiry = datetime.utcnow() + timedelta(seconds=60)
    user.otp_verified = False

    db.commit()
    #Send email for otp
    send_otp_email(email, otp)
    #print("OTP =", otp)

    return {
        "message": "OTP sent successfully",
        "expires_in": 60
    }


def verify_otp_crud(email: str, otp: str, db: Session):

    user = db.query(User).filter(
        User.email == email
    ).first()

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

    if not user.otp_expiry:
        raise HTTPException(
            status_code=400,
            detail="No OTP found"
        )

    if user.otp_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="OTP expired"
        )

    user.otp_verified = True

    db.commit()

    return {
        "message": "OTP verified successfully"
    }



def reset_password_crud(
    email: str,
    new_password: str,
    confirm_password: str,
    db: Session
):

    user = db.query(User).filter(
        User.email == email
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if not user.otp_code:
        raise HTTPException(
            status_code=400,
            detail="No active OTP found"
        )

    if not user.otp_verified:
        raise HTTPException(
            status_code=400,
            detail="OTP not verified"
        )

    if not user.otp_expiry:
        raise HTTPException(
            status_code=400,
            detail="OTP session not found"
        )

    if user.otp_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="OTP session expired"
        )

    if new_password != confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )

    user.password = hash_password(new_password)

    user.otp_code = None
    user.otp_expiry = None
    user.otp_verified = False

    db.commit()

    return {
        "message": "Password reset successful"
    }