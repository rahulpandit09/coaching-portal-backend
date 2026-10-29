from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class DmsFolderHistory(Base):
    __tablename__ = "dms_folders_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    folder_id = Column(Integer, nullable=True, index=True)

    folder_name = Column(String(500), nullable=True)
    folder_description = Column(Text, nullable=True)
    folder_icon = Column(String(100), nullable=True)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, nullable=True)
    history_created_at = Column(DateTime, server_default=func.now(), nullable=True)
