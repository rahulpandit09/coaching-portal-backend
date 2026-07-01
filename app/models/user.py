from sqlalchemy import (Column,Integer,String,DateTime,Boolean,ForeignKey)
from app.database import Base

class User(Base):
    __tablename__ = "users"

    # Primary Key
    id = Column(Integer,primary_key=True,index=True)
    
    full_name = Column(String(100),nullable=False)
    username = Column(String(100),unique=True,index=True,nullable=False)
    email = Column(String(100),unique=True,index=True,nullable=False)
    password = Column(String(255),nullable=False)
    role_id = Column(Integer,ForeignKey("role.id"),nullable=False)
    reset_token = Column(String,nullable=True)
    reset_token_expiry = Column(DateTime,nullable=True)
    otp_code = Column(String(6),nullable=True)
    otp_expiry = Column( DateTime,nullable=True)
    otp_verified = Column( Boolean,default=False)
    profile_image = Column(String,nullable=True)
    last_login = Column(DateTime,nullable=True)