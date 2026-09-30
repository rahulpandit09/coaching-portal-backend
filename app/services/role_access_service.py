from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.role import Role
from app.models.menu import Menu
from app.models.submenu import SubMenu
from app.models.permission import Permission
from app.schemas.role_schema import RoleAccessUpdate
from app.crud.role_access_crud import get_role_access_data, update_role_access_data


def get_role_access_service(db: Session, role_id: int):
    # Verify role exists
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )

    access_data = get_role_access_data(db, role_id)
    return access_data


def update_role_access_service(db: Session, role_id: int, access_data: RoleAccessUpdate):
    # 1. Verify role exists
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )

    # Deduplicate IDs
    menu_ids = list(dict.fromkeys(access_data.menuIds))
    submenu_ids = list(dict.fromkeys(access_data.subMenuIds))
    permission_ids = list(dict.fromkeys(access_data.permissionIds))

    # 2. Validate Menu IDs
    valid_menus = {}
    if menu_ids:
        existing_menus = (
            db.query(Menu)
            .filter(Menu.id.in_(menu_ids), Menu.is_deleted == False)
            .all()
        )
        valid_menus = {m.id: m for m in existing_menus}
        missing_menu_ids = set(menu_ids) - set(valid_menus.keys())
        if missing_menu_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or non-existent menu IDs: {list(missing_menu_ids)}"
            )

    # 3. Validate SubMenu IDs & hierarchy
    if submenu_ids:
        existing_submenus = (
            db.query(SubMenu)
            .filter(SubMenu.id.in_(submenu_ids), SubMenu.is_deleted == False)
            .all()
        )
        valid_submenus = {sm.id: sm for sm in existing_submenus}
        missing_submenu_ids = set(submenu_ids) - set(valid_submenus.keys())
        if missing_submenu_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or non-existent submenu IDs: {list(missing_submenu_ids)}"
            )

        # Hierarchy validation: each selected submenu must belong to a selected menuId
        for sm in existing_submenus:
            if sm.menu_id not in valid_menus:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"SubMenu '{sm.title}' (ID: {sm.id}) belongs to Menu ID {sm.menu_id}, "
                        f"which is not included in the selected menuIds"
                    )
                )

    # 4. Validate Permission IDs
    if permission_ids:
        existing_permissions = (
            db.query(Permission)
            .filter(Permission.id.in_(permission_ids))
            .all()
        )
        valid_permission_ids = {p.id for p in existing_permissions}
        missing_permission_ids = set(permission_ids) - valid_permission_ids
        if missing_permission_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or non-existent permission IDs: {list(missing_permission_ids)}"
            )

    # 5. Apply transactional updates
    updated_access = update_role_access_data(
        db=db,
        role_id=role_id,
        menu_ids=menu_ids,
        submenu_ids=submenu_ids,
        permission_ids=permission_ids
    )

    return updated_access
