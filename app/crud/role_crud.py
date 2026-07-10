from sqlalchemy.orm import Session
from app.models.role import Role
from app.schemas.role_schema import RoleCreate, RoleUpdate


def create_role(db: Session, role: RoleCreate):
    db_role = Role(name = role.name)

    db.add(db_role)
    db.commit()
    db.refresh(db_role)

    return db_role

def get_role_by_id(db: Session, role_id: int):
    return (db.query(Role).filter(Role.id == role_id).first())

def get_role_by_name(db: Session, role_name: str):
    return(db.query(Role).filter(Role.name == role_name).first())

def get_all_roles(db: Session):
    return(db.query(Role).all())

def update_role(db: Session, db_role: Role, role: RoleUpdate):
    db_role.name = role.name
    db.commit()
    db.refresh(db_role)

    return(db_role)

def delete_role(db: Session, db_role:Role):
    db.delete(db_role)
    db.commit()

    return (True)