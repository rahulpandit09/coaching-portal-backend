from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import auth, course, student, admin

from app.routers.Student import RegistrationForm
from app.routers.studentAdmin import addStudent
from app.routers.studentAdmin import admin_dashboard
from app.routers.studentAdmin import adminDashboard_router
from app.models import user, course as course_model, lecture, enrollment, test, result
from app.models.admin.addStudent import AdminStudent
from app.models.admin.fee import Fee
from app.routers.studentAdmin import admin_notification
from app.routers.Teacher import faculty_router
from app.routers.Courses.course import router as course_router
from app.routers.Batchs import batch



# app = FastAPI(title="Coaching Portal API")
app = FastAPI(
    title="Coaching Portal API",
    openapi_version="3.0.3"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# #this is a production leve 
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # for learning
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )




# # Create Tables on Startup
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# Include Routers
app.include_router(auth.router)
app.include_router(course.router)
app.include_router(student.router)
app.include_router(RegistrationForm.router)
app.include_router(admin.router)
app.include_router(addStudent.router)
app.include_router(admin_dashboard.router)
app.include_router(admin_notification.router)
app.include_router(adminDashboard_router.router)
app.include_router(faculty_router.router)
app.include_router(course_router)  
app.include_router(batch.router)



# Root Endpoint
@app.get("/")
def root():
    return {"message": "Coaching Portal Backend Running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}