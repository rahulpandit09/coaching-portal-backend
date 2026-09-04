import os
import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List, Dict

from app.models.user import User
from app.models.role import Role
from app.models.userManagement.student import StudentDetail
from app.models.userManagement.teacher import TeacherDetail
from app.models.userManagement.parent import ParentDetail
from app.schemas.userManagement.user import UserCreate, UserUpdate
from app.utils.hashing import hash_password


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    role_id: Optional[int] = None,
    search: Optional[str] = None
) -> List[User]:
    query = db.query(User)

    if role_id is not None:
        query = query.filter(User.role_id == role_id)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_filter),
                User.last_name.ilike(search_filter),
                User.username.ilike(search_filter),
                User.email.ilike(search_filter),
                User.phone_number.ilike(search_filter)
            )
        )

    return query.offset(skip).limit(limit).all()


def get_total_users_count(
    db: Session,
    role_id: Optional[int] = None,
    search: Optional[str] = None
) -> int:
    query = db.query(User)

    if role_id is not None:
        query = query.filter(User.role_id == role_id)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_filter),
                User.last_name.ilike(search_filter),
                User.username.ilike(search_filter),
                User.email.ilike(search_filter),
                User.phone_number.ilike(search_filter)
            )
        )

    return query.count()


def get_user_kpi_stats(db: Session) -> Dict[str, int]:
    """
    Get user counts for KPI cards:
    - total_users: All users in the database
    - students: Users with role 'student'
    - teachers: Users with role 'teacher'
    - parents: Users with role 'parent'
    """
    total_users = db.query(func.count(User.id)).scalar() or 0

    students_count = db.query(func.count(User.id)).join(
        Role, User.role_id == Role.id
    ).filter(
        func.lower(Role.name).like("%student%")
    ).scalar() or 0

    teachers_count = db.query(func.count(User.id)).join(
        Role, User.role_id == Role.id
    ).filter(
        func.lower(Role.name).like("%teacher%")
    ).scalar() or 0

    parents_count = db.query(func.count(User.id)).join(
        Role, User.role_id == Role.id
    ).filter(
        func.lower(Role.name).like("%parent%")
    ).scalar() or 0

    return {
        "total_users": total_users,
        "students": students_count,
        "teachers": teachers_count,
        "parents": parents_count,
        "total_students": students_count,
        "total_teachers": teachers_count,
        "total_parents": parents_count
    }


def create_user_with_details(db: Session, user_in: UserCreate) -> User:
    # 1. Prepare user data and hash password
    user_dict = {
        "first_name": user_in.first_name,
        "last_name": user_in.last_name,
        "username": user_in.username,
        "email": user_in.email,
        "phone_number": user_in.phone_number,
        "password": hash_password(user_in.password),
        "role_id": user_in.role_id,
        "profile_image": user_in.profile_image,
        "aadhaar_card": user_in.aadhaar_card
    }

    db_user = User(**user_dict)
    db.add(db_user)
    db.flush()  # Populates db_user.id for foreign key references

    # 2. Add role-specific details if provided
    if user_in.student_details:
        student_data = user_in.student_details.model_dump(exclude_unset=True)
        db_student = StudentDetail(user_id=db_user.id, **student_data)
        db.add(db_student)

    if user_in.teacher_details:
        teacher_data = user_in.teacher_details.model_dump(exclude_unset=True)
        db_teacher = TeacherDetail(user_id=db_user.id, **teacher_data)
        db.add(db_teacher)

    if user_in.parent_details:
        parent_data = user_in.parent_details.model_dump(exclude_unset=True)
        db_parent = ParentDetail(user_id=db_user.id, **parent_data)
        db.add(db_parent)

    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_with_details(
    db: Session,
    user_id: int,
    user_in: UserUpdate
) -> Optional[User]:
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None

    # Update basic user fields
    user_data = user_in.model_dump(
        exclude_unset=True,
        exclude={"student_details", "teacher_details", "parent_details", "password"}
    )
    for field, value in user_data.items():
        setattr(db_user, field, value)

    # Update password if provided
    if user_in.password:
        db_user.password = hash_password(user_in.password)

    # Update Student Details
    if user_in.student_details is not None:
        student_update_data = user_in.student_details.model_dump(exclude_unset=True)
        if db_user.student_details:
            for field, value in student_update_data.items():
                setattr(db_user.student_details, field, value)
        else:
            db_student = StudentDetail(user_id=db_user.id, **student_update_data)
            db.add(db_student)

    # Update Teacher Details
    if user_in.teacher_details is not None:
        teacher_update_data = user_in.teacher_details.model_dump(exclude_unset=True)
        if db_user.teacher_details:
            for field, value in teacher_update_data.items():
                setattr(db_user.teacher_details, field, value)
        else:
            db_teacher = TeacherDetail(user_id=db_user.id, **teacher_update_data)
            db.add(db_teacher)

    # Update Parent Details
    if user_in.parent_details is not None:
        parent_update_data = user_in.parent_details.model_dump(exclude_unset=True)
        if db_user.parent_details:
            for field, value in parent_update_data.items():
                setattr(db_user.parent_details, field, value)
        else:
            db_parent = ParentDetail(user_id=db_user.id, **parent_update_data)
            db.add(db_parent)

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return False

    db.delete(db_user)
    db.commit()
    return True


UPLOAD_AADHAAR_DIR = os.path.join("uploads", "aadhaar_cards")
ALLOWED_DOC_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
MAX_DOC_SIZE = 10 * 1024 * 1024  # 10MB


def save_aadhaar_file(file) -> str:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_DOC_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_DOC_EXTENSIONS))}"
        )

    contents = file.file.read()
    if len(contents) > MAX_DOC_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds maximum limit of 10MB")

    os.makedirs(UPLOAD_AADHAAR_DIR, exist_ok=True)
    unique_filename = f"aadhaar_{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_AADHAAR_DIR, unique_filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    return f"/uploads/aadhaar_cards/{unique_filename}"


def upload_user_aadhaar_card(db: Session, user_id: int, file) -> User:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    file_url = save_aadhaar_file(file)

    # Remove old file if present
    if user.aadhaar_card:
        old_path = user.aadhaar_card.lstrip("/")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    user.aadhaar_card = file_url
    db.commit()
    db.refresh(user)
    return user

