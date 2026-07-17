from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Menu(Base):
    __tablename__ = "menu"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False, unique=True)
    path = Column(String(100), nullable=True, unique=True)
    icon = Column(String(50), nullable=True)
    parent_id = Column(Integer, ForeignKey("menu.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    order_index = Column(Integer, default=0, index=True)
    
    # Audit & Soft Delete
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    submenu = relationship("SubMenu", back_populates="menu", cascade="all, delete-orphan")
    roles = relationship("RoleMenu", back_populates="menu", cascade="all, delete-orphan")
    parent = relationship("Menu", remote_side=[id])