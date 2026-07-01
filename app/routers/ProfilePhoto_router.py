from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.ProfilePhoto_router import upload_profile_photo_service, delete_profile_photo_service

router = APIRouter(
    prefix="/api/User",
    tags=["Profile Photo"]
)


@router.post("/upload-profile-photo/{roleId}")
def upload_profile_photo(
    roleId: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    user = upload_profile_photo_service(
        db,
        roleId,
        file
    )

    return {
        "message": "Profile photo uploaded successfully",
        "data": user
    }


@router.delete("/delete-profile-photo/{roleId}")
def delete_profile_photo(
    roleId: int,
    db: Session = Depends(get_db)
):

    delete_profile_photo_service(
        db,
        roleId
    )

    return {
        "message": "Profile photo deleted successfully"
    }