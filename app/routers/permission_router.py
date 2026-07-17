from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.permission_schema import (
    PermissionCreate,
    PermissionListResponse,
    PermissionResponse,
    PermissionUpdate
)
from app.services.permission_service import (
    creat_permission_service,
    get_permission_by_id_service,
    get_all_permission_service,
    get_permission_by_code_service,
    update_permission_service,
    delete_permission_service
)

router = APIRouter(prefix="/permissions", tags=["Permissions"])

#Create Permission
@router.post("/", response_model=PermissionResponse)
def create_permission(permission: PermissionCreate, db: Session = Depends(get_db)):
    return creat_permission_service(db, permission)

# get_permission_by_id
@router.get("/{permission_id}", response_model=PermissionResponse)
def get_permission_by_id(permission_id: int, db: Session = Depends(get_db)):
    return get_permission_by_id_service(db, permission_id)

#get_all_permission
@router.get("/", response_model=PermissionListResponse)
def get_all_permission(db: Session = Depends(get_db)):
    return get_all_permission_service(db)

#get_permission_by_code
@router.get("/{permission_code}", response_model=PermissionResponse)
def get_permission_by_code(permission_code: str, db: Session = Depends(get_db)):
    return get_permission_by_code_service(db, permission_code)

#update_permission
@router.put("/{permission_id}", response_model=PermissionResponse)
def update_permission(permission_id: int, permission: PermissionResponse, db: Session = Depends(get_db)):
    return update_permission_service(db, permission_id, permission)

#delete_permission
@router.delete("/{permission_id}",)
def delete_permission(permission_id: int, db: Session = Depends(get_db)):
    return delete_permission_service(db, permission_id)