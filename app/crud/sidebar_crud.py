from sqlalchemy.orm import Session
from app.models.menu import Menu
from app.models.submenu import SubMenu
from app.models.role_menu import RoleMenu


def get_sidebar_by_role(
    db: Session,
    role_id: int
):
    # Check if specific role-menu mappings exist for this role
    has_role_mapping = db.query(RoleMenu).filter(RoleMenu.role_id == role_id).first()

    if has_role_mapping:
        menus = (
            db.query(Menu)
            .join(
                RoleMenu,
                Menu.id == RoleMenu.menu_id
            )
            .filter(
                RoleMenu.role_id == role_id,
                Menu.is_active == True,
                Menu.is_deleted == False
            )
            .order_by(Menu.order_index)
            .all()
        )
    else:
        # Fallback: if no specific role_menu restriction exists, return all active non-deleted menus
        menus = (
            db.query(Menu)
            .filter(
                Menu.is_active == True,
                Menu.is_deleted == False
            )
            .order_by(Menu.order_index)
            .all()
        )

    # Filter each menu's submenus to only include active and non-deleted submenus
    for menu in menus:
        if menu.submenu:
            menu.submenu = [
                sm for sm in menu.submenu 
                if sm.status and not sm.is_deleted
            ]

    return menus