from pydantic import BaseModel
from typing import Optional, List, Any, Union
from datetime import datetime


class DmsPublisherBase(BaseModel):
    publisher_user_id: Optional[int] = None
    publisher_name: str
    publisher_email: Optional[str] = None
    publisher_dept: Optional[str] = None
    publisher_station_location: Optional[str] = None
    publisher_station_id: Optional[int] = None
    status: Optional[str] = "ACTIVE"
    assigned_folders: Optional[List[Any]] = None
    assigned_subfolders: Optional[List[Any]] = None


class DmsPublisherCreate(DmsPublisherBase):
    created_by: Optional[int] = None


class DmsPublisherUpdate(BaseModel):
    publisher_user_id: Optional[int] = None
    publisher_name: Optional[str] = None
    publisher_email: Optional[str] = None
    publisher_dept: Optional[str] = None
    publisher_station_location: Optional[str] = None
    publisher_station_id: Optional[int] = None
    status: Optional[str] = None
    assigned_folders: Optional[List[Any]] = None
    assigned_subfolders: Optional[List[Any]] = None
    updated_by: Optional[int] = None


class DmsPublisherResponse(DmsPublisherBase):
    publisher_id: int
    is_deleted: Optional[bool] = False
    created_at: Optional[Union[datetime, str]] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    updated_at: Optional[Union[datetime, str]] = None
    updated_by: Optional[int] = None
    updated_by_name: Optional[str] = None
    assigned_folder_ids: Optional[List[int]] = None
    assigned_subfolder_ids: Optional[List[int]] = None
    raw_assigned_folders: Optional[List[Any]] = None
    raw_assigned_subfolders: Optional[List[Any]] = None
    assigned_hierarchy: Optional[List[Any]] = None

    class Config:
        from_attributes = True
