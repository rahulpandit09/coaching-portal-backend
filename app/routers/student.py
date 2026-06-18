from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.schemas.enrollment_schema import EnrollRequest

router = APIRouter(
    prefix="/student",
    tags=["Student"]
)

# --------------------------------------------------
# 1️⃣ VIEW ALL ACTIVE COURSES
# --------------------------------------------------
@router.get("/courses")
def view_courses(db: Session = Depends(get_db)):
    return db.query(Course).filter(Course.is_active == True).all()


# --------------------------------------------------
# 2️⃣ ENROLL IN A COURSE
# --------------------------------------------------
@router.post("/enroll")
def enroll_course(
    data: EnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can enroll")

    course = db.query(Course).filter(
        Course.id == data.course_id,
        Course.is_active == True
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    exists = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == data.course_id
    ).first()

    if exists:
        raise HTTPException(status_code=400, detail="Already enrolled")

    enrollment = Enrollment(
        user_id=current_user.id,
        course_id=data.course_id
    )

    db.add(enrollment)
    db.commit()

    return {"message": "Enrolled successfully"}


# --------------------------------------------------
# 3️⃣ VIEW MY ENROLLED COURSES
# --------------------------------------------------
@router.get("/my-courses")
def my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students allowed")

    courses = (
        db.query(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == current_user.id)
        .all()
    )

    return courses


# --------------------------------------------------
# 4️⃣ STUDENT PROFILE
# --------------------------------------------------
@router.get("/me")
def student_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role
    }
