from pydantic import BaseModel, ConfigDict, Field
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
    teacherDetailId: int = Field(validation_alias="id")
    userId: int = Field(validation_alias="user_id")
    employeeId: Optional[str] = Field(default=None, validation_alias="employee_id")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
