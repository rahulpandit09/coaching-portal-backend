from sqlalchemy import Column, Integer, String
from app.database import Base


class Sidebar(Base):
    __tablename__ = "sidebar"

    id = Column(Integer, primary_key=True, index=True)

    role = Column(String(20), nullable=False)

    title = Column(String(100), nullable=False)

    route = Column(String(100), nullable=False)

    icon = Column(String(50), nullable=True)