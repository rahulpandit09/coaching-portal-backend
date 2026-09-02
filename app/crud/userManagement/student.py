from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from app.models.userManagement.student import StudentDetail
from app.models.user import User
from app.schemas.userManagement.student import StudentDetailCreate, StudentDetailUpdate


def get_student_by_id(db: Session, student_id: int) -> Optional[StudentDetail]:
    return db.query(StudentDetail).filter(StudentDetail.id == student_id).first()


def get_student_by_user_id(db: Session, user_id: int) -> Optional[StudentDetail]:
    return db.query(StudentDetail).filter(StudentDetail.user_id == user_id).first()


def get_student_by_student_code(db: Session, student_code: str) -> Optional[StudentDetail]:
    return db.query(StudentDetail).filter(StudentDetail.student_id == student_code).first()


def get_all_students(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
) -> List[StudentDetail]:
    query = db.query(StudentDetail).join(User, StudentDetail.user_id == User.id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_filter),
                User.last_name.ilike(search_filter),
                User.email.ilike(search_filter),
                StudentDetail.student_id.ilike(search_filter),
                StudentDetail.school_name.ilike(search_filter),
                StudentDetail.class_name.ilike(search_filter)
            )
        )
    return query.offset(skip).limit(limit).all()


def create_student_detail(
    db: Session,
    user_id: int,
    student_data: StudentDetailCreate
) -> StudentDetail:
    db_student = StudentDetail(
        user_id=user_id,
        **student_data.model_dump(exclude_unset=True)
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


def update_student_detail(
    db: Session,
    user_id: int,
    student_data: StudentDetailUpdate
) -> Optional[StudentDetail]:
    db_student = get_student_by_user_id(db, user_id)
    if not db_student:
        return None

    update_data = student_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_student, field, value)

    db.commit()
    db.refresh(db_student)
    return db_student


def delete_student_detail(db: Session, user_id: int) -> bool:
    db_student = get_student_by_user_id(db, user_id)
    if not db_student:
        return False

    db.delete(db_student)
    db.commit()
    return True
