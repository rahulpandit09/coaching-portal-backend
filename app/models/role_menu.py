from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base

class RoleMenu(Base):
    __tablename__ = "role_menu"
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("role.id"), nullable=False)
    menu_id = Column(Integer, ForeignKey("menu.id"), nullable=False)