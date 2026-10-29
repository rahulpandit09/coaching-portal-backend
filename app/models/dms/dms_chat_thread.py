from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class DmsChatThread(Base):
    __tablename__ = "dms_chat_threads"

    thread_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    thread_title = Column(String(255), nullable=False, default="New Chat")
    document_id = Column(Integer, nullable=True, index=True)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    updated_by = Column(Integer, nullable=True)
