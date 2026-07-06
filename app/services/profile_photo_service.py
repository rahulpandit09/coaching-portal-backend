from app.crud.profile_photo_crud import update_profile, delete_profile_image


def upload_profile_photo_service(db, role_id, file):
    return update_profile(db, role_id, file=file)


def delete_profile_photo_service(db, role_id):
    return delete_profile_image(db, role_id)