from pydantic import BaseModel
from typing import Optional, Union, List
from datetime import datetime


class DmsSubFolderBase(BaseModel):
    folder_id: Optional[int] = None
    parent_sub_folder_id: Optional[int] = None
    sub_folder_code: Optional[str] = None
    sub_folder_name: str
    sub_folder_description: Optional[str] = None
    status: Optional[str] = "ACTIVE"


class DmsSubFolderCreate(DmsSubFolderBase):
    created_by: Optional[int] = None


class DmsSubFolderUpdate(BaseModel):
    folder_id: Optional[int] = None
    parent_sub_folder_id: Optional[int] = None
    sub_folder_code: Optional[str] = None
    sub_folder_name: Optional[str] = None
    sub_folder_description: Optional[str] = None
    status: Optional[str] = None
    updated_by: Optional[int] = None


class DmsSubFolderResponse(DmsSubFolderBase):
    sub_folder_id: int
    folder_name: Optional[str] = None
    parent_sub_folder_id: Optional[int] = None
    parent_sub_folder_name: Optional[str] = None
    sub_sub_folders: Optional[List[dict]] = []
    children: Optional[List[dict]] = []
    is_deleted: Optional[bool] = False
    created_at: Optional[Union[datetime, str]] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    updated_at: Optional[Union[datetime, str]] = None
    updated_by: Optional[int] = None
    updated_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class DmsSubFolderMoveRequest(BaseModel):
    destination_folder_id: int
    parent_sub_folder_id: Optional[int] = None  # None = root of primary folder; non-null = move into this subfolder as parent
    updated_by: Optional[int] = None


class DmsSubFolderMoveData(BaseModel):
    sub_folder_id: int
    sub_folder_name: str
    source_folder_id: int
    source_folder_name: Optional[str] = None
    source_parent_sub_folder_id: Optional[int] = None
    source_parent_sub_folder_name: Optional[str] = None
    destination_folder_id: int
    destination_folder_name: Optional[str] = None
    destination_parent_sub_folder_id: Optional[int] = None
    destination_parent_sub_folder_name: Optional[str] = None
    affected_documents_count: int
    affected_descendants_count: int = 0


class DmsSubFolderMovePreviewResponse(BaseModel):
    status: str = "success"
    data: DmsSubFolderMoveData


class DmsSubFolderMoveResponse(BaseModel):
    status: str = "success"
    message: str = "Sub-folder moved successfully"
    data: DmsSubFolderMoveData
