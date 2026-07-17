from sqlalchemy import Column, String, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base

class RoleSubMenu(Base):
    __tablename__ = "role_submenu"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("role.id"))
    submenu_id = Column(Integer, ForeignKey("submenu.id"))
    role = relationship("Role", back_populates="role_submenus")
    submenu = relationship("SubMenu", back_populates="roles")

