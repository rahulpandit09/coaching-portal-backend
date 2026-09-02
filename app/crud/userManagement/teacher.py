from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from app.models.userManagement.teacher import TeacherDetail
from app.models.user import User
from app.schemas.userManagement.teacher import TeacherDetailCreate, TeacherDetailUpdate


def get_teacher_by_id(db: Session, teacher_id: int) -> Optional[TeacherDetail]:
    return db.query(TeacherDetail).filter(TeacherDetail.id == teacher_id).first()


def get_teacher_by_user_id(db: Session, user_id: int) -> Optional[TeacherDetail]:
    return db.query(TeacherDetail).filter(TeacherDetail.user_id == user_id).first()


def get_teacher_by_employee_id(db: Session, employee_id: str) -> Optional[TeacherDetail]:
    return db.query(TeacherDetail).filter(TeacherDetail.employee_id == employee_id).first()


def get_all_teachers(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
) -> List[TeacherDetail]:
    query = db.query(TeacherDetail).join(User, TeacherDetail.user_id == User.id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_filter),
                User.last_name.ilike(search_filter),
                User.email.ilike(search_filter),
                TeacherDetail.employee_id.ilike(search_filter),
                TeacherDetail.specialization.ilike(search_filter),
                TeacherDetail.qualification.ilike(search_filter)
            )
        )
    return query.offset(skip).limit(limit).all()


def create_teacher_detail(
    db: Session,
    user_id: int,
    teacher_data: TeacherDetailCreate
) -> TeacherDetail:
    db_teacher = TeacherDetail(
        user_id=user_id,
        **teacher_data.model_dump(exclude_unset=True)
    )
    db.add(db_teacher)
    db.commit()
    db.refresh(db_teacher)
    return db_teacher


def update_teacher_detail(
    db: Session,
    user_id: int,
    teacher_data: TeacherDetailUpdate
) -> Optional[TeacherDetail]:
    db_teacher = get_teacher_by_user_id(db, user_id)
    if not db_teacher:
        return None

    update_data = teacher_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_teacher, field, value)

    db.commit()
    db.refresh(db_teacher)
    return db_teacher


def delete_teacher_detail(db: Session, user_id: int) -> bool:
    db_teacher = get_teacher_by_user_id(db, user_id)
    if not db_teacher:
        return False

    db.delete(db_teacher)
    db.commit()
    return True
