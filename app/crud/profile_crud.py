import os
import uuid
import shutil
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from app.models.user import User

def update_profile(db, current_user, full_name=None, file=None):

    try:

        # check user
        user = db.query(User).filter(
            User.id == current_user.id
        ).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # update text field
        if full_name:
            user.full_name = full_name

        # handle image
        if file:

            # empty filename check
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="No file selected"
                )

            # validate image type
            if not file.content_type:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file"
                )

            if not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail="Only image files allowed"
                )

            # create folder if missing
            upload_dir = "uploads/profile"

            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            # delete old image
            if user.profile_image:

                try:
                    if os.path.exists(user.profile_image):
                        os.remove(user.profile_image)

                except PermissionError:
                    raise HTTPException(
                        status_code=500,
                        detail="Cannot delete old image"
                    )

                except OSError:
                    raise HTTPException(
                        status_code=500,
                        detail="Old image delete failed"
                    )

            # save new image
            ext = file.filename.split(".")[-1]

            filename = f"{uuid.uuid4()}.{ext}"

            file_path = os.path.join(
                upload_dir,
                filename
            )

            try:
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(
                        file.file,
                        buffer
                    )

            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="Image upload failed"
                )

            user.profile_image = file_path

        # save db
        db.commit()

        db.refresh(user)

        return user

    except HTTPException:
        raise

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error"
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unexpected error occurred"
        )


def delete_profile_image(db, current_user):

    try:

        user = db.query(User).filter(
            User.id == current_user.id
        ).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if not user.profile_image:
            raise HTTPException(
                status_code=404,
                detail="No profile image found"
            )

        # delete physical file
        try:

            if os.path.exists(
                user.profile_image
            ):
                os.remove(
                    user.profile_image
                )

        except PermissionError:
            raise HTTPException(
                status_code=500,
                detail="File permission denied"
            )

        except OSError:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete image"
            )

        # remove db entry
        user.profile_image = None

        db.commit()

        return True

    except HTTPException:
        raise

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error"
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unexpected error occurred"
        )

    try:

        # check user
        user = db.query(User).filter(
            User.id == current_user.id
        ).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # update text field
        if full_name:
            user.full_name = full_name

        # handle image
        if file:

            # empty filename check
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="No file selected"
                )

            # validate image type
            if not file.content_type:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file"
                )

            if not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail="Only image files allowed"
                )

            # create folder if missing
            upload_dir = "uploads/profile"

            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            # delete old image
            if user.profile_image:

                try:
                    if os.path.exists(user.profile_image):
                        os.remove(user.profile_image)

                except PermissionError:
                    raise HTTPException(
                        status_code=500,
                        detail="Cannot delete old image"
                    )

                except OSError:
                    raise HTTPException(
                        status_code=500,
                        detail="Old image delete failed"
                    )

            # save new image
            ext = file.filename.split(".")[-1]

            filename = f"{uuid.uuid4()}.{ext}"

            file_path = os.path.join(
                upload_dir,
                filename
            )

            try:
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(
                        file.file,
                        buffer
                    )

            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="Image upload failed"
                )

            user.profile_image = file_path

        # save db
        db.commit()

        db.refresh(user)

        return user

    except HTTPException:
        raise

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error"
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unexpected error occurred"
        )

    user = db.query(User).filter(
        User.id == current_user.id
    ).first()

    if user.profile_image:

        if os.path.exists(user.profile_image):
            os.remove(user.profile_image)

        user.profile_image = None
        db.commit()

    return True