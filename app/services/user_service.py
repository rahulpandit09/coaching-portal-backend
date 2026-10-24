from app.crud.user_crud import get_user_by_id, get_all_users


def get_user_profile(db, user_id):
    return get_user_by_id(db, user_id)


def get_all_user_service(db, current_user=None):
    return get_all_users(db)


def get_me_service(current_user):
    return current_user