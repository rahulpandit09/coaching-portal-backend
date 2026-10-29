from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class DmsGroup(Base):
    __tablename__ = "dms_groups"

    group_id = Column(Integer, primary_key=True, autoincrement=True)
    group_name = Column(String(255), nullable=False, index=True)
    discipline_dept = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Selected Member Engineers (list of engineer user objects/IDs)
    member_engineers = Column(JSONB, nullable=True)
    member_count = Column(Integer, default=0, nullable=False)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    updated_by = Column(Integer, nullable=True)
