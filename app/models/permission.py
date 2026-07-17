from sqlalchemy import Column, Integer, ForeignKey, String
from app.database import Base
from sqlalchemy.orm import relationship

class Permission(Base):
    __tablename__ = "permission"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    code = Column(String)

    roles = relationship("RolePermission", back_populates="permission", cascade="all, delete")
    