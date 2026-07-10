from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class SubMenu(Base):
    __tablename__ =  "submenus"

    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, ForeignKey("menu.id"))
    title = Column(String, nullable=False)
    path = Column(String)
    icon = Column(String)
    order_index = Column(Integer)
    status = Column(Boolean, default=True)

    menu = relationship("Menu", back_populates="submenu")
    roles = relationship("RoleSubMenu", back_populates="submenu", cascade="all, delete")