from sqlalchemy.orm import Session
from app.models.sidebar_model import Sidebar


def get_sidebar_by_role(
    db: Session,
    role: str
):
    menus = db.query(Sidebar).filter(
        Sidebar.role == role
    ).all()

    return menus