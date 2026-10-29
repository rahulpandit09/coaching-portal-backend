from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List, Union
from datetime import datetime


# -------------------------------------------------
# THREAD SCHEMAS
# -------------------------------------------------
class DmsChatThreadCreate(BaseModel):
    thread_title: Optional[str] = Field(default="New Chat", max_length=255)
    document_id: Optional[int] = Field(
        default=None,
        description="Optional document ID if scoped to a specific document"
    )


class DmsChatThreadResponse(BaseModel):
    thread_id: int
    user_id: int
    thread_title: str
    document_id: Optional[int] = None
    document_title: Optional[str] = None
    document_number: Optional[str] = None
    message_count: Optional[int] = 0
    last_message: Optional[str] = None
    created_at: Optional[Union[datetime, str]] = None
    updated_at: Optional[Union[datetime, str]] = None

    class Config:
        from_attributes = True


# -------------------------------------------------
# MESSAGE SCHEMAS
# -------------------------------------------------
class DocumentCitation(BaseModel):
    document_id: int
    document_title: str
    document_number: Optional[str] = None
    page_number: Optional[int] = None
    snippet: Optional[str] = None


class DmsChatMessageResponse(BaseModel):
    message_id: int
    thread_id: int
    sender: str
    content: str
    document_references: Optional[Union[List[Any], Dict[str, Any]]] = None
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    created_at: Optional[Union[datetime, str]] = None

    class Config:
        from_attributes = True


# -------------------------------------------------
# SEND & SUMMARIZE SCHEMAS
# -------------------------------------------------
class DmsChatSendRequest(BaseModel):
    thread_id: int = Field(..., description="Target thread ID")
    question: str = Field(..., min_length=1, description="User question / prompt")
    document_id: Optional[int] = Field(
        default=None,
        description="Optionally scope answer strictly to this document"
    )
    folder_id: Optional[int] = Field(
        default=None,
        description="Optionally scope context to this folder"
    )
    sub_folder_id: Optional[int] = Field(
        default=None,
        description="Optionally scope context to this subfolder"
    )
    sub_sub_folder_id: Optional[int] = Field(
        default=None,
        description="Optionally scope context to this sub-sub-folder"
    )


class DmsChatSummarizeRequest(BaseModel):
    thread_id: Optional[int] = Field(
        default=None,
        description="Optional thread ID. If provided, user query and Navi's summary are appended to the thread"
    )
    summary_type: Optional[str] = Field(
        default="detailed",
        description="Summary style: 'brief', 'detailed', 'executive', 'key_points'"
    )
    custom_instructions: Optional[str] = Field(
        default=None,
        description="Optional custom focus or instructions for the summary"
    )


class DmsChatSummarizeResponse(BaseModel):
    document_id: int
    document_title: str
    document_number: Optional[str] = None
    page_count: Optional[int] = None
    summary_type: str = "detailed"
    summary: str
    thread_id: Optional[int] = None
    created_at: Optional[Union[datetime, str]] = None


# -------------------------------------------------
# STANDARD ENVELOPE
# -------------------------------------------------
class DmsChatEnvelope(BaseModel):
    status: str = "success"
    message: Optional[str] = None
    data: Optional[Union[Dict[str, Any], List[Any], Any]] = None
