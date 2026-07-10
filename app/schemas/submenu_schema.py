from pydantic import BaseModel, ConfigDict

class SubMenuCreate(BaseModel):
    menu_id: int
    title: str
    path: str | None = None
    icon: str | None = None
    order_index: int = 1
    status: bool = True
    parent_id: int

class subMenuUpdate(BaseModel):
    title: str
    path: str | None = None
    icon: str | None = None
    order_index: int = 1
    status: bool = True

class subMenuResponse(BaseModel):
    id: int
    menu_id: int
    title: str
    path: str | None = None
    icon: str | None = None
    order_index: int
    status: bool

    model_config = ConfigDict(from_attribute=True)

class SubMenuListResponse(BaseModel):
    count: int
    data: list[subMenuResponse]