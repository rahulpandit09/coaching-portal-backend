from pydantic import BaseModel


class FacultyTeacherSchema(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    status: str | None = None

    class Config:
        from_attributes = True


class FacultyCourseSchema(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


class FacultyBatchSchema(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class FacultyAssignSchema(BaseModel):
    teacher_id: int
    course_id: int
    batch_id: int