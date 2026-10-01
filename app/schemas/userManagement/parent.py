from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class ParentDetailBase(BaseModel):
    parent_id: Optional[str] = None
    relationship: Optional[str] = None
    occupation: Optional[str] = None
    company_name: Optional[str] = None
    preferred_communication: Optional[str] = None


class ParentDetailCreate(ParentDetailBase):
    pass


class ParentDetailUpdate(BaseModel):
    parent_id: Optional[str] = None
    relationship: Optional[str] = None
    occupation: Optional[str] = None
    company_name: Optional[str] = None
    preferred_communication: Optional[str] = None


class ParentDetailOut(ParentDetailBase):
    parentDetailId: int = Field(validation_alias="id")
    userId: int = Field(validation_alias="user_id")
    parentId: Optional[str] = Field(default=None, validation_alias="parent_id")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
