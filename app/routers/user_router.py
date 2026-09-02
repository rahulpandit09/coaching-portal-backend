from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import get_current_user
from app.services.user_service import get_user_profile

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return get_user_profile(db, current_user.id)

