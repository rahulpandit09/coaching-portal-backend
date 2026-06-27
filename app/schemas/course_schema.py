from pydantic import BaseModel
from typing import Optional
from datetime import datetime 

class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    duration: Optional[int] = None
    level: Optional[str] = None        
    is_active: Optional[bool] = True


class CourseResponse(CourseCreate):
    id: int
    created_at: datetime               

    class Config:
        from_attributes = True












# from pydantic import BaseModel
# from typing import Optional

# class CourseCreate(BaseModel):
#     title: str
#     description: Optional[str] = None
#     price:float

# class CourseResponse(CourseCreate):
#     id:int

# class Config:
#         from_attribute = True
