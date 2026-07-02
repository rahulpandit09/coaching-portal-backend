from app.models.user import User


def get_user_by_id(db, user_id):
    user = db.query(User).filter(User.id == user_id).first()

    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "role": user.role.name if user.role else None
    }

