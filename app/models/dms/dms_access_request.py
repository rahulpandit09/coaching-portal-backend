from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date
from sqlalchemy.sql import func
from app.database import Base


class DmsAccessRequest(Base):
    __tablename__ = "dms_access_requests"

    request_id = Column(Integer, primary_key=True, autoincrement=True)

    # Requester Details
    requester_id = Column(Integer, nullable=True, index=True)
    requester_name = Column(String(255), nullable=True)
    requester_designation = Column(String(255), nullable=True)
    requester_department = Column(String(255), nullable=True)

    # Target Document Details
    document_id = Column(Integer, nullable=True, index=True)
    document_number = Column(String(100), nullable=True)
    document_title = Column(String(255), nullable=True)
    security_classification = Column(String(100), nullable=True)

    # Request Information
    justification = Column(Text, nullable=True)
    status = Column(String(50), default="PENDING", nullable=True, index=True)  # PENDING, APPROVED, REJECTED, EXPIRED
    requested_on = Column(DateTime, server_default=func.now(), nullable=True)

    # Permission Model & Validity Window (when Approved)
    permission_model = Column(String(50), default="TIME_BOUNDED", nullable=True)  # TIME_BOUNDED, LIFETIME
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)

    # Review / Approval Tracking
    reviewed_by = Column(Integer, nullable=True)
    reviewed_by_name = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_remarks = Column(Text, nullable=True)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    updated_by = Column(Integer, nullable=True)
