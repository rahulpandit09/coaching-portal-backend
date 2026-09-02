from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from app.schemas.submenu_schema import SubMenuResponse

class MenuCreate(BaseModel):
    title: str = Field(..., max_length=100)
    path: str | None = Field(default=None, max_length=100)
    icon: str | None = Field(default=None, max_length=50)
    parent_id: int | None = None
    is_active: bool = True
    order_index: int = 0

class MenuUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    path: str | None = Field(default=None, max_length=100)
    icon: str | None = Field(default=None, max_length=50)
    parent_id: int | None = None
    is_active: bool | None = None
    order_index: int | None = None

class MenuResponse(BaseModel):
    id: int
    title: str
    path: str | None = None
    icon: str | None = None
    parent_id: int | None = None
    is_active: bool
    order_index: int
    created_at: datetime
    updated_at: datetime | None = None
    submenu: list[SubMenuResponse] = []

    model_config = ConfigDict(from_attributes=True)

class MenuListResponse(BaseModel):
    count: int
    data: list[MenuResponse]