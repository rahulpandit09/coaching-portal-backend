from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    course_id = Column(Integer, nullable=True)
    pending_amount = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    payments = relationship("Payment", back_populates="student")
