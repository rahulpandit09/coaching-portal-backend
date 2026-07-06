import os
import uuid
import shutil

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User


def update_profile(db, role_id, full_name=None, file=None):

    try:

        user = db.query(User).filter(
            User.role_id == role_id
        ).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if full_name:
            user.full_name = full_name

        if file:

            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="No file selected"
                )

            if not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail="Only image files allowed"
                )

            upload_dir = "uploads/profile"

            os.makedirs(upload_dir, exist_ok=True)

            if user.profile_image:

                old_path = user.profile_image.replace(
                    "/uploads/",
                    "uploads/"
                )

                if os.path.exists(old_path):
                    os.remove(old_path)

            ext = file.filename.split(".")[-1]

            filename = f"{uuid.uuid4()}.{ext}"

            file_path = os.path.join(
                upload_dir,
                filename
            )

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(
                    file.file,
                    buffer
                )

            user.profile_image = f"/uploads/profile/{filename}"

        db.commit()

        db.refresh(user)

        return {
            "id": user.id,
            "full_name": user.full_name,
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


def delete_profile_image(db, role_id):

    try:

        user = db.query(User).filter(
            User.role_id == role_id
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

        old_path = user.profile_image.replace(
            "/uploads/",
            "uploads/"
        )

        if os.path.exists(old_path):
            os.remove(old_path)

        user.profile_image = None

        db.commit()

        return True

    except Exception as e:

        print("ERROR:", e)

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )