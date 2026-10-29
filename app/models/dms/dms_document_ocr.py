from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class DmsDocumentOcr(Base):
    __tablename__ = "dms_document_ocr"

    ocr_id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, nullable=False, unique=True, index=True)

    ocr_status = Column(String(50), nullable=False, default="PENDING")
    extracted_text = Column(Text, nullable=True)
    document_summary = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=True)
    metadata_info = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    updated_by = Column(Integer, nullable=True)
