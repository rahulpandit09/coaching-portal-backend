from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.submenu_schema import (
    SubMenuCreate,
    SubMenuUpdate
)

from app.crud.submenu_crud import (
    create_submenu,
    get_submenu_by_id,
    get_all_submenu,
    update_submenu,
    delete_submenu
)


# Create
def create_submenu_service(
    db: Session,
    submenu: SubMenuCreate
):
    return create_submenu(db, submenu)


# Get by ID
def get_submenu_by_id_service(
    db: Session,
    submenu_id: int
):
    submenu = get_submenu_by_id(db, submenu_id)

    if not submenu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SubMenu not found"
        )

    return submenu


# Get All
def get_all_submenu_service(
    db: Session
):
    submenus = get_all_submenu(db)

    return {
        "count": len(submenus),
        "data": submenus
    }


# Update
def update_submenu_service(
    db: Session,
    submenu_id: int,
    submenu: SubMenuUpdate
):
    db_submenu = get_submenu_by_id(db, submenu_id)

    if not db_submenu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SubMenu not found"
        )

    update_submenu(
        db,
        db_submenu,
        submenu
    )

    return {
        "message": "SubMenu updated successfully"
    }


# Delete
def delete_submenu_service(
    db: Session,
    submenu_id: int
):
    db_submenu = get_submenu_by_id(db, submenu_id)

    if not db_submenu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SubMenu not found"
        )

    delete_submenu(
        db,
        db_submenu
    )

    return {
        "message": "SubMenu deleted successfully"
    }