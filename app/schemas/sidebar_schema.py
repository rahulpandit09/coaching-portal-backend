from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List

class SidebarSubmenuResponse(BaseModel):
    subMenuId: int = Field(validation_alias="id")
    title: str
    path: Optional[str] = None
    icon: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class SidebarResponse(BaseModel):
    menuId: int = Field(validation_alias="id")
    title: str
    path: Optional[str] = None
    icon: Optional[str] = None
    child: List[SidebarSubmenuResponse] = Field(default=[], alias="submenu")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class SidebarListResponse(BaseModel):
    count: int
    data: List[SidebarResponse]