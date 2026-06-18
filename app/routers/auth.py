from sqlalchemy import or_
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user_schema import UserCreate
from app.schemas.auth_schema import LoginSchema, TokenSchema
from app.utils.hashing import hash_password, verify_password
from app.utils.token import create_access_token
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import get_current_user
from datetime import datetime, timedelta
import secrets
from app.schemas.auth_schema import ForgotPasswordSchema,ResetPasswordSchema
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["Auth"])

# @router.post("/register")
# def register(user: UserCreate, db: Session = Depends(get_db)):
#     if db.query(User).filter(User.email == user.email).first():
#         raise HTTPException(status_code=400, detail="Email already exists")

#     if db.query(User).filter(User.username == user.username).first():
#         raise HTTPException(status_code=400, detail="Username already exists")

#     new_user = User(
#         full_name=user.full_name,
#         email=user.email,
#         username=user.username,
#         password=hash_password(user.password),
#         role="student"
#     )

#     db.add(new_user)
#     db.commit()

#     return {"message": "User registered successfully"}

@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        full_name=user.full_name,
        username=user.username,
        email=user.email,
        password=hash_password(user.password),
        role="student"   # 🔒 Always student
    )

    db.add(new_user)
    db.commit()

    return {"message": "Student registered successfully"}



@router.post("/login", response_model=TokenSchema)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # user = db.query(User).filter(User.email == form_data.username).first()
    # user = db.query(User).filter(or_(    User.email == form_data.username, User.username == form_data.username)).first()
    # user = db.query(User).filter(or_(    User.email == form_data.username, User.full_name == form_data.username)).first()
    user = db.query(User).filter(or_(User.email == form_data.username, User.username == form_data.username)).first()


    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user.last_login = datetime.now()
    db.commit()

    token = create_access_token(
        {"user_id": user.id, "role": user.role},
        ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    # Generate secure token
    token = secrets.token_urlsafe(32)

    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=15)

    db.commit()

    return {
        "message": "Reset token generated",
        "reset_token": token  # Normally send via email
    }


@router.post("/reset-password")
def reset_password(data: ResetPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == data.token).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")

    if user.reset_token_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

    user.password = hash_password(data.new_password)
    user.reset_token = None
    user.reset_token_expiry = None

    db.commit()

    return {"message": "Password reset successfully"}

