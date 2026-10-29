from sqlalchemy import (Column, Integer, String, Text, Boolean, Date, DateTime, ForeignKey)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class DmsDocument(Base):
    __tablename__ = "dms_documents"

    document_id = Column(Integer, primary_key=True, autoincrement=True)
    document_number = Column(String(100), unique=True, nullable=False, index=True)
    document_title = Column(String(255), nullable=False)
    document_subject = Column(Text, nullable=True)

    # Categorization & Location
    target_folder = Column(String(255), nullable=True)
    folder_id = Column(Integer,nullable=True)
    sub_folder_id = Column(Integer, nullable=True)
    sub_sub_folder_id = Column(Integer, nullable=True)

    department = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    station_id = Column(Integer, nullable=True, index=True)
    category = Column(String(255), nullable=True)
    document_type = Column(String(255), nullable=True)

    # 2.lifecycle ,dates and volume
    custodian_id = Column(Integer, nullable=True, index=True)
    custodian_name = Column(String(255), nullable=True)
    open_date = Column(Date, nullable=True)
    close_date = Column(Date, nullable=True)
    volume = Column(String(255), nullable=True)

    # 3.Security, revision and status
    security_classification = Column(String(255), nullable=True)
    retention_class = Column(String(255), nullable=True)
    confidential_document = Column(Boolean, nullable=True)
    revision = Column(String(50), default="Rev 01", nullable=True)
    revision_number = Column(Integer, default=1, nullable=True)
    revision_note = Column(Text, nullable=True)

    #4.Physical Access 
    physical_rack = Column(String(255), nullable=True)
    physical_shelf = Column(String(255), nullable=True)
    physical_box = Column(String(255), nullable=True)

    status = Column(String(50), nullable=True)
   
    # Ownership & Custody (Access Permissions)
    custody_list = Column(JSONB, nullable=True)
    individual_engineer = Column(JSONB, nullable=True)

    # File Attachment & Tags
    file_path = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(String(50), nullable=True)
    file_type = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=True)

    # Audit Tracking
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    updated_by = Column(Integer, nullable=True)

