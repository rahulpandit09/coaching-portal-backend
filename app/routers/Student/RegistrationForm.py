from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import SessionLocal
from app.models.Student.RegistrationForm import RegistrationStudent
from app.schemas.Student.RegistrationForm import StudentCreate, StudentResponse
from app.dependencies.auth import get_current_user


router = APIRouter(prefix="/student-registration", tags=["Student Registration"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ✅ REGISTER (Only Student Role)
@router.post("/register")
def register_student(
    student: StudentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can register")

    # Prevent duplicate registration
    existing_student = db.query(RegistrationStudent).filter(
        RegistrationStudent.user_id == current_user.id
    ).first()

    if existing_student:
        raise HTTPException(status_code=400, detail="Already registered")

    new_student = RegistrationStudent(
        **student.model_dump(),
        user_id=current_user.id
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return {
        "message": "Student Registered Successfully",
        "id": new_student.id
    }


#  STUDENT CAN VIEW ONLY THEIR OWN DATA
@router.get("/me", response_model=StudentResponse)
def get_my_student_data(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    student = db.query(RegistrationStudent).filter(
        RegistrationStudent.user_id == current_user.id
    ).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not registered")

    return student


#  ADMIN & TEACHER CAN VIEW ALL STUDENTS
def require_admin_or_teacher(current_user = Depends(get_current_user)):
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


@router.get("/", response_model=List[StudentResponse])
def get_all_students(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin_or_teacher)
):
    return db.query(RegistrationStudent).all()
