from sqlalchemy import Column, Integer, String, Float, Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY
from app.database import Base
from sqlalchemy import Column, Integer, String, Float, Enum as SAEnum, DateTime
from datetime import datetime



class Course(Base):
    __tablename__ = "teacher_course"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_id    = Column(String,  unique=True, index=True, nullable=False)   # e.g. CRS-001
    name         = Column(String,  nullable=False)
    subject      = Column(String,  nullable=False)
    teacher_name = Column(String,  nullable=False)
    batches      = Column(ARRAY(String), nullable=False, default=[])
    students     = Column(Integer, nullable=False, default=0)
    max_students = Column(Integer, nullable=False, default=60)
    status       = Column(
                       SAEnum("Active", "Inactive", name="course_status_enum"),
                       nullable=False,
                       default="Active",
                   )
    fee_type     = Column(
                       SAEnum("Monthly", "Full Course", name="fee_type_enum"),
                       nullable=False,
                   )
    fee_amount   = Column(Float,   nullable=False)
    discount     = Column(Float,   nullable=False, default=0)
    fee_due_day  = Column(Integer, nullable=False, default=5)
    start_date   = Column(String,  nullable=False)
    end_date     = Column(String,  nullable=False)
    class_days   = Column(ARRAY(String), nullable=False, default=[])
    class_time   = Column(String,  nullable=False)
    description  = Column(String,  nullable=True, default="")
