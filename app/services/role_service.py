from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.role_crud import (
    create_role,
    get_role_by_id,
    get_role_by_name,
    get_all_roles,
    update_role,
    delete_role
)
from app.schemas.role_schema import (
    RoleCreate, RoleUpdate
    )

def create_role_service(db: Session, db_role:RoleCreate):
    existing_role = get_role_by_name(db, db_role.name)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already exists"
        )
    return create_role(db, db_role)

def create_role_by_name_service(db: Session, Role: RoleCreate):
    existing_role = get_role_by_name(db, Role.name)
    if existing_role:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail=f"Role with name {Role.name} already exists"
        )

    return create_role(db, role)

def get_role_by_id_service(db: Session, role_id: int):
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"role not found"
        )

    return role

def get_all_roles_service(db: Session):
    roles = get_all_roles(db)
    return{
        "count": len(roles),
        "data": roles
    }

def update_role_service(db: Session, role_id: int, role: RoleUpdate):
    db_role = get_role_by_id(db, role_id)
    if not db_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role not found"
        )
    return update_role(db, db_role, role)

def delete_role_service(db: Session, role_id: int):
    db_role = get_role_by_id(db, role_id)
    if not db_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail = "Role Not Found"
        )
    delete_role(db, db_role)

    return{
        "message": "Role Deleted Successfully"
    }
