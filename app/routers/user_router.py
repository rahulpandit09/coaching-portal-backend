from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.core.security import get_current_user
from app.services.user_service import get_user_profile

route = APIRouter(profix="/users", tags=["Users"])

@route.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return get_user_profile(db, current_user.id)
