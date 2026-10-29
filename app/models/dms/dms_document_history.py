from sqlalchemy import (Column, Integer, String, Text, Boolean, Date, DateTime)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class DmsDocumentHistory(Base):
    __tablename__ = "dms_documents_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, nullable=True, index=True)

    document_number = Column(String(100), nullable=True, index=True)
    document_title = Column(String(255), nullable=True)
    document_subject = Column(Text, nullable=True)

    # Categorization & Location
    target_folder = Column(String(255), nullable=True)
    folder_id = Column(Integer, nullable=True)
    sub_folder_id = Column(Integer, nullable=True)
    sub_sub_folder_id = Column(Integer, nullable=True)

    department = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    station_id = Column(Integer, nullable=True)
    category = Column(String(255), nullable=True)
    document_type = Column(String(255), nullable=True)

    # Lifecycle, Dates & Volume
    custodian_id = Column(Integer, nullable=True)
    custodian_name = Column(String(255), nullable=True)
    open_date = Column(Date, nullable=True)
    close_date = Column(Date, nullable=True)
    volume = Column(String(255), nullable=True)

    # Security, Revision & Status
    security_classification = Column(String(255), nullable=True)
    retention_class = Column(String(255), nullable=True)
    confidential_document = Column(Boolean, nullable=True)
    status = Column(String(50), nullable=True)
    revision = Column(String(50), nullable=True)
    revision_number = Column(Integer, nullable=True)
    revision_note = Column(Text, nullable=True)

    # Physical Access
    physical_rack = Column(String(255), nullable=True)
    physical_shelf = Column(String(255), nullable=True)
    physical_box = Column(String(255), nullable=True)

    # Ownership & Custody (Access Permissions)
    custody_list = Column(JSONB, nullable=True)
    individual_engineer = Column(JSONB, nullable=True)

    # File Attachment & Tags
    file_path = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(String(50), nullable=True)
    file_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=True)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, nullable=True)
    history_created_at = Column(DateTime, server_default=func.now(), nullable=True)
