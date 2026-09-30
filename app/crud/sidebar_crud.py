from sqlalchemy.orm import Session
from app.models.menu import Menu
from app.models.submenu import SubMenu
from app.models.role_menu import RoleMenu
from app.models.role_submenu import RoleSubMenu


def get_sidebar_by_role(
    db: Session,
    role_id: int
):
    # Check if specific role-menu mappings exist for this role
    has_role_menu_mapping = db.query(RoleMenu).filter(RoleMenu.role_id == role_id).first()

    if has_role_menu_mapping:
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

    # Check if specific role-submenu mappings exist for this role
    has_role_submenu_mapping = db.query(RoleSubMenu).filter(RoleSubMenu.role_id == role_id).first()
    allowed_submenu_ids = set()
    if has_role_submenu_mapping:
        allowed_submenu_ids = {
            rsm.submenu_id for rsm in db.query(RoleSubMenu.submenu_id).filter(RoleSubMenu.role_id == role_id).all()
        }

    # Filter each menu's submenus to only include active, non-deleted, and authorized submenus
    for menu in menus:
        if menu.submenu:
            menu.submenu = [
                sm for sm in menu.submenu 
                if sm.status and not sm.is_deleted and (not has_role_submenu_mapping or sm.id in allowed_submenu_ids)
            ]

    return menus