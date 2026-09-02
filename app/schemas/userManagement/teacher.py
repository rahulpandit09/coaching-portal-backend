from pydantic import BaseModel
from typing import Optional


class TeacherDetailBase(BaseModel):
    employee_id: Optional[str] = None
    qualification: Optional[str] = None
    specialization: Optional[str] = None
    experience: Optional[int] = None
    teaching_language: Optional[str] = None
    teaching_classes: Optional[str] = None
    teaching_subjects: Optional[str] = None


class TeacherDetailCreate(TeacherDetailBase):
    pass


class TeacherDetailUpdate(BaseModel):
    employee_id: Optional[str] = None
    qualification: Optional[str] = None
    specialization: Optional[str] = None
    experience: Optional[int] = None
    teaching_language: Optional[str] = None
    teaching_classes: Optional[str] = None
    teaching_subjects: Optional[str] = None


class TeacherDetailOut(TeacherDetailBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
