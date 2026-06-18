from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base

class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String(200), nullable=False)
    video_url = Column(String(500))
