import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import auth_router
from app.routers import ProfilePhoto_router
from app.routers import sidebar_router
from fastapi.staticfiles import StaticFiles
# from app.routers.user_router import user_router


# This all table i am importing Temporarily import in main.py because i don't have router
from app.models.user import User
from app.models.role import Role
from app.models.menu import Menu
from app.models.role_menu import RoleMenu

app = FastAPI(
    title="Coaching Portal API'S",
    openapi_version="3.0.3"
)

app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
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

# Create Tables on Startup
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# Include Routers
app.include_router(auth_router.router)
app.include_router(ProfilePhoto_router.router)
app.include_router(sidebar_router.router)
# app.include_router(user_router.route)

# Root Endpoint
@app.get("/")
def root():
    return {"message": "Coaching Portal Backend Running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}