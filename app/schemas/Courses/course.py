from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


# ─── Enums ────────────────────────────────────────────────────────────────────

class CourseStatus(str, Enum):
    active   = "Active"
    inactive = "Inactive"


class FeeType(str, Enum):
    monthly     = "Monthly"
    full_course = "Full Course"


# ─── Base (shared fields) ─────────────────────────────────────────────────────

class CourseBase(BaseModel):
    name:         str            = Field(...,  min_length=1, example="Physics Foundation")
    subject:      str            = Field(...,  example="Physics")
    teacher_name: str            = Field(...,  example="Rahul Sharma")
    batches:      List[str]      = Field(...,  example=["Batch A", "Batch B"])
    status:       CourseStatus   = Field(CourseStatus.active)
    fee_type:     FeeType        = Field(...,  example="Monthly")
    fee_amount:   float          = Field(...,  gt=0, example=1500)
    discount:     float          = Field(0,    ge=0, le=100, example=0)
    fee_due_day:  int            = Field(5,    ge=1, le=28,  example=5)
    start_date:   str            = Field(...,  example="2024-01-10")
    end_date:     str            = Field(...,  example="2024-06-10")
    class_days:   List[str]      = Field(...,  example=["Mon", "Wed", "Fri"])
    class_time:   str            = Field(...,  example="10:00")
    description:  Optional[str] = Field("",   example="Core physics for board exams")
    max_students: int            = Field(60,   gt=0, example=60)


# ─── Request Schemas ────────────────
class CourseCreate(CourseBase):
    """Used for POST /api/courses"""
    pass


class CourseUpdate(CourseBase):
    """Used for PATCH /api/courses/:id  — all fields required (full update)"""
    pass


class CourseStatusUpdate(BaseModel):
    """Used for PATCH /api/courses/:id/status"""
    status: CourseStatus


# ─── Response Schema ──────────────────────────────────────────────────────────

class CourseResponse(CourseBase):
    """Returned by every endpoint"""
    id:        int
    course_id: str   # e.g. CRS-001
    students:  int

    class Config:
        from_attributes = True   # allows SQLAlchemy model → Pydantic
