from pydantic import BaseModel, ConfigDict
from typing import Optional

class SubMenuCreate(BaseModel):
    menu_id: int
    title: str
    path: str | None = None
    icon: str | None = None
    order_index: int = 1
    status: bool = True

class SubMenuUpdate(BaseModel):
    title: str
    path: str | None = None
    icon: str | None = None
    order_index: int = 1
    status: bool = True

class MessageResponse(BaseModel):
    message: str

class SubMenuResponse(BaseModel):
    submenu_id: int
    menu_id: int
    title: str
    path: str | None = None
    icon: str | None = None
    order_index: int
    status: bool

    model_config = ConfigDict(from_attributes=True)

class SubMenuListResponse(BaseModel):
    count: int
    data: list[SubMenuResponse]