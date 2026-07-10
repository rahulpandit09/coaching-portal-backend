from sqlalchemy.orm import Session
from app.models.submenu import SubMenu
from app.schemas.submenu_schema import (
    SubMenuCreate,
    subMenuUpdate
)


def create_submenu(db: Session, submenu: SubMenuCreate):
    db_submenu = SubMenu(title = submenu.title, path = submenu.path, icon = submenu.icon, menu_id = submenu.menu_id, parent_id = submenu.parent_id, is_active = submenu.is_active)
    db.add(db_submenu)
    db.commit()
    db.refresh(db_submenu)

    return db_submenu

def get_submenu_by_id(db: Session, submenu_id: int):
    return(db.query(SubMenu).filter(SubMenu.id == submenu_id). first())


def get_all_submenu(db: Session):
    return(db.query(SubMenu).all())

def update_submenu(db: Session, db_submenu: SubMenu, submenu: subMenuUpdate):
    db_submenu.title = submenu.title
    db_submenu.path = submenu.path
    db_submenu.icon = submenu.icon
    db_submenu.parent_id = submenu.parent_id
    db_submenu.is_active = submenu.is_active

    db.commit()
    db.refresh(db_submenu)

    return db_submenu

def delete_submenu(db: Session, db_submenu: SubMenu):
    db.delete(db_submenu)
    db.commit()

    return True