from app.crud.user_crud import get_user_by_id

def get_user_profile(db, user_id):
    return(get_user_by_id(db, user_id))