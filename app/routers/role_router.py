from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.role_schema import(
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse
)
from app.services.role_service import (
    create_role_service,
    create_role_by_name_service,
    get_role_by_id_service,
    get_all_roles_service,
    update_role_service,
    delete_role_service
)

router = APIRouter(prefix="/roles", tags=["Roles"])

#create role
@router.post("/",response_model=RoleResponse)
def create_role(role: RoleCreate, db: Session = Depends(get_db)):
    return create_role_service(db, role)

#get all router
@router.get("/", response_model=RoleListResponse)
def get_roles(db: Session = Depends(get_db)):
    return get_all_roles_service(db)

#get role by id
@router.get("/{role_id}",response_model=RoleCreate)
def get_role(role_id: int, db: Session = Depends(get_db)):
    return get_role_by_id_service(db, role_id)

#update role 
@router.put("/{role_id}", response_model=RoleResponse)
def update_role(role_id: int, role: RoleUpdate, db: Session = Depends(get_db)):
    return update_role_service(db, role_id, role)

#Delete role
@router.delete("/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db)):
    return delete_role_service(db, role_id)

#role by name 
@router.get("/{role_name}",response_model=RoleResponse)
def get_role_by_name(role_name: str, db: Session = Depends(get_db)):
    return get_role_by_name(db, role_name)