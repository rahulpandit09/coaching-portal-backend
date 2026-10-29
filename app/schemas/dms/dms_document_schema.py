from pydantic import BaseModel
from typing import Optional, Any, Union, List
from datetime import datetime, date


class DmsDocumentBase(BaseModel):
    document_title: str
    document_subject: Optional[str] = None

    # Categorization & Location
    target_folder: Optional[str] = None
    target_folder_id: Optional[int] = None
    folder_id: Optional[int] = None
    sub_folder_id: Optional[int] = None
    sub_sub_folder_id: Optional[int] = None

    department: Optional[str] = None
    location: Optional[str] = None
    station_id: Optional[int] = None
    category: Optional[str] = None
    document_type: Optional[str] = None

    # Lifecycle, dates and volume
    custodian_id: Optional[int] = None
    custodian_name: Optional[str] = None
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    volume: Optional[str] = None

    # Security, revision and status
    security_classification: Optional[str] = None
    retention_class: Optional[str] = None
    confidential_document: Optional[bool] = False
    revision: Optional[str] = "Rev 01"
    revision_number: Optional[int] = 1
    revision_note: Optional[str] = None
    status: Optional[str] = "ACTIVE"

    # Physical Access
    physical_rack: Optional[str] = None
    physical_shelf: Optional[str] = None
    physical_box: Optional[str] = None

    # Ownership & Custody (Access Permissions)
    custody_list: Optional[Any] = None
    individual_engineer: Optional[Any] = None

    # File Attachment & Tags
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[str] = None
    file_type: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[Any] = None


class DmsDocumentCreate(DmsDocumentBase):
    created_by: Optional[int] = None


class DmsDocumentUpdate(BaseModel):
    document_title: Optional[str] = None
    document_subject: Optional[str] = None

    # Categorization & Location
    target_folder: Optional[str] = None
    target_folder_id: Optional[int] = None
    folder_id: Optional[int] = None
    sub_folder_id: Optional[int] = None
    sub_sub_folder_id: Optional[int] = None

    department: Optional[str] = None
    location: Optional[str] = None
    station_id: Optional[int] = None
    category: Optional[str] = None
    document_type: Optional[str] = None

    # Lifecycle, dates and volume
    custodian_id: Optional[int] = None
    custodian_name: Optional[str] = None
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    volume: Optional[str] = None

    # Security, revision and status
    security_classification: Optional[str] = None
    retention_class: Optional[str] = None
    confidential_document: Optional[bool] = None
    revision: Optional[str] = None
    revision_number: Optional[int] = None
    revision_note: Optional[str] = None
    status: Optional[str] = None

    # Physical Access
    physical_rack: Optional[str] = None
    physical_shelf: Optional[str] = None
    physical_box: Optional[str] = None

    # Ownership & Custody (Access Permissions)
    custody_list: Optional[Any] = None
    individual_engineer: Optional[Any] = None

    # File Attachment & Tags
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[str] = None
    file_type: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[Any] = None

    updated_by: Optional[int] = None


class DmsDocumentResponse(DmsDocumentBase):
    document_id: int
    document_number: Optional[str] = None
    folder_name: Optional[str] = None
    sub_folder_name: Optional[str] = None
    folder_path: Optional[str] = None
    breadcrumbs: Optional[List[dict]] = None
    revision_count: Optional[int] = 1
    latest_revision_date: Optional[Union[datetime, str]] = None
    is_deleted: Optional[bool] = False
    created_at: Optional[Union[datetime, str]] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    updated_at: Optional[Union[datetime, str]] = None
    updated_by: Optional[int] = None
    updated_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class DmsTrashDocumentResponse(DmsDocumentResponse):
    folder_name: Optional[str] = None
    sub_folder_name: Optional[str] = None
    deleted_at: Optional[Union[datetime, str]] = None
    deleted_by: Optional[int] = None
    deleted_by_name: Optional[str] = None


class PaginatedTrashResponse(BaseModel):
    status: str = "success"
    total_deleted: int
    matching_filter_count: int
    page: int
    limit: int
    data: List[DmsTrashDocumentResponse]


# -------------------------------------------------
# REVISION MODAL SCHEMAS
# -------------------------------------------------
class DmsRevisionItem(BaseModel):
    history_id: int
    revision: str
    revision_number: int
    is_current_active: bool = False
    is_oldest_baseline: bool = False
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[str] = None
    file_type: Optional[str] = None
    deposited_at: Optional[str] = None
    deposited_by_id: Optional[int] = None
    deposited_by_name: Optional[str] = None
    description: Optional[str] = None
    download_url: Optional[str] = None


class DmsOldestBaseline(BaseModel):
    history_id: Optional[int] = None
    revision: Optional[str] = "Rev 01"
    revision_number: Optional[int] = 1
    registered_date: Optional[str] = None
    registered_by_id: Optional[int] = None
    registered_by_name: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[str] = None
    file_type: Optional[str] = None
    description: Optional[str] = None
    download_url: Optional[str] = None


class DmsRevisionDocumentHeader(BaseModel):
    document_id: int
    document_number: Optional[str] = None
    document_title: Optional[str] = None
    document_subject: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    station_id: Optional[int] = None
    target_folder: Optional[str] = None
    folder_id: Optional[int] = None
    folder_name: Optional[str] = None
    sub_folder_id: Optional[int] = None
    sub_folder_name: Optional[str] = None
    volume: Optional[str] = None
    security_classification: Optional[str] = None
    status: Optional[str] = None
    current_revision: Optional[str] = None
    current_file_name: Optional[str] = None
    current_file_size: Optional[str] = None
    current_file_type: Optional[str] = None
    current_download_url: Optional[str] = None


class DmsRevisionDetailsResponse(BaseModel):
    document: DmsRevisionDocumentHeader
    oldest_baseline: Optional[DmsOldestBaseline] = None
    revisions: List[DmsRevisionItem] = []
    action_urls: Optional[dict] = None

