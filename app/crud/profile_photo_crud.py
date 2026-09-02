import os
import uuid
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User

UPLOAD_DIR = os.path.join("uploads", "profile_images")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def _delete_file_from_disk(image_path: str):
    if not image_path:
        return
    rel_path = image_path.lstrip("/")
    abs_upload_dir = os.path.abspath(UPLOAD_DIR)
    target_abs_path = os.path.abspath(rel_path)

    # Security check: ensure target path is within UPLOAD_DIR
    if target_abs_path.startswith(abs_upload_dir) and os.path.exists(target_abs_path):
        try:
            os.remove(target_abs_path)
        except OSError:
            pass


def update_profile(db, user_id, first_name=None, last_name=None, file=None):

    try:

        user = db.query(User).filter(
            User.id == user_id
        ).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if first_name is not None:
            user.first_name = first_name

        if last_name is not None:
            user.last_name = last_name

        if file:

            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="No file selected"
                )

            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                )

            if not file.content_type or not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail="Only image files allowed"
                )

            contents = file.file.read()
            if len(contents) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail="File size exceeds maximum limit of 5MB"
                )

            os.makedirs(UPLOAD_DIR, exist_ok=True)

            unique_filename = f"user_{user_id}_{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)

            if user.profile_image:
                _delete_file_from_disk(user.profile_image)

            with open(file_path, "wb") as f:
                f.write(contents)

            db_path = f"/uploads/profile_images/{unique_filename}"
            user.profile_image = db_path

        db.commit()

        db.refresh(user)

        return {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "email": user.email,
            "profile_image": user.profile_image
        }

    except HTTPException:
        raise

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error"
        )

    except Exception as e:

        print("ERROR:", e)

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


def delete_profile_image(db, user_id):

    try:

        user = db.query(User).filter(
            User.id == user_id
        ).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if not user.profile_image:
            raise HTTPException(
                status_code=404,
                detail="No image found"
            )

        _delete_file_from_disk(user.profile_image)

        user.profile_image = None

        db.commit()

        return {
            "message": "Profile photo deleted successfully"
        }

    except HTTPException:
        raise

    except Exception as e:

        print("ERROR:", e)

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )