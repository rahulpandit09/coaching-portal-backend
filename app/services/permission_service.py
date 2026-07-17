from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.permission_schema import (
    PermissionCreate,
    PermissionUpdate
)
from app.crud.permission_crud import (
    create_permission,
    get_permission_by_id,
    get_permission_by_code,
    get_all_permission,
    update_permission,
    delete_permission
) 

#get permission 
def creat_permission_service(db: Session, permission: PermissionCreate):
    existing_permission = get_permission_by_code(db, permission.code)
    if existing_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="peermission already exists"
        )
    return create_permission(db, permission)

#get permission by id 
def get_permission_by_id_service(db: Session, permission_id: int):
    permission = get_permission_by_id(db, permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail= "Permission Not Found"
        )
    return permission

#get permission by code
def get_permission_by_code_service(db: Session, permission_code: str):
    permission = get_permission_by_code(db, permission_code)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail= "Permission Code not Found"
        )
    return permission

#get all permission
def get_all_permission_service(db: Session):
    permissions = get_all_permission(db)
    return {
        "count" : len(permissions),
        "data" : tuple(permissions)
    }

#update permission
def update_permission_service(db: Session, permission_id: int, permission:PermissionUpdate):
    db_permission = get_permission_by_id(db, permission_id = permission_id)
    if not db_permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
        duplicate_permission = get_all_permission_by_code(db, permission.code)
        if duplicate_permission and duplicate_permission.id != permission_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail= "Permission Code already exists"
            )
    return update_permission(db, db_permission, permission)
   
#delete permission 
def delete_permission_service(db: Session, permission_id: int):
    db_permission = get_permission_by_id(db, permission_id)
    if not db_permission:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Permission not Found"
        )
    delete_permission(db, db_permission)
    return{
        "message": "permission deleted successfully"
    }