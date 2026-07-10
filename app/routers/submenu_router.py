from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.submenu_schema import (
    SubMenuCreate,
    subMenuUpdate,
    subMenuResponse,
    SubMenuListResponse
)
from app.services.submenu_services import (
    create_submenu_services,
    get_submenu_by_id_services,
    get_all_submenu_service,
    update_submenu_service,
    delete_submenu_service
)

router = APIRouter(prefix="/submenu", tags=["Submenu"])

#Create SubMenu
@router.post("/", response_model=subMenuResponse)
def create_submenu(submenu:SubMenuCreate, db: Session = Depends(get_db)):
    return create_submenu_services(db, submenu)

#get_submenu_by_id
@router.get("/{submenu_id}", response_model=subMenuResponse)
def get_submenu_by_id(submenu_id: int, db: Session = Depends(get_db)):
    return get_submenu_by_id_services(db, submenu_id)

#get all submenu
@router.get("/", response_model=SubMenuListResponse)
def get_all_submenu(db: Session = Depends(get_db)):
    return get_all_submenu_service(db)

#update submenu
@router.put("/{submenu_id}", response_model=subMenuUpdate)
def update_submenu(submenu_id: int, submenu:subMenuUpdate, db: Session = Depends(get_db)):
    return update_submenu_service(db, submenu_id)

#Delete submenu
@router.delete("/{submenu_id}")
def delete_submenu(submenu_id: int, db: Session = Depends(get_db)):
    return delete_submenu_service(db, submenu_id)