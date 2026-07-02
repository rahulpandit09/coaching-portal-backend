from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base

class Permission(Base):
    __tablename__ = "Permissions"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    code = Column(String)
    