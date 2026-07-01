from sqlalchemy.orm import Session
from app.models.menu import Menu
from app.models.role_menu import RoleMenu


def get_sidebar_by_role(
    db: Session,
    role_id: int
):

    menus = (
        db.query(Menu)
        .join(
            RoleMenu,
            Menu.id == RoleMenu.menu_id
        )
        .filter(
            RoleMenu.role_id == role_id
        )
        .all()
    )

    return menus