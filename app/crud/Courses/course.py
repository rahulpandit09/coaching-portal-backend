from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from app.models.Courses.course import Course
from app.schemas.Courses.course import CourseCreate, CourseUpdate, CourseStatusUpdate


# ─── Private Helper ───────────────────────────────────────────────────────────

def _generate_course_id(db: Session) -> str:
    """Auto-generates course_id like CRS-001, CRS-002, ..."""
    last = db.query(Course).order_by(Course.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    return f"CRS-{str(next_num).zfill(3)}"


# ─── READ ───────────────

def get_all_courses(
    db:      Session,
    search:  Optional[str] = "",
    subject: Optional[str] = "",
    batch:   Optional[str] = "",
    status:  Optional[str] = "",
):
    """
    Returns all courses.
    Supports optional filters: search (name/id/teacher), subject, batch, status.
    """
    query = db.query(Course)

    if search:
        query = query.filter(
            or_(
                Course.name.ilike(f"%{search}%"),
                Course.course_id.ilike(f"%{search}%"),
                Course.teacher_name.ilike(f"%{search}%"),
            )
        )

    if subject:
        query = query.filter(Course.subject == subject)

    if batch:
        query = query.filter(Course.batches.any(batch))   # PostgreSQL ARRAY contains

    if status:
        query = query.filter(Course.status == status)

    return query.order_by(Course.id.asc()).all()


def get_course_by_id(db: Session, course_id: int):
    """Returns a single course by primary key id."""
    return db.query(Course).filter(Course.id == course_id).first()


# ─── CREATE ───────────────────────────────────────────────────────────────────

def create_course(db: Session, data: CourseCreate, user):
    """
    Creates a new course.
    Auto-generates course_id (CRS-001 etc.) and sets students = 0.
    """
    new_course = Course(
        **data.model_dump(),
        course_id=_generate_course_id(db),
        students=0,
    )

    new_course = Course(
    **data.model_dump(),
    course_id=_generate_course_id(db),
    students=0,

    created_by=user.id,
    created_by_name=user.name,
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course




# ─── UPDATE ───────────────────────────────────────────────────────────────────

def update_course(db: Session, course_id: int, data: CourseUpdate):
    """
    Updates all fields of a course (full update).
    Returns None if course not found.
    """
    course = get_course_by_id(db, course_id)
    if not course:
        return None

    for field, value in data.model_dump().items():
        setattr(course, field, value)

    db.commit()
    db.refresh(course)
    return course


def update_course_status(db: Session, course_id: int, data: CourseStatusUpdate):
    """
    Updates only the status field (Active / Inactive toggle).
    Returns None if course not found.
    """
    course = get_course_by_id(db, course_id)
    if not course:
        return None

    course.status = data.status
    db.commit()
    db.refresh(course)
    return course


# ─── DELETE ───────────────────────────────────────────────────────────────────

def delete_course(db: Session, course_id: int):
    """
    Deletes a course permanently.
    Returns True on success, False if not found.
    """
    course = get_course_by_id(db, course_id)
    if not course:
        return False

    db.delete(course)
    db.commit()
    return True
