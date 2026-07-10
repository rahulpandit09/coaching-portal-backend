from sqlalchemy.orm import Session
from app.models.menu import Menu
from app.schemas.menu_schema import (
    MenuCreate,
    MenuUpdate
)

def create_menu(db: Session, menu: MenuCreate):
    db_menu = Menu(title = menu.title, path = menu.path, icon = menu.icon, parent_id = menu.parent_id, is_active = menu.is_active)
    db.add(db_menu)
    db.flush()
    db.commit()
    db.refresh(db_menu)

    return db_menu

def get_menu_by_id(db: Session, menu_id: int):
    return(db.query(Menu).filter(Menu.id == menu_id). first())


def get_all_menu(db: Session):
    return(db.query(Menu).all())

def update_menu(db: Session, db_menu: Menu, menu: MenuUpdate):
    db_menu.title = menu.title
    db_menu.path = menu.path
    db_menu.icon = menu.icon
    db_menu.parent_id = menu.parent_id
    db_menu.is_active = menu.is_active

    db.commit()
    db.refresh(db_menu)

    return db_menu

def delete_menu(db: Session, db_menu: Menu):
    db.delete(db_menu)
    db.commit()

    return True