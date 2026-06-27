from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, status

from app.core.config import SECRET_KEY, ALGORITHM


# Create Access Token
def create_access_token(data: dict, minutes: int):
    payload = data.copy()

    payload["exp"] = datetime.utcnow() + timedelta(minutes=minutes)
    payload["type"] = "access"

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Create Refresh Token
def create_refresh_token(data: dict):
    payload = data.copy()

    payload["exp"] = datetime.utcnow() + timedelta(days=7)
    payload["type"] = "refresh"

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Verify Access Token
def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token"
            )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# Verify Refresh Token
def verify_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )