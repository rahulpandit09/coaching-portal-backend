from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    message = Column(Text)

    # who should receive it
    role = Column(String(50), nullable=True)   # student / teacher
    user_id = Column(Integer, nullable=True)   # specific user
    batch_id = Column(Integer, nullable=True)  # specific batch

    is_read = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())