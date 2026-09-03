from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Any
from datetime import datetime

from app.schemas.userManagement.student import StudentDetailOut
from app.schemas.userManagement.teacher import TeacherDetailOut
from app.schemas.userManagement.parent import ParentDetailOut

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    role_name: Optional[str] = "Student"


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    username: Optional[str] = None
    email: EmailStr
    profile_image: Optional[str] = None
    aadhaar_card: Optional[str] = None
    role_id: Optional[int] = None
    role: Optional[str] = None
    last_login: Optional[datetime] = None

    # Role specific details
    student_details: Optional[StudentDetailOut] = None
    teacher_details: Optional[TeacherDetailOut] = None
    parent_details: Optional[ParentDetailOut] = None

    @field_validator('role', mode='before')
    @classmethod
    def extract_role_name(cls, v: Any) -> Optional[str]:
        if hasattr(v, 'name'):
            return v.name
        if isinstance(v, str):
            return v
        return None

    class Config:
        from_attributes = True



