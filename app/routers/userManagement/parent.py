from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas.userManagement.parent import (
    ParentDetailCreate,
    ParentDetailUpdate,
    ParentDetailOut
)
from app.crud.userManagement.parent import (
    get_parent_by_id,
    get_parent_by_user_id,
    get_all_parents,
    create_parent_detail,
    update_parent_detail,
    delete_parent_detail
)

router = APIRouter(
    prefix="/user-management/parents",
    tags=["Parent Tab"]
)


@router.get("/", response_model=List[ParentDetailOut])
def list_parents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get all parent details with optional search and pagination.
    """
    return get_all_parents(db=db, skip=skip, limit=limit, search=search)


@router.get("/{user_id}", response_model=ParentDetailOut)
def get_parent(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get parent detail by user ID.
    """
    parent = get_parent_by_user_id(db=db, user_id=user_id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent details not found for this user"
        )
    return parent


@router.post("/{user_id}", response_model=ParentDetailOut, status_code=status.HTTP_201_CREATED)
def create_parent(
    user_id: int,
    parent_data: ParentDetailCreate,
    db: Session = Depends(get_db)
):
    """
    Create parent details for a user.
    """
    existing = get_parent_by_user_id(db=db, user_id=user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent details already exist for this user"
        )
    return create_parent_detail(db=db, user_id=user_id, parent_data=parent_data)


@router.put("/{user_id}", response_model=ParentDetailOut)
def update_parent(
    user_id: int,
    parent_data: ParentDetailUpdate,
    db: Session = Depends(get_db)
):
    """
    Update parent details for a user.
    """
    updated = update_parent_detail(db=db, user_id=user_id, parent_data=parent_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent details not found for this user"
        )
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def remove_parent(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete parent details for a user.
    """
    success = delete_parent_detail(db=db, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent details not found for this user"
        )
    return {"message": "Parent details deleted successfully"}
