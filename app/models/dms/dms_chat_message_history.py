from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class DmsChatMessageHistory(Base):
    __tablename__ = "dms_chat_messages_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, nullable=True, index=True)
    thread_id = Column(Integer, nullable=True, index=True)
    sender = Column(String(50), nullable=True)
    content = Column(Text, nullable=True)
    document_references = Column(JSONB, nullable=True)
    model_used = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, nullable=True, default=False)
    created_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, nullable=True)
    history_created_at = Column(DateTime, server_default=func.now(), nullable=True)
