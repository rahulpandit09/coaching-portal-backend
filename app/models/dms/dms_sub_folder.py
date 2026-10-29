from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class DmsSubFolder(Base):
    __tablename__ = "dms_sub_folders"

    sub_folder_id = Column(Integer, primary_key=True, autoincrement=True)
    folder_id = Column(Integer, ForeignKey("dms_folders.folder_id"), nullable=False, index=True)
    parent_sub_folder_id = Column(
        Integer, ForeignKey("dms_sub_folders.sub_folder_id"), nullable=True, index=True
    )
    sub_folder_code = Column(String(50), nullable=True)
    sub_folder_name = Column(String(500), nullable=False)
    sub_folder_description = Column(Text, nullable=True)
    status = Column(String(50), nullable=True, index=True)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, nullable=True)
