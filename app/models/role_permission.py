from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base
from sqlalchemy.orm import relationship

class RolePermission(Base):
    __tablename__ = "RolePermission"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("role.id"))
    permission_id = Column(Integer, ForeignKey("permission.id"))

    role = relationship("Role", back_populates="permission")
    permission = relationship("Permission", back_populates="roles")