from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class SubMenuCreate(BaseModel):
    menu_id: int
    title: str = Field(..., max_length=100)
    path: str | None = Field(default=None, max_length=100)
    icon: str | None = Field(default=None, max_length=50)
    order_index: int = 0
    status: bool = True

class SubMenuUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    path: str | None = Field(default=None, max_length=100)
    icon: str | None = Field(default=None, max_length=50)
    order_index: int | None = None
    status: bool | None = None
    menu_id: int | None = None

class MessageResponse(BaseModel):
    message: str

class SubMenuResponse(BaseModel):
    id: int
    menu_id: int
    title: str
    path: str | None = None
    icon: str | None = None
    order_index: int
    status: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class SubMenuListResponse(BaseModel):
    count: int
    data: list[SubMenuResponse]