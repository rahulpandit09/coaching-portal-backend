from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500))

    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    price = Column(Float, nullable=False)
    duration = Column(Integer, nullable=True)
    level = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
