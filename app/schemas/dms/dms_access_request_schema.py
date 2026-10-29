from pydantic import BaseModel
from typing import Optional, Union
from datetime import datetime, date


class DmsAccessRequestBase(BaseModel):
    # Requester Details
    requester_id: Optional[int] = None
    requester_name: Optional[str] = None
    requester_designation: Optional[str] = None
    requester_department: Optional[str] = None

    # Target Document Details
    document_id: Optional[int] = None
    document_number: Optional[str] = None
    document_title: Optional[str] = None
    security_classification: Optional[str] = None

    # Request Details
    justification: Optional[str] = None
    status: Optional[str] = "PENDING"

    # Permission Model & Validity Window
    permission_model: Optional[str] = "TIME_BOUNDED"  # "TIME_BOUNDED" or "LIFETIME"
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class DmsAccessRequestCreate(DmsAccessRequestBase):
    created_by: Optional[int] = None


class DmsAccessRequestUpdate(BaseModel):
    requester_id: Optional[int] = None
    requester_name: Optional[str] = None
    requester_designation: Optional[str] = None
    requester_department: Optional[str] = None
    document_id: Optional[int] = None
    document_number: Optional[str] = None
    document_title: Optional[str] = None
    security_classification: Optional[str] = None
    justification: Optional[str] = None
    status: Optional[str] = None
    permission_model: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    review_remarks: Optional[str] = None
    updated_by: Optional[int] = None


class DmsAccessRequestAction(BaseModel):
    status: str  # "APPROVED" or "REJECTED"
    permission_model: Optional[str] = "TIME_BOUNDED"  # "TIME_BOUNDED" or "LIFETIME"
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    review_remarks: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_by_name: Optional[str] = None


class DmsAccessRequestResponse(DmsAccessRequestBase):
    request_id: int
    requested_on: Optional[Union[datetime, str]] = None
    reviewed_by: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[Union[datetime, str]] = None
    review_remarks: Optional[str] = None
    is_deleted: Optional[bool] = False
    created_at: Optional[Union[datetime, str]] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    updated_at: Optional[Union[datetime, str]] = None
    updated_by: Optional[int] = None
    updated_by_name: Optional[str] = None

    class Config:
        from_attributes = True
