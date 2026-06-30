from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user

from app.schemas.sidebar_schema import SidebarResponse
from app.crud.sidebar_crud import get_sidebar_by_role


router = APIRouter(
    prefix="/sidebar",
    tags=["Sidebar"]
)


@router.get(
    "/",
    response_model=list[SidebarResponse]
)
def get_sidebar(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_sidebar_by_role(db, current_user.role)