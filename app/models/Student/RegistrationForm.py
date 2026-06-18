from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class RegistrationStudent(Base):
    __tablename__ = "RegistrationStudent"

    id = Column(Integer, primary_key=True, index=True)

    fullName = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    dob = Column(String, nullable=False)
    gender = Column(String, nullable=False)

    address = Column(String, nullable=False)

    course = Column(String, nullable=False)
    batch = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    qualification = Column(String, nullable=False)
    school = Column(String, nullable=False)

    parentContact = Column(String, nullable=True)
    agree = Column(Boolean, nullable=False)

  
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    
    user = relationship("User", back_populates="student")
