from sqlalchemy import Column, String, Boolean, ForeignKey
from app.core.dependencies import Base

class Role_Submenu(Base):
    __tablename__ = "role_submenu"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("role.id"))
    submenus_id = Column(Integer, ForeignKey("submenus.id"))
    

