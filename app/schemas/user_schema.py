from pydantic import BaseModel, EmailStr, Field
from typing import Optional

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
    role_id: Optional[int] = None
    role: Optional[str] = None

    class Config:
        from_attributes = True


