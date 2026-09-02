from app.crud.profile_photo_crud import update_profile, delete_profile_image


def upload_profile_photo_service(db, user_id, file):
    return update_profile(db, user_id, file=file)


def delete_profile_photo_service(db, user_id):
    return delete_profile_image(db, user_id)