from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class FacultyTeacher(Base):
    __tablename__ = "faculty_teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    status = Column(String, default="Active")


class FacultyCourse(Base):
    __tablename__ = "faculty_courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)


class FacultyBatch(Base):
    __tablename__ = "faculty_batches"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    course_id = Column(Integer, ForeignKey("faculty_courses.id"))


class FacultyAssignment(Base):
    __tablename__ = "faculty_assignments"

    id = Column(Integer, primary_key=True)

    teacher_id = Column(Integer, ForeignKey("faculty_teachers.id"))
    course_id = Column(Integer, ForeignKey("faculty_courses.id"))
    batch_id = Column(Integer, ForeignKey("faculty_batches.id"))


class FacultyStudent(Base):
    __tablename__ = "faculty_students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)

    batch_id = Column(Integer, ForeignKey("faculty_batches.id"))