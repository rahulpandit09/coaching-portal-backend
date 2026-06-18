from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base

class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    score = Column(Integer)
