import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import auth_router
from app.routers import profile_photo_router
from app.routers import sidebar_router
from fastapi.staticfiles import StaticFiles
# from app.routers.user_router import user_router

# This all table i am importing Temporarily import in main.py because i don't have router
from app.models.user import User
from app.models.role import Role
from app.models.menu import Menu
from app.models.role_menu import RoleMenu
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.submenu import SubMenu
from app.models.role_submenu import RoleSubMenu

#This is all Menu and subMenu all related Side bar 
from app.routers.menu_router import router as menu_router
from app.routers.submenu_router import router as submenu_router
from app.routers.permission_router import router as permission_router
from app.routers.role_router import router as role_router



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
app.include_router(profile_photo_router.router)
app.include_router(sidebar_router.router)
app.include_router(menu_router)
app.include_router(submenu_router)
app.include_router(permission_router)
app.include_router(role_router)
# app.include_router(user_router.route)

# Root Endpoint
@app.get("/")
def root():
    return {"message": "Coaching Portal Backend Running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}