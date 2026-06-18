from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course
from app.schemas.course_schema import CourseCreate, CourseResponse

router = APIRouter(
    prefix="/courses",
    tags=["Courses"]
)

@router.post("/", response_model=CourseResponse)
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    new_course = Course(**course.dict())
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course


@router.get("/", response_model=list[CourseResponse])
def get_courses(db: Session = Depends(get_db)):
    return db.query(Course).all()


















# from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session
# from app.database import get_db
# from app.models.course import Course
# from app.routers.course import CourseCreate, CourseResponse

# router = APIRouter(
#     prefix="/courses",
#     tags=["Courses"]
# )

# @router.post("/", response_model=CourseResponse)
# def create_course(course: CourseCreate, db: Session = Depends(get_db)):
#     new_course = Course(**course.dict())
#     db.add(new_course)
#     db.commit()
#     db.refresh(new_course)
#     return new_course


# @router.get("/", response_model=list[CourseResponse])
# def get_courses(db: Session = Depends(get_db)):
#     return db.query(Course).all()

















# # from fastapi import APIRouter, Depends
# # from sqlalchemy.orm import Session
# # from app.database import get_db
# # from app.models.course import CourseCreate, CourseResponse
# # # from app.schemas.course import CourseCreate, CourseResponse


# # router = APIRouter(
# #     prefix="/Courses",
# #     tags=["Course"]
# # )

# # @router.post("/",response_model=CourseResponse)
# # def create_course(course:CourseCreate, db: Session = Depends(get_db)):
# #     new_course = Course(**course.dict())
# #     db.add(new_course)
# #     db.commit()
# #     db.refresh(new_course)

# # @router.get("/",response_model=list[CourseResponse])
# # def get_courses(db: Session = Depends(get_db)):
# #     return db.query(Course).all()