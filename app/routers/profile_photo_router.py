from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.profile_photo_service import upload_profile_photo_service, delete_profile_photo_service

router = APIRouter(
    prefix="/profile-photo",
    tags=["Profile"]
)


@router.post("/upload/{userId}")
def upload_profile_photo(
    userId: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    user = upload_profile_photo_service(
        db,
        userId,
        file
    )

    return {
        "message": "Profile photo uploaded successfully",
        "data": user
    }


@router.put("/upload/{userId}")
def update_profile_photo(
    userId: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    user = upload_profile_photo_service(
        db,
        userId,
        file
    )

    return {
        "message": "Profile photo updated successfully",
        "data": user
    }


@router.delete("/delete-profile-photo/{userId}")
def delete_profile_photo(
    userId: int,
    db: Session = Depends(get_db)
):

    delete_profile_photo_service(
        db,
        userId
    )

    return {
        "message": "Profile photo deleted successfully"
    }