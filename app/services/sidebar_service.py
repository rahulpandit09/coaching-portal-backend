from sqlalchemy.orm import Session
from app.crud.sidebar_crud import get_sidebar_by_role


def sidebar_service(
    db: Session,
    role_id: int
):

    menus = get_sidebar_by_role(
        db,
        role_id
    )

    return menus