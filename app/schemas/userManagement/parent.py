from pydantic import BaseModel
from typing import Optional


class ParentDetailBase(BaseModel):
    relationship: Optional[str] = None
    occupation: Optional[str] = None
    company_name: Optional[str] = None
    preferred_communication: Optional[str] = None


class ParentDetailCreate(ParentDetailBase):
    pass


class ParentDetailUpdate(BaseModel):
    relationship: Optional[str] = None
    occupation: Optional[str] = None
    company_name: Optional[str] = None
    preferred_communication: Optional[str] = None


class ParentDetailOut(ParentDetailBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
