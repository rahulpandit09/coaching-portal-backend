from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey
)
from sqlalchemy.orm import relationship

from app.database import Base


class TeacherDetail(Base):
    __tablename__ = "teacher_details"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    employee_id = Column(
        String(100),
        unique=True,
        nullable=True
    )

    qualification = Column(
        String(255),
        nullable=True
    )

    specialization = Column(
        String(255),
        nullable=True
    )

    experience = Column(
        Integer,
        nullable=True
    )

    teaching_language = Column(
        String(100),
        nullable=True
    )

    teaching_classes = Column(
        String(255),
        nullable=True
    )

    teaching_subjects = Column(
        Text,
        nullable=True
    )

    user = relationship(
        "User",
        back_populates="teacher_details"
    )
