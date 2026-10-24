from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import get_current_user
from app.schemas.user_schema import UserOut
from app.services.user_service import get_all_user_service, get_me_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user=Depends(get_current_user)):
    """
    Get profile details of the currently logged-in user.
    """
    return get_me_service(current_user)


@router.get("/", response_model=List[UserOut])
def get_all_user(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get list of all registered users.
    """
    return get_all_user_service(db, current_user)

