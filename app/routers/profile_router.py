from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.crud.profile_crud import (
    update_profile,
    delete_profile_image
)

# your auth dependency
from app.core.security import get_current_user

router = APIRouter(
    prefix="/profile",
    tags=["Profile"]
)

@router.put("/")
def update_user_profile(
    full_name: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    user = update_profile(
        db,
        current_user,
        full_name,
        file
    )

    return {
        "message": "Updated successfully",
        "data": user
    }

@router.delete("/image")
def delete_image(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    delete_profile_image(db, current_user)

    return {
        "message": "Image deleted"
    }