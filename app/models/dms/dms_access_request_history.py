from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date
from sqlalchemy.sql import func
from app.database import Base


class DmsAccessRequestHistory(Base):
    __tablename__ = "dms_access_requests_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, nullable=True, index=True)

    # Requester Details
    requester_id = Column(Integer, nullable=True)
    requester_name = Column(String(255), nullable=True)
    requester_designation = Column(String(255), nullable=True)
    requester_department = Column(String(255), nullable=True)

    # Target Document Details
    document_id = Column(Integer, nullable=True)
    document_number = Column(String(100), nullable=True)
    document_title = Column(String(255), nullable=True)
    security_classification = Column(String(100), nullable=True)

    # Request Information
    justification = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)
    requested_on = Column(DateTime, nullable=True)

    # Permission Model & Timed Validity Window
    permission_model = Column(String(50), nullable=True)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)

    # Review / Approval Tracking
    reviewed_by = Column(Integer, nullable=True)
    reviewed_by_name = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_remarks = Column(Text, nullable=True)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, nullable=True)
    history_created_at = Column(DateTime, server_default=func.now(), nullable=True)
