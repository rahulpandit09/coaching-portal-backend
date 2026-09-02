from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas.userManagement.user import (
    UserCreate,
    UserUpdate,
    UserOut,
    UserKPICardResponse
)
from app.crud.userManagement.user import (
    get_user_by_id,
    get_user_by_email,
    get_user_by_username,
    get_users,
    get_total_users_count,
    get_user_kpi_stats,
    create_user_with_details,
    update_user_with_details,
    delete_user,
    upload_user_aadhaar_card,
    save_aadhaar_file
)

router = APIRouter(
    prefix="/user-management/users",
    tags=["User Management"]
)


@router.get("/kpi", response_model=UserKPICardResponse)
def get_user_kpi_cards(
    db: Session = Depends(get_db)
):
    """
    Get KPI card counts:
    - Total Users
    - Students
    - Teachers
    - Parents
    """
    return get_user_kpi_stats(db=db)


@router.get("/", response_model=List[UserOut])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    role_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get all users with optional filtering by role_id, search term, and pagination.
    """
    users = get_users(
        db=db,
        skip=skip,
        limit=limit,
        role_id=role_id,
        search=search
    )
    return users


@router.get("/count")
def count_users(
    role_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get total users count for pagination calculations.
    """
    total = get_total_users_count(db=db, role_id=role_id, search=search)
    return {"total": total}


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific user by ID along with their role-specific details.
    """
    user = get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user with optional role-specific details (Student, Teacher, Parent).
    """
    # Check for duplicate email
    if get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check for duplicate username
    if get_user_by_username(db, user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    try:
        user = create_user_with_details(db=db, user_in=user_in)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user information and their role-specific details.
    """
    existing_user = get_user_by_id(db, user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Validate unique email if being changed
    if user_in.email and user_in.email != existing_user.email:
        if get_user_by_email(db, user_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )

    # Validate unique username if being changed
    if user_in.username and user_in.username != existing_user.username:
        if get_user_by_username(db, user_in.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    try:
        updated_user = update_user_with_details(db=db, user_id=user_id, user_in=user_in)
        return updated_user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def remove_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a user and cascade delete their role details.
    """
    success = delete_user(db=db, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "User deleted successfully", "user_id": user_id}


@router.post("/upload-aadhaar-document")
def upload_aadhaar_document(
    file: UploadFile = File(...)
):
    """
    Upload Aadhaar card document (Image or PDF) and return its stored URL.
    Useful when creating a new user or attaching to form data.
    """
    file_url = save_aadhaar_file(file)
    return {
        "message": "Aadhaar document uploaded successfully",
        "aadhaar_card": file_url,
        "url": file_url
    }


@router.post("/{user_id}/upload-aadhaar", response_model=UserOut)
def upload_aadhaar_for_user(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and attach Aadhaar card document directly to an existing user.
    """
    user = upload_user_aadhaar_card(db=db, user_id=user_id, file=file)
    return user

