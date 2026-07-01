from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.database import Base

class Menu(Base):
    __tablename__ = "menu"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    route = Column(String(100), nullable=True)
    icon = Column(String(50), nullable=True)
    parent_id = Column(Integer, ForeignKey("menu.id"), nullable=True)
    is_active = Column(Boolean, default=True)
