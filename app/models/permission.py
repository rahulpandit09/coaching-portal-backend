from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Permission(Base):
    __tablename__ = "permission"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(100), unique=True, nullable=False)

    roles = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan"
    )