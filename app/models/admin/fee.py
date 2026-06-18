from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Fee(Base):
    __tablename__ = "fees"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("add_students.id", ondelete="CASCADE"))

    total_fees = Column(Numeric, nullable=False)
    paid_amount = Column(Numeric, nullable=False)
    pending_amount = Column(Numeric, nullable=False)

    payment_mode = Column(String)
    comments = Column(Text, default="")

    #  Back reference
    student = relationship("AdminStudent", back_populates="fee")