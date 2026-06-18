from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    ARRAY, ForeignKey, DateTime, Text
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id           = Column(Integer, primary_key=True, index=True)
    batch_id     = Column(String,  unique=True, index=True, nullable=False)  # BAT-001
    name         = Column(String,  nullable=False)
    course       = Column(String,  nullable=False)
    teacher      = Column(String,  nullable=False)
    days         = Column(ARRAY(String), default=[])        # ["Mon","Wed","Fri"]
    time         = Column(String,  default="")              # "10:00"
    students     = Column(Integer, default=0)               # auto-updated
    max_students = Column(Integer, default=40)
    status       = Column(String,  default="Active")        # Active | Upcoming | Completed | Inactive
    fee          = Column(Float,   default=0)
    discount     = Column(Float,   default=0)
    start_date   = Column(String,  nullable=False)
    end_date     = Column(String,  nullable=False)
    description  = Column(Text,    default="")
    created_at   = Column(DateTime, default=datetime.utcnow)

    # Relationships
    enrollments  = relationship("BatchStudent",  back_populates="batch", cascade="all, delete-orphan")
    attendance   = relationship("BatchAttendance", back_populates="batch", cascade="all, delete-orphan")
    tests        = relationship("BatchTest",     back_populates="batch", cascade="all, delete-orphan")


class BatchStudent(Base):
    __tablename__ = "batch_students"

    id           = Column(Integer, primary_key=True, index=True)
    batch_id     = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    student_id   = Column(Integer, nullable=False)
    student_name = Column(String,  nullable=False)
    phone        = Column(String,  default="")
    attendance   = Column(Float,   default=0)               # percentage 0–100
    fee_status   = Column(String,  default="Pending")       # Paid | Pending | Unpaid
    joined_at    = Column(DateTime, default=datetime.utcnow)

    batch        = relationship("Batch", back_populates="enrollments")


class BatchAttendance(Base):
    __tablename__ = "batch_attendance"

    id           = Column(Integer, primary_key=True, index=True)
    batch_id     = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    student_id   = Column(Integer, nullable=False)
    student_name = Column(String,  nullable=False)
    date         = Column(String,  nullable=False)          # "2024-03-15"
    present      = Column(Boolean, default=False)
    marked_at    = Column(DateTime, default=datetime.utcnow)

    batch        = relationship("Batch", back_populates="attendance")


class BatchTest(Base):
    __tablename__ = "batch_tests"

    id           = Column(Integer, primary_key=True, index=True)
    batch_id     = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    title        = Column(String,  nullable=False)
    total_marks  = Column(Float,   default=100)
    test_date    = Column(String,  nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    batch        = relationship("Batch", back_populates="tests")
    results      = relationship("BatchTestResult", back_populates="test", cascade="all, delete-orphan")


class BatchTestResult(Base):
    __tablename__ = "batch_test_results"

    id           = Column(Integer, primary_key=True, index=True)
    test_id      = Column(Integer, ForeignKey("batch_tests.id", ondelete="CASCADE"), nullable=False)
    batch_id     = Column(Integer, nullable=False)
    student_id   = Column(Integer, nullable=False)
    student_name = Column(String,  nullable=False)
    marks        = Column(Float,   default=0)
    remarks      = Column(String,  default="")

    test         = relationship("BatchTest", back_populates="results")