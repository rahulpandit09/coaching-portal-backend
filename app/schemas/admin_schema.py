from pydantic import BaseModel, EmailStr, Field

class CreateTeacherSchema(BaseModel):
    name: str = Field(..., min_length=2)
    username: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=6)


class CreateStudentSchema(BaseModel):
    name: str = Field(..., min_length=2)
    username: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=6)
