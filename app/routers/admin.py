from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.security import admin_required
from app.utils.hashing import hash_password
from app.schemas.admin_schema import CreateTeacherSchema, CreateStudentSchema

router = APIRouter(prefix="/admin", tags=["Admin"])


# ------------------------------
# CREATE TEACHER
# ------------------------------
@router.post("/create-teacher")
def create_teacher(
    data: CreateTeacherSchema,
    db: Session = Depends(get_db),
    admin=Depends(admin_required)
):

    # Check email uniqueness
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    # Check username uniqueness
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    new_teacher = User(
        full_name=data.name,
        username=data.username,
        email=data.email,
        password=hash_password(data.password),
        role="teacher"
    )

    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)

    return {
        "message": "Teacher created successfully",
        "teacher_id": new_teacher.id
    }


# ------------------------------
# CREATE STUDENT
# ------------------------------
@router.post("/create-student")
def create_student(
    data: CreateStudentSchema,
    db: Session = Depends(get_db),
    admin=Depends(admin_required)
):

    # Check email uniqueness
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    # Check username uniqueness
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    new_student = User(
        full_name=data.name,
        username=data.username,
        email=data.email,
        password=hash_password(data.password),
        role="student"
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return {
        "message": "Student created successfully",
        "student_id": new_student.id
    }
