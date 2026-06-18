# from sqlalchemy import Column, Integer, String, Date, DateTime, Text
# from sqlalchemy.sql import func
# from app.database import Base

# class AdminStudent(Base):
#     __tablename__ = "add_students"

#     id = Column(Integer, primary_key=True, index=True)
#     student_id = Column(String, unique=True, nullable=False)
#     name = Column(String, nullable=False)
#     phone = Column(String, nullable=False)
#     email = Column(String)
#     dob = Column(Date)
#     address = Column(Text)
#     course = Column(String, nullable=False)
#     batch = Column(String, nullable=False)
#     admission_date = Column(Date)
#     status = Column(String, nullable=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())


# from sqlalchemy import Column, Integer, String, Date, DateTime, Text
# from sqlalchemy.sql import func
# from sqlalchemy.orm import relationship
# from app.database import Base

# class AdminStudent(Base):
#     __tablename__ = "add_students"

#     id = Column(Integer, primary_key=True, index=True)
#     student_id = Column(String, unique=True, nullable=False)
#     name = Column(String, nullable=False)
#     phone = Column(String, nullable=False)
#     email = Column(String)
#     dob = Column(Date)
#     address = Column(Text)
#     course = Column(String, nullable=False)
#     batch = Column(String, nullable=False)
#     admission_date = Column(Date)
#     status = Column(String, nullable=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())

#     fee = relationship("Fee", back_populates="student", uselist=False)


from sqlalchemy import Column, Integer, String, Date, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AdminStudent(Base):
    __tablename__ = "add_students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String)
    address = Column(Text)
    course = Column(String, nullable=False)
    batch = Column(String, nullable=False)
    admission_date = Column(Date)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 🔥 One-to-One Relationship
    fee = relationship("Fee", back_populates="student", uselist=False)