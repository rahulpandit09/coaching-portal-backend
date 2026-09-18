from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date


class StudentDetailBase(BaseModel):
    student_id: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    school_name: Optional[str] = None
    class_name: Optional[str] = None
    board: Optional[str] = None
    academic_year: Optional[str] = None
    subjects: Optional[str] = None
    preferred_language: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pin_code: Optional[str] = None


class StudentDetailCreate(StudentDetailBase):
    pass


class StudentDetailUpdate(BaseModel):
    student_id: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    school_name: Optional[str] = None
    class_name: Optional[str] = None
    board: Optional[str] = None
    academic_year: Optional[str] = None
    subjects: Optional[str] = None
    preferred_language: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pin_code: Optional[str] = None


class StudentDetailOut(StudentDetailBase):
    studentDetailId: int = Field(validation_alias="id")
    userId: int = Field(validation_alias="user_id")
    studentId: Optional[str] = Field(default=None, validation_alias="student_id")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
