from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.submenu_schema import (
    SubMenuCreate,
    subMenuUpdate
)

from app.crud.submenu_crud import(
    create_submenu,
    get_submenu_by_id,
    get_all_submenu,
    update_submenu,
    delete_submenu
)

#create submenu
def create_submenu_services(db: Session, submenu:SubMenuCreate):
    return create_submenu(db, submenu)

def get_submenu_by_id_services(db: Session, submenu_id: int):
    submenu = get_submenu_by_id(db, submenu_id)
    if not submenu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu id not found"
        )
    return submenu

def get_all_submenu_service(db: Session):
    submenus = get_all_submenu(db)
    return {
        "count": len(submenus),
        "data": tuple(submenus)
    }

# update submenu
def update_submenu_service(db: Session, submenu_id: int, submenu: subMenuUpdate):
    db_submenu = get_submenu_by_id(db, submenu_id)
    if not db_submenu:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail = "Submenu not Found"
        )
    return update_submenu(db, db_submenu, submenu)

#delete submenu
def delete_submenu_service(db: Session, submenu_id: int, submenu:update_submenu):
    db_submenu = get_submenu_by_id(db, submenu_id)
    if not db_submenu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SubMenu Not Found"
        )
    
    db_submenu = delete_submenu(db, db_submenu)
    return {
        "message": "SubMenu Deleted Successfully"
    }