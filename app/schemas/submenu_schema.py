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
    subMenuId: int = Field(validation_alias="id")
    menuId: int = Field(validation_alias="menu_id")
    title: str
    path: str | None = None
    icon: str | None = None
    orderIndex: int = Field(default=0, validation_alias="order_index")
    status: bool = True
    createdAt: datetime = Field(validation_alias="created_at")
    updatedAt: datetime | None = Field(default=None, validation_alias="updated_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class SubMenuListResponse(BaseModel):
    count: int
    data: list[SubMenuResponse]