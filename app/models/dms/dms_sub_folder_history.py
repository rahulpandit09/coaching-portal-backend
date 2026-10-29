from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class DmsSubFolderHistory(Base):
    __tablename__ = "dms_sub_folders_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    sub_folder_id = Column(Integer, nullable=True, index=True)
    folder_id = Column(Integer, nullable=True, index=True)
    parent_sub_folder_id = Column(Integer, nullable=True, index=True)

    sub_folder_code = Column(String(50), nullable=True)
    sub_folder_name = Column(String(500), nullable=True)
    sub_folder_description = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, nullable=True)
    history_created_at = Column(DateTime, server_default=func.now(), nullable=True)
