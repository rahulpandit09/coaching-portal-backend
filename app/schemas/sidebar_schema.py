from pydantic import BaseModel
from typing import Optional, List

class SidebarResponse(BaseModel):
    id: int
    title: str
    route: Optional[str]
    icon: Optional[str]
    child: Optional[List['SidebarResponse']] = []
    
    class Config:
        from_attributes = True

class SidebarListResponse(BaseModel):
    count: int
    data: List[SidebarListResponse]