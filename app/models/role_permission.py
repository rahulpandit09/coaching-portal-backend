from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base

class RolePermission(Base):
    __tablename__ = "RolePermissions"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey(role.id))
    Permission_id = Column(Integer, ForeignKey(permission.id))