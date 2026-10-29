from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class DmsChatThreadHistory(Base):
    __tablename__ = "dms_chat_threads_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    thread_title = Column(String(255), nullable=True)
    document_id = Column(Integer, nullable=True)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, nullable=True, default=False)
    created_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, nullable=True)
    history_created_at = Column(DateTime, server_default=func.now(), nullable=True)
