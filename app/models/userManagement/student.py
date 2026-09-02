from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    ForeignKey
)
from sqlalchemy.orm import relationship

from app.database import Base


class StudentDetail(Base):
    __tablename__ = "student_details"

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

    date_of_birth = Column(
        Date,
        nullable=True
    )

    gender = Column(
        String(20),
        nullable=True
    )

    student_id = Column(
        String(100),
        unique=True,
        nullable=True
    )

    school_name = Column(
        String(255),
        nullable=True
    )

    class_name = Column(
        String(50),
        nullable=True
    )

    board = Column(
        String(100),
        nullable=True
    )

    academic_year = Column(
        String(20),
        nullable=True
    )

    subjects = Column(
        Text,
        nullable=True
    )

    preferred_language = Column(
        String(100),
        nullable=True
    )

    address = Column(
        Text,
        nullable=True
    )

    city = Column(
        String(100),
        nullable=True
    )

    state = Column(
        String(100),
        nullable=True
    )

    country = Column(
        String(100),
        nullable=True
    )

    pin_code = Column(
        String(20),
        nullable=True
    )

    user = relationship(
        "User",
        back_populates="student_details"
    )
