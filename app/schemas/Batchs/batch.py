from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# BATCH SCHEMAS
class BatchCreate(BaseModel):
    name:         str
    course:       str
    teacher:      str
    days:         List[str]   = []
    time:         str         = ""
    max_students: int         = 40
    status:       str         = "Active"
    fee:          float       = 0
    discount:     float       = 0
    start_date:   str
    end_date:     str
    description:  str         = ""


class BatchUpdate(BaseModel):
    name:         Optional[str]       = None
    course:       Optional[str]       = None
    teacher:      Optional[str]       = None
    days:         Optional[List[str]] = None
    time:         Optional[str]       = None
    max_students: Optional[int]       = None
    status:       Optional[str]       = None
    fee:          Optional[float]     = None
    discount:     Optional[float]     = None
    start_date:   Optional[str]       = None
    end_date:     Optional[str]       = None
    description:  Optional[str]       = None


class BatchResponse(BaseModel):
    id:           int
    batch_id:     str
    name:         str
    course:       str
    teacher:      str
    days:         List[str]
    time:         str
    students:     int
    max_students: int
    status:       str
    fee:          float
    discount:     float
    start_date:   str
    end_date:     str
    description:  str
    created_at:   datetime

    class Config:
        from_attributes = True


class BatchStats(BaseModel):
    total:    int
    active:   int
    full:     int
    students: int


# ─────────────────────────────────────────────────────────────────────────────
# BATCH STUDENT SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class BatchStudentAdd(BaseModel):
    student_id:   int
    student_name: str
    phone:        str = ""


class BatchStudentUpdate(BaseModel):
    attendance: Optional[float] = Field(None, ge=0, le=100)
    fee_status: Optional[str]   = None    # Paid | Pending | Unpaid


class BatchStudentResponse(BaseModel):
    id:           int
    batch_id:     int
    student_id:   int
    student_name: str
    phone:        str
    attendance:   float
    fee_status:   str
    joined_at:    datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# ATTENDANCE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class AttendanceMark(BaseModel):
    student_id:   int
    student_name: str
    present:      bool


class AttendanceCreate(BaseModel):
    date:    str                        # "2024-03-15"
    records: List[AttendanceMark]


class AttendanceResponse(BaseModel):
    id:           int
    batch_id:     int
    student_id:   int
    student_name: str
    date:         str
    present:      bool
    marked_at:    datetime

    class Config:
        from_attributes = True


class AttendanceSummary(BaseModel):
    student_id:   int
    student_name: str
    total_classes: int
    present:      int
    absent:       int
    percentage:   float


# ─────────────────────────────────────────────────────────────────────────────
# TEST SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class TestCreate(BaseModel):
    title:       str
    total_marks: float = 100
    test_date:   str


class TestUpdate(BaseModel):
    title:       Optional[str]   = None
    total_marks: Optional[float] = None
    test_date:   Optional[str]   = None


class TestResponse(BaseModel):
    id:          int
    batch_id:    int
    title:       str
    total_marks: float
    test_date:   str
    created_at:  datetime

    class Config:
        from_attributes = True


class TestResultAdd(BaseModel):
    student_id:   int
    student_name: str
    marks:        float
    remarks:      str = ""


class TestResultResponse(BaseModel):
    id:           int
    test_id:      int
    batch_id:     int
    student_id:   int
    student_name: str
    marks:        float
    remarks:      str

    class Config:
        from_attributes = True