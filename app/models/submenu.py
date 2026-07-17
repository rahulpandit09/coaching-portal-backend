from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class SubMenu(Base):
    __tablename__ =  "submenu"

    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, ForeignKey("menu.id"))
    title = Column(String(100), nullable=False)
    path = Column(String(100))
    icon = Column(String(50))
    order_index = Column(Integer, default=0, index=True)
    status = Column(Boolean, default=True)

    # Audit & Soft Delete
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    menu = relationship("Menu", back_populates="submenu")
    roles = relationship("RoleSubMenu", back_populates="submenu", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('menu_id', 'title', name='uq_submenu_title_per_menu'),
        UniqueConstraint('menu_id', 'path', name='uq_submenu_path_per_menu'),
    )