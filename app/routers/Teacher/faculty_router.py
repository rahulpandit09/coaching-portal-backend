from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.crud.Teacher import faculty_crud
from app.schemas.Teacher.faculty_schema import FacultyAssignSchema
from app.models.Teacher.faculty_module import FacultyTeacher

router = APIRouter(
    prefix="/admin",
    tags=["Faculty Management"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET ALL TEACHERS
@router.get("/faculty-teachers")
def get_teachers(db: Session = Depends(get_db)):
    return faculty_crud.get_teachers(db)


# GET SINGLE TEACHER
@router.get("/faculty-teacher/{teacher_id}")
def get_teacher(teacher_id: int, db: Session = Depends(get_db)):
    return faculty_crud.get_teacher(db, teacher_id)


# GET COURSES
@router.get("/faculty-courses")
def get_courses(db: Session = Depends(get_db)):
    return faculty_crud.get_courses(db)


# GET BATCHES
@router.get("/faculty-batches/{course_id}")
def get_batches(course_id: int, db: Session = Depends(get_db)):
    return faculty_crud.get_batches(db, course_id)


# ASSIGN TEACHER
@router.post("/faculty-assign")
def assign_teacher(data: FacultyAssignSchema, db: Session = Depends(get_db)):
    return faculty_crud.assign_teacher(
        db,
        data.teacher_id,
        data.course_id,
        data.batch_id
    )

# All Teacher List
@router.get("/faculty-teachers-list")
def get_teachers_list(db: Session = Depends(get_db)):
    return db.query(FacultyTeacher).all()