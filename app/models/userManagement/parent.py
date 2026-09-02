from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey
)
from sqlalchemy.orm import relationship as orm_relationship

from app.database import Base


class ParentDetail(Base):
    __tablename__ = "parent_details"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    relationship = Column(
        String(50),
        nullable=True
    )

    occupation = Column(
        String(255),
        nullable=True
    )

    company_name = Column(
        String(255),
        nullable=True
    )

    preferred_communication = Column(
        String(50),
        nullable=True
    )

    user = orm_relationship(
        "User",
        back_populates="parent_details"
    )

