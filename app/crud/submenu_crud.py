from sqlalchemy.orm import Session
from app.models.submenu import SubMenu
from app.schemas.submenu_schema import (
    SubMenuCreate,
    SubMenuUpdate
)


def create_submenu(db: Session, submenu: SubMenuCreate):
    db_submenu = SubMenu(
        menu_id=submenu.menu_id,
        title=submenu.title,
        path=submenu.path,
        icon=submenu.icon,
        order_index=submenu.order_index,
        status=submenu.status
    )
    try:
        db.add(db_submenu)
        db.commit()
        db.refresh(db_submenu)
        return db_submenu
    except Exception as e:
        db.rollback()
        raise e

def get_submenu_by_id(db: Session, submenu_id: int):
    return db.query(SubMenu).filter(SubMenu.id == submenu_id, SubMenu.is_deleted == False).first()


def get_all_submenu(db: Session):
    return db.query(SubMenu).filter(SubMenu.is_deleted == False).order_by(SubMenu.order_index).all()

def update_submenu(db: Session, db_submenu: SubMenu, submenu: SubMenuUpdate):
    update_data = submenu.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_submenu, key, value)

    try:
        db.commit()
        db.refresh(db_submenu)
        return db_submenu
    except Exception as e:
        db.rollback()
        raise e

def delete_submenu(db: Session, db_submenu: SubMenu):
    try:
        # Soft delete
        db_submenu.is_deleted = True
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e