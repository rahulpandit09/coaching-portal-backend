import logging
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.core.config import SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

# HTTPBearer security scheme for FastAPI dependency injection and Swagger documentation
security = HTTPBearer(auto_error=False)


def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> int:
    """
    Extract authenticated user_id securely using:
    1. HTTP Bearer token via FastAPI HTTPBearer scheme (Authorization: Bearer <token>)
    2. Direct Authorization header fallback
    3. request.state.user populated by JWTMiddleware
    """
    token = None

    # 1. Bearer token from FastAPI HTTPBearer dependency
    if credentials and getattr(credentials, "credentials", None):
        token = credentials.credentials
    # 2. Direct Authorization header fallback
    elif request and getattr(request, "headers", None) and request.headers.get("Authorization"):
        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        elif auth_header:
            token = auth_header

    # Decode and validate token if found
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            uid = payload.get("user_id") or payload.get("sub") or payload.get("id")
            if uid:
                return int(uid)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

    # 3. Check request.state.user (populated by JWTMiddleware)
    if request and hasattr(request, "state"):
        user_payload = getattr(request.state, "user", {}) or {}
        uid = user_payload.get("user_id") or user_payload.get("sub") or user_payload.get("id")
        if uid:
            try:
                return int(uid)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid user authentication"
                )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide a valid Bearer token."
    )
