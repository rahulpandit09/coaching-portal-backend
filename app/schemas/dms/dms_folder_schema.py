from pydantic import BaseModel
from typing import Optional, Union
from datetime import datetime


class DmsFolderBase(BaseModel):
    folder_name: str
    folder_description: Optional[str] = None
    folder_icon: Optional[str] = None


class DmsFolderCreate(DmsFolderBase):
    created_by: Optional[int] = None


class DmsFolderUpdate(BaseModel):
    folder_name: Optional[str] = None
    folder_description: Optional[str] = None
    folder_icon: Optional[str] = None
    updated_by: Optional[int] = None


class DmsFolderResponse(DmsFolderBase):
    folder_id: int
    is_deleted: Optional[bool] = False
    created_at: Optional[Union[datetime, str]] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    updated_at: Optional[Union[datetime, str]] = None
    updated_by: Optional[int] = None
    updated_by_name: Optional[str] = None

    class Config:
        from_attributes = True
