from pydantic import BaseModel


class SidebarResponse(BaseModel):
    id: int
    title: str
    route: str
    icon: str | None

    class Config:
        from_attributes = True