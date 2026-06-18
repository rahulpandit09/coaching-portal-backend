from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.Teacher.faculty_module import (
    FacultyTeacher,
    FacultyCourse,
    FacultyBatch,
    FacultyAssignment,
    FacultyStudent
)


# GET ALL TEACHERS
def get_teachers(db: Session):

    results = (
        db.query(
            FacultyTeacher.id,
            FacultyTeacher.name,
            FacultyTeacher.email,
            FacultyTeacher.phone,
            FacultyTeacher.status,
            FacultyCourse.title.label("course"),
            FacultyBatch.name.label("batch"),
            func.count(FacultyStudent.id).label("students")
        )
        .outerjoin(FacultyAssignment, FacultyTeacher.id == FacultyAssignment.teacher_id)
        .outerjoin(FacultyCourse, FacultyAssignment.course_id == FacultyCourse.id)
        .outerjoin(FacultyBatch, FacultyAssignment.batch_id == FacultyBatch.id)
        .outerjoin(FacultyStudent, FacultyBatch.id == FacultyStudent.batch_id)
        .group_by(
            FacultyTeacher.id,
            FacultyTeacher.name,
            FacultyTeacher.email,
            FacultyTeacher.phone,
            FacultyTeacher.status,
            FacultyCourse.title,
            FacultyBatch.name
        )
        .all()
    )

    teachers = []

    for r in results:
        teachers.append({
            "id": r.id,
            "name": r.name,
            "email": r.email,
            "phone": r.phone,
            "status": r.status,
            "course": r.course,
            "batch": r.batch,
            "students": r.students
        })

    return teachers



# GET SINGLE TEACHER
def get_teacher(db: Session, teacher_id: int):

    r = (
        db.query(
            FacultyTeacher.id,
            FacultyTeacher.name,
            FacultyTeacher.email,
            FacultyTeacher.phone,
            FacultyTeacher.status,
            FacultyCourse.title.label("course"),
            FacultyBatch.name.label("batch"),
            func.count(FacultyStudent.id).label("students")
        )
        .outerjoin(FacultyAssignment, FacultyTeacher.id == FacultyAssignment.teacher_id)
        .outerjoin(FacultyCourse, FacultyAssignment.course_id == FacultyCourse.id)
        .outerjoin(FacultyBatch, FacultyAssignment.batch_id == FacultyBatch.id)
        .outerjoin(FacultyStudent, FacultyBatch.id == FacultyStudent.batch_id)
        .filter(FacultyTeacher.id == teacher_id)
        .group_by(
            FacultyTeacher.id,
            FacultyTeacher.name,
            FacultyTeacher.email,
            FacultyTeacher.phone,
            FacultyTeacher.status,
            FacultyCourse.title,
            FacultyBatch.name
        )
        .first()
    )

    if not r:
        return None

    return {
        "id": r.id,
        "name": r.name,
        "email": r.email,
        "phone": r.phone,
        "status": r.status,
        "course": r.course,
        "batch": r.batch,
        "students": r.students
    }



# GET COURSES
def get_courses(db: Session):

    courses = db.query(FacultyCourse).all()

    return [
        {
            "id": c.id,
            "title": c.title
        }
        for c in courses
    ]



# GET BATCHES BY COURSE
def get_batches(db: Session, course_id: int):

    batches = db.query(FacultyBatch).filter(
        FacultyBatch.course_id == course_id
    ).all()

    return [
        {
            "id": b.id,
            "name": b.name,
            "course_id": b.course_id
        }
        for b in batches
    ]


# ASSIGN TEACHER
def assign_teacher(db: Session, teacher_id: int, course_id: int, batch_id: int):

    assignment = FacultyAssignment(
        teacher_id=teacher_id,
        course_id=course_id,
        batch_id=batch_id
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return {
        "message": "Teacher assigned successfully",
        "id": assignment.id,
        "teacher_id": assignment.teacher_id,
        "course_id": assignment.course_id,
        "batch_id": assignment.batch_id
    }