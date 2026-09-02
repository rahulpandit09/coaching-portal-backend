import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
import app.models
from app.routers import auth_router
from app.routers import profile_photo_router
from app.routers import sidebar_router
from app.routers import user_router
#This is all Menu and subMenu all related Side bar 
from app.routers.menu_router import router as menu_router
from app.routers.submenu_router import router as submenu_router
from app.routers.permission_router import router as permission_router
from app.routers.role_router import router as role_router
from app.routers.userManagement import (
    user_management_router,
    student_management_router,
    teacher_management_router,
    parent_management_router,
)

app = FastAPI(
    title="Coaching Portal API'S",
    openapi_version="3.0.3"
)

# CORS Configuration
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")

if allowed_origins_str:
    allowed_origins = [
        origin.strip()
        for origin in allowed_origins_str.split(",")
        if origin.strip()
    ]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

# If allowed_origins contains "*", allow_credentials MUST be False.
allow_credentials = True
if "*" in allowed_origins:
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists and mount static files
os.makedirs("uploads/profile_images", exist_ok=True)
os.makedirs("uploads/aadhaar_cards", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Create Tables and ensure schema updates on Startup
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    try:
        from sqlalchemy import inspect, text
        with engine.connect() as conn:
            inspector = inspect(engine)
            if "users" in inspector.get_table_names():
                user_cols = [c["name"] for c in inspector.get_columns("users")]
                if "aadhaar_card" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN aadhaar_card VARCHAR(500)"))
                    conn.commit()
    except Exception as e:
        print(f"Startup migration notice: {e}")

# Include Routers
app.include_router(auth_router.router)
app.include_router(profile_photo_router.router)
app.include_router(sidebar_router.router)
app.include_router(menu_router)
app.include_router(submenu_router)
app.include_router(permission_router)
app.include_router(role_router)
app.include_router(user_router.router)
app.include_router(user_management_router)
app.include_router(student_management_router)
app.include_router(teacher_management_router)
app.include_router(parent_management_router)

# Root Endpoint
@app.get("/")
def root():
    return {"message": "Coaching Portal Backend Running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}