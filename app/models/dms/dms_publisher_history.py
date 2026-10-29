from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class DmsPublisherHistory(Base):
    __tablename__ = "dms_publishers_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    publisher_id = Column(Integer, nullable=True, index=True)

    publisher_user_id = Column(Integer, nullable=True)
    publisher_name = Column(String(255), nullable=True)
    publisher_email = Column(String(255), nullable=True)
    publisher_dept = Column(String(255), nullable=True)
    publisher_station_location = Column(String(255), nullable=True)
    publisher_station_id = Column(Integer, nullable=True)

    status = Column(String(50), nullable=True)

    # Folder Access Delegation (RBAC)
    assigned_folders = Column(JSONB, nullable=True)
    assigned_subfolders = Column(JSONB, nullable=True)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, nullable=True)
    history_created_at = Column(DateTime, server_default=func.now(), nullable=True)
