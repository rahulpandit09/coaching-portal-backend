from pydantic import BaseModel
from typing import Optional, List, Any, Union
from datetime import datetime


class DmsGroupBase(BaseModel):
    group_name: str
    discipline_dept: Optional[str] = None
    description: Optional[str] = None
    member_engineers: Optional[List[Any]] = None
    member_count: Optional[int] = 0


class DmsGroupCreate(DmsGroupBase):
    created_by: Optional[int] = None


class DmsGroupUpdate(BaseModel):
    group_name: Optional[str] = None
    discipline_dept: Optional[str] = None
    description: Optional[str] = None
    member_engineers: Optional[List[Any]] = None
    member_count: Optional[int] = None
    updated_by: Optional[int] = None


class DmsGroupResponse(DmsGroupBase):
    group_id: int
    is_deleted: Optional[bool] = False
    created_at: Optional[Union[datetime, str]] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    updated_at: Optional[Union[datetime, str]] = None
    updated_by: Optional[int] = None
    updated_by_name: Optional[str] = None

    class Config:
        from_attributes = True
