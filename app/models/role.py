from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    users = relationship("User", back_populates="role")
    role_menus = relationship("RoleMenu",back_populates="role",cascade="all, delete")
    permission = relationship("RolePermission", back_populates="role",cascade="all, delete")
    role_submenus = relationship("RoleSubMenu",back_populates="role",cascade="all, delete")