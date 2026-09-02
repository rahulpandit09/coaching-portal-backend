from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

from .student import StudentDetailCreate, StudentDetailUpdate, StudentDetailOut
from .teacher import TeacherDetailCreate, TeacherDetailUpdate, TeacherDetailOut
from .parent import ParentDetailCreate, ParentDetailUpdate, ParentDetailOut


class UserBase(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    role_id: int


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    role_id: int
    profile_image: Optional[str] = None
    aadhaar_card: Optional[str] = None

    # Role specific details (optional during create depending on role)
    student_details: Optional[StudentDetailCreate] = None
    teacher_details: Optional[TeacherDetailCreate] = None
    parent_details: Optional[ParentDetailCreate] = None


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=72)
    role_id: Optional[int] = None
    profile_image: Optional[str] = None
    aadhaar_card: Optional[str] = None

    # Role specific details updates
    student_details: Optional[StudentDetailUpdate] = None
    teacher_details: Optional[TeacherDetailUpdate] = None
    parent_details: Optional[ParentDetailUpdate] = None


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    username: Optional[str] = None
    email: EmailStr
    role_id: Optional[int] = None
    profile_image: Optional[str] = None
    aadhaar_card: Optional[str] = None
    last_login: Optional[datetime] = None

    # Nested detail models
    student_details: Optional[StudentDetailOut] = None
    teacher_details: Optional[TeacherDetailOut] = None
    parent_details: Optional[ParentDetailOut] = None

    class Config:
        from_attributes = True


class UserKPICardResponse(BaseModel):
    total_users: int = 0
    students: int = 0
    teachers: int = 0
    parents: int = 0
    total_students: int = 0
    total_teachers: int = 0
    total_parents: int = 0
