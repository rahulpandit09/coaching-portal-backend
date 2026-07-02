from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.database import Base

class SubMenu(Base):
    __tablename__: "submenus"

    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, ForeignKey("menu.id"))
    title = Column(string, nullable=False)
    route = Column(string)
    icon = Column(string)
    order_index = Column(Integer)
    status = Column(Boolean, default=True)