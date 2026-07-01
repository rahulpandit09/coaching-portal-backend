from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.services.sidebar_service import sidebar_service
from app.schemas.sidebar_schema import SidebarResponse, SidebarListResponse


router = APIRouter(
    prefix="/sidebar",
    tags=["sidebar"]
)


@router.get("/", response_model=SidebarListResponse)
def get_sidebar(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    menus = sidebar_service(
        db,
        current_user.role_id
    )

    return {
        "count": len(menus),
        "data": menus
    }