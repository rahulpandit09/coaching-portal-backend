from pydantic import BaseModel
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
    id: int
    user_id: int
    student_id: Optional[str] = None

    class Config:
        from_attributes = True
