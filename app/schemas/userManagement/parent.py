from pydantic import BaseModel, ConfigDict, Field
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
    parentDetailId: int = Field(validation_alias="id")
    userId: int = Field(validation_alias="user_id")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
