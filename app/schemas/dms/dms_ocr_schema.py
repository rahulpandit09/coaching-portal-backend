from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List, Union
from datetime import datetime


class DmsOcrProcessRequest(BaseModel):
    """Optional configuration when requesting OCR processing."""
    force_reprocess: Optional[bool] = Field(
        default=False,
        description="If True, re-extracts text and regenerates summary even if already completed"
    )
    custom_summary_prompt: Optional[str] = Field(
        default=None,
        description="Optional specific instructions for AI document summary"
    )


class DmsOcrMetadata(BaseModel):
    ocr_id: int
    document_id: int
    ocr_status: str
    page_count: Optional[int] = None
    character_count: Optional[int] = None
    word_count: Optional[int] = None
    document_summary: Optional[str] = None
    metadata_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: Optional[Union[datetime, str]] = None
    updated_at: Optional[Union[datetime, str]] = None

    class Config:
        from_attributes = True


class DmsOcrDetails(DmsOcrMetadata):
    document_title: Optional[str] = None
    document_number: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[str] = None
    extracted_text: Optional[str] = None


class DmsOcrResponse(BaseModel):
    status: str = "success"
    message: Optional[str] = None
    data: Optional[Union[DmsOcrDetails, DmsOcrMetadata, Dict[str, Any]]] = None
