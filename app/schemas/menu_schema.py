from pydantic import BaseModel, ConfigDict

class MenuCreate(BaseModel):
    title: str
    path: str | None = None
    icon: str | None = None
    parent_id: int | None = None
    is_active: bool = True

class MenuUpdate(BaseModel):
    title: str | None = None
    path: str | None = None
    icon: str | None = None
    parent_id: int | None = None
    is_active: bool | None = None

class MenuResponse(BaseModel):
    id: int
    title: str
    path: str | None = None
    icon: str | None = None
    parent_id: int | None = None
    is_active: bool = True

    model_config = ConfigDict(from_attribute=True)

class MenuListResponse(BaseModel):
    count: int
    data: list[MenuResponse]