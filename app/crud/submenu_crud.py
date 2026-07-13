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
    db.add(db_submenu)
    db.commit()
    db.refresh(db_submenu)

    return db_submenu

def get_submenu_by_id(db: Session, submenu_id: int):
    return(db.query(SubMenu).filter(SubMenu.submenu_id == submenu_id). first())


def get_all_submenu(db: Session):
    return(db.query(SubMenu).all())

def update_submenu(db: Session, db_submenu: SubMenu, submenu: SubMenuUpdate):
    db_submenu.title = submenu.title
    db_submenu.path = submenu.path
    db_submenu.icon = submenu.icon
    db_submenu.order_index = submenu.order_index
    db_submenu.status = submenu.status

    db.commit()
    db.refresh(db_submenu)

    return db_submenu

def delete_submenu(db: Session, db_submenu: SubMenu):
    db.delete(db_submenu)
    db.commit()

    return True