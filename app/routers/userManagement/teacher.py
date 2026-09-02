from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas.userManagement.teacher import (
    TeacherDetailCreate,
    TeacherDetailUpdate,
    TeacherDetailOut
)
from app.crud.userManagement.teacher import (
    get_teacher_by_id,
    get_teacher_by_user_id,
    get_all_teachers,
    create_teacher_detail,
    update_teacher_detail,
    delete_teacher_detail
)

router = APIRouter(
    prefix="/user-management/teachers",
    tags=["Teacher Tab"]
)


@router.get("/", response_model=List[TeacherDetailOut])
def list_teachers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get all teacher details with optional search and pagination.
    """
    return get_all_teachers(db=db, skip=skip, limit=limit, search=search)


@router.get("/{user_id}", response_model=TeacherDetailOut)
def get_teacher(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get teacher detail by user ID.
    """
    teacher = get_teacher_by_user_id(db=db, user_id=user_id)
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher details not found for this user"
        )
    return teacher


@router.post("/{user_id}", response_model=TeacherDetailOut, status_code=status.HTTP_201_CREATED)
def create_teacher(
    user_id: int,
    teacher_data: TeacherDetailCreate,
    db: Session = Depends(get_db)
):
    """
    Create teacher details for a user.
    """
    existing = get_teacher_by_user_id(db=db, user_id=user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teacher details already exist for this user"
        )
    return create_teacher_detail(db=db, user_id=user_id, teacher_data=teacher_data)


@router.put("/{user_id}", response_model=TeacherDetailOut)
def update_teacher(
    user_id: int,
    teacher_data: TeacherDetailUpdate,
    db: Session = Depends(get_db)
):
    """
    Update teacher details for a user.
    """
    updated = update_teacher_detail(db=db, user_id=user_id, teacher_data=teacher_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher details not found for this user"
        )
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def remove_teacher(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete teacher details for a user.
    """
    success = delete_teacher_detail(db=db, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher details not found for this user"
        )
    return {"message": "Teacher details deleted successfully"}
