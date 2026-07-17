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

from app.crud.menu_crud import get_menu_by_id

from app.models.submenu import SubMenu

# Create
def create_submenu_service(
    db: Session,
    submenu: SubMenuCreate
):
    # Check if the menu exists and is active
    menu = get_menu_by_id(db, submenu.menu_id)
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu with id {submenu.menu_id} not found."
        )
    if not menu.is_active or menu.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot add submenu to an inactive or deleted menu.")

    # Duplicate validation
    duplicate_title = db.query(SubMenu).filter(SubMenu.menu_id == submenu.menu_id, SubMenu.title == submenu.title, SubMenu.is_deleted == False).first()
    if duplicate_title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SubMenu title already exists in this menu.")
    
    if submenu.path:
        duplicate_path = db.query(SubMenu).filter(SubMenu.menu_id == submenu.menu_id, SubMenu.path == submenu.path, SubMenu.is_deleted == False).first()
        if duplicate_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SubMenu path already exists in this menu.")

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
    
    # Validation on update
    check_menu_id = submenu.menu_id if submenu.menu_id else db_submenu.menu_id
    if submenu.title:
        duplicate_title = db.query(SubMenu).filter(SubMenu.menu_id == check_menu_id, SubMenu.title == submenu.title, SubMenu.id != submenu_id, SubMenu.is_deleted == False).first()
        if duplicate_title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SubMenu title already exists in this menu.")
    
    if submenu.path:
        duplicate_path = db.query(SubMenu).filter(SubMenu.menu_id == check_menu_id, SubMenu.path == submenu.path, SubMenu.id != submenu_id, SubMenu.is_deleted == False).first()
        if duplicate_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SubMenu path already exists in this menu.")

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