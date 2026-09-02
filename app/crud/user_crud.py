from app.models.user import User


def get_user_by_id(db, user_id):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return None

    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "profile_image": user.profile_image,
        "role": user.role.name if user.role else None
    }

