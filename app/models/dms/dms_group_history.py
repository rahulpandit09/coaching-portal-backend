from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class DmsGroupHistory(Base):
    __tablename__ = "dms_groups_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, nullable=True, index=True)

    group_name = Column(String(255), nullable=True)
    discipline_dept = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Selected Member Engineers
    member_engineers = Column(JSONB, nullable=True)
    member_count = Column(Integer, default=0, nullable=True)

    # Standard Audit Tracking
    is_deleted = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, nullable=True)
    history_created_at = Column(DateTime, server_default=func.now(), nullable=True)
