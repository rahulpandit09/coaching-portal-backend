from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.database import Base

class adminDashboardStudent(Base):
    __tablename__ = "adminDashboardStudent"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    status = Column(String)
    course = Column(String)
    fees = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

