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
    menuId: int = Field(validation_alias="id")
    title: str
    path: str | None = None
    icon: str | None = None
    parentId: int | None = Field(default=None, validation_alias="parent_id")
    isActive: bool = Field(default=True, validation_alias="is_active")
    orderIndex: int = Field(default=0, validation_alias="order_index")
    createdAt: datetime = Field(validation_alias="created_at")
    updatedAt: datetime | None = Field(default=None, validation_alias="updated_at")
    submenu: list[SubMenuResponse] = Field(default=[], validation_alias="submenu")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class MenuListResponse(BaseModel):
    count: int
    data: list[MenuResponse]