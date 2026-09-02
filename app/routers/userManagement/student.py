from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas.userManagement.student import (
    StudentDetailCreate,
    StudentDetailUpdate,
    StudentDetailOut
)
from app.crud.userManagement.student import (
    get_student_by_id,
    get_student_by_user_id,
    get_all_students,
    create_student_detail,
    update_student_detail,
    delete_student_detail
)

router = APIRouter(
    prefix="/user-management/students",
    tags=["Student Tab"]
)


@router.get("/", response_model=List[StudentDetailOut])
def list_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get all student details with optional search and pagination.
    """
    return get_all_students(db=db, skip=skip, limit=limit, search=search)


@router.get("/{user_id}", response_model=StudentDetailOut)
def get_student(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get student detail by user ID.
    """
    student = get_student_by_user_id(db=db, user_id=user_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student details not found for this user"
        )
    return student


@router.post("/{user_id}", response_model=StudentDetailOut, status_code=status.HTTP_201_CREATED)
def create_student(
    user_id: int,
    student_data: StudentDetailCreate,
    db: Session = Depends(get_db)
):
    """
    Create student details for a user.
    """
    existing = get_student_by_user_id(db=db, user_id=user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student details already exist for this user"
        )
    return create_student_detail(db=db, user_id=user_id, student_data=student_data)


@router.put("/{user_id}", response_model=StudentDetailOut)
def update_student(
    user_id: int,
    student_data: StudentDetailUpdate,
    db: Session = Depends(get_db)
):
    """
    Update student details for a user.
    """
    updated = update_student_detail(db=db, user_id=user_id, student_data=student_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student details not found for this user"
        )
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def remove_student(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete student details for a user.
    """
    success = delete_student_detail(db=db, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student details not found for this user"
        )
    return {"message": "Student details deleted successfully"}
