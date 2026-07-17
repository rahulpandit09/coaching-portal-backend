from sqlalchemy.orm import Session
from app.models.permission import Permission
from app.schemas.permission_schema import (
    PermissionCreate,
    PermissionUpdate
)

def create_permission(db: Session, permission: PermissionCreate):
    db_permission = Permission(name = permission.name, code = permission.code)
    try:
        db.add(db_permission)
        db.commit()
        db.refresh(db_permission)
        return(db_permission)
    except Exception as e:
        db.rollback()
        raise e

def get_permission_by_id(db: Session, permission_id: int):
    return (db.query(Permission).filter(Permission.id == permission_id).first())

def get_permission_by_code(db: Session, code: str):
    return(db.query(Permission).filter(Permission.code == code).first())

def get_all_permission(db: Session):
    return(db.query(Permission).all())

def update_permission(db: Session, db_permission: Permission, permission: PermissionUpdate):
    db_permission.name = permission.name
    db_permission.code = permission.code
    try:
        db.commit()
        db.refresh(db_permission)
        return db_permission
    except Exception as e:
        db.rollback()
        raise e

def delete_permission(db: Session, db_permission: Permission):
    try:
        db.delete(db_permission)
        db.commit()
        return(True)
    except Exception as e:
        db.rollback()
        raise e
