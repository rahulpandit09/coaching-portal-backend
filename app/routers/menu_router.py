from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.menu_schema import (
    MenuCreate,
    MenuListResponse,
    MenuResponse,
    MenuUpdate
)
from app.services.menu_service import (
    create_menu_service,
    get_menu_by_id_service,
    get_all_menu_service,
    update_menu_service,
    delete_menu_service
)

router = APIRouter(prefix="/menu", tags=["Menu"])

#Create Menu
@router.post("/", response_model=MenuResponse)
def create_menu(menu: MenuCreate, db: Session = Depends(get_db)):
    return create_menu_service(db, menu)

#get menu_by_id
@router.get("/{menu_id}", response_model=MenuResponse)
def get_menu_by_id(menu_id: int, db: Session = Depends(get_db)):
    return get_menu_by_id_service(db, menu_id)

#get all menu
@router.get("/", response_model=MenuListResponse)
def get_all_menus(db: Session = Depends(get_db)):
    return get_all_menu_service(db)

#update menu
@router.put("/{menu_id}", response_model=MenuResponse)
def update_menu(menu_id:int, menu: MenuResponse, db: Session = Depends(get_db)):
    return update_menu_service(db, menu_id, menu)

#delete menu
@router.delete("/{menu_id}")
def delete_menu(menu_id: int, db: Session = Depends(get_db)):
    return delete_menu_service(db, menu_id)