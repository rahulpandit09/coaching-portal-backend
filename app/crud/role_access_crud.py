from sqlalchemy.orm import Session
from app.models.role import Role
from app.models.menu import Menu
from app.models.submenu import SubMenu
from app.models.permission import Permission
from app.models.role_menu import RoleMenu
from app.models.role_submenu import RoleSubMenu
from app.models.role_permission import RolePermission


def get_role_access_data(db: Session, role_id: int):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        return None

    # Get all menus assigned to this role (active & not deleted)
    menus = (
        db.query(Menu)
        .join(RoleMenu, Menu.id == RoleMenu.menu_id)
        .filter(
            RoleMenu.role_id == role_id,
            Menu.is_active == True,
            Menu.is_deleted == False
        )
        .order_by(Menu.order_index)
        .all()
    )

    # Get all submenus assigned to this role (active & not deleted)
    submenus = (
        db.query(SubMenu)
        .join(RoleSubMenu, SubMenu.id == RoleSubMenu.submenu_id)
        .filter(
            RoleSubMenu.role_id == role_id,
            SubMenu.status == True,
            SubMenu.is_deleted == False
        )
        .order_by(SubMenu.order_index)
        .all()
    )

    # Group submenus by menu_id
    submenus_by_menu_id: dict[int, list] = {}
    for sm in submenus:
        submenus_by_menu_id.setdefault(sm.menu_id, []).append(sm)

    # Build structured menu access list
    menu_list = []
    for menu in menus:
        assigned_submenus = submenus_by_menu_id.get(menu.id, [])
        menu_list.append({
            "menuId": menu.id,
            "id": menu.id,
            "title": menu.title,
            "path": menu.path,
            "icon": menu.icon,
            "subMenus": [
                {
                    "subMenuId": sm.id,
                    "id": sm.id,
                    "title": sm.title,
                    "path": sm.path,
                    "icon": sm.icon
                }
                for sm in assigned_submenus
            ]
        })

    # Get all permissions assigned to this role
    permissions = (
        db.query(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .filter(RolePermission.role_id == role_id)
        .order_by(Permission.id)
        .all()
    )

    permission_list = [
        {
            "permissionId": p.id,
            "id": p.id,
            "name": p.name,
            "code": p.code
        }
        for p in permissions
    ]

    return {
        "roleId": role.id,
        "roleName": role.name,
        "menus": menu_list,
        "permissions": permission_list
    }


def update_role_access_data(
    db: Session,
    role_id: int,
    menu_ids: list[int],
    submenu_ids: list[int],
    permission_ids: list[int]
):
    try:
        # Delete existing role mappings
        db.query(RoleMenu).filter(RoleMenu.role_id == role_id).delete(synchronize_session=False)
        db.query(RoleSubMenu).filter(RoleSubMenu.role_id == role_id).delete(synchronize_session=False)
        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete(synchronize_session=False)

        # Add new role_menu entries
        if menu_ids:
            new_role_menus = [RoleMenu(role_id=role_id, menu_id=m_id) for m_id in menu_ids]
            db.add_all(new_role_menus)

        # Add new role_submenu entries
        if submenu_ids:
            new_role_submenus = [RoleSubMenu(role_id=role_id, submenu_id=sm_id) for sm_id in submenu_ids]
            db.add_all(new_role_submenus)

        # Add new role_permission entries
        if permission_ids:
            new_role_permissions = [RolePermission(role_id=role_id, permission_id=p_id) for p_id in permission_ids]
            db.add_all(new_role_permissions)

        db.commit()
        return get_role_access_data(db, role_id)
    except Exception as e:
        db.rollback()
        raise e
