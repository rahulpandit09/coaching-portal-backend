from fastapi import HTTPException, status 
from sqlalchemy.orm import Session
from app.schemas.menu_schema import (
    MenuCreate,
    MenuUpdate
)
from app.crud.menu_crud import(
    create_menu,
    get_menu_by_id,
    get_all_menu,
    update_menu,
    delete_menu
)
from app.models.menu import Menu

# Create Menu
def create_menu_service(db: Session, menu: MenuCreate):
    if menu.parent_id:
        parent = get_menu_by_id(db, menu.parent_id)
        if not parent or not parent.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent menu does not exist or is inactive.")

    # Duplicate validation across DB to prevent 500 DB constraint error
    if db.query(Menu).filter(Menu.title == menu.title).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Menu title already exists.")
    if menu.path and db.query(Menu).filter(Menu.path == menu.path).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Menu path already exists.")

    return create_menu(db, menu)

# Get Menu by_id
def get_menu_by_id_service(db: Session, menu_id: int):
    menu = get_menu_by_id(db, menu_id)
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu Not Found"
        )
    return menu

# Get all menu 
def get_all_menu_service(db: Session):
    menus = get_all_menu(db)
    return {
        "count": len(menus),
        "data": menus
    }

# Update menu
def update_menu_service(db: Session, menu_id: int, menu: MenuUpdate):
    db_menu = get_menu_by_id(db, menu_id)
    if not db_menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu Not Found"
        )
    
    if menu.parent_id is not None:
        if menu.parent_id == menu_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Menu cannot be its own parent.")
        parent = get_menu_by_id(db, menu.parent_id)
        if not parent or not parent.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent menu does not exist or is inactive.")

    # Duplicate validation on update
    if menu.title:
        duplicate_title = db.query(Menu).filter(Menu.title == menu.title, Menu.id != menu_id).first()
        if duplicate_title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Menu title already exists.")
    if menu.path:
        duplicate_path = db.query(Menu).filter(Menu.path == menu.path, Menu.id != menu_id).first()
        if duplicate_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Menu path already exists.")

    return update_menu(db, db_menu, menu)

# Delete menu
def delete_menu_service(db: Session, menu_id: int):
    db_menu = get_menu_by_id(db, menu_id)
    if not db_menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu Not Found"
        )

    delete_menu(db, db_menu)
    return {
        "message": "Menu deleted successfully"
    }