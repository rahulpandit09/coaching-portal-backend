from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import get_current_user
from app.schemas.role_schema import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse,
    RoleAccessResponse,
    RoleAccessUpdate
)
from app.services.role_service import (
    create_role_service,
    get_role_by_id_service,
    get_role_by_name_service,
    get_all_roles_service,
    update_role_service,
    delete_role_service
)
from app.services.role_access_service import (
    get_role_access_service,
    update_role_access_service
)

router = APIRouter(prefix="/roles", tags=["Roles"])


# Create role
@router.post("/", response_model=RoleResponse)
def create_role(
    role: RoleCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_role_service(db, role)


# Get all roles
@router.get("/", response_model=RoleListResponse)
def get_roles(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_all_roles_service(db)


# Role by name
@router.get("/name/{role_name}", response_model=RoleResponse)
def get_role_by_name(
    role_name: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_role_by_name_service(db, role_name)


# Get role access (menus, submenus, permissions)
@router.get("/{role_id}/access", response_model=RoleAccessResponse)
def get_role_access(
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_role_access_service(db, role_id)


# Update role access (assign/update menus, submenus, permissions)
@router.put("/{role_id}/access", response_model=RoleAccessResponse)
def update_role_access(
    role_id: int,
    access_data: RoleAccessUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return update_role_access_service(db, role_id, access_data)


# Get role by id
@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_role_by_id_service(db, role_id)


# Update role 
@router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    role: RoleUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return update_role_service(db, role_id, role)


# Delete role
@router.delete("/{role_id}")
def delete_role(
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return delete_role_service(db, role_id)
