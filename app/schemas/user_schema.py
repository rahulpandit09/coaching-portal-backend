from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
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
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    password: str = Field(min_length=6, max_length=72)
    role_name: Optional[str] = "Student"


class UserOut(BaseModel):
    userId: int = Field(validation_alias="id")
    first_name: str
    last_name: str
    username: Optional[str] = None
    email: EmailStr
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    profile_image: Optional[str] = None
    aadhaar_card: Optional[str] = None
    roleId: Optional[int] = Field(default=None, validation_alias="role_id")
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

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)



