from sqlalchemy.orm import Session
from app.models.menu import Menu
from app.schemas.menu_schema import (
    MenuCreate,
    MenuUpdate
)

def create_menu(db: Session, menu: MenuCreate):
    db_menu = Menu(
        title=menu.title, 
        path=menu.path, 
        icon=menu.icon, 
        parent_id=menu.parent_id, 
        is_active=menu.is_active,
        order_index=menu.order_index
    )
    try:
        db.add(db_menu)
        db.commit()
        db.refresh(db_menu)
        return db_menu
    except Exception as e:
        db.rollback()
        raise e

def get_menu_by_id(db: Session, menu_id: int):
    return db.query(Menu).filter(Menu.id == menu_id, Menu.is_deleted == False).first()


def get_all_menu(db: Session):
    return db.query(Menu).filter(Menu.is_deleted == False).order_by(Menu.order_index).all()

def update_menu(db: Session, db_menu: Menu, menu: MenuUpdate):
    update_data = menu.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_menu, key, value)

    try:
        db.commit()
        db.refresh(db_menu)
        return db_menu
    except Exception as e:
        db.rollback()
        raise e

def delete_menu(db: Session, db_menu: Menu):
    try:
        # Soft delete
        db_menu.is_deleted = True
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e