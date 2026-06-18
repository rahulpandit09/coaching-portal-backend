from pydantic import BaseModel
from typing import Optional
from datetime import datetime  # ✅ FIX 1

class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    duration: Optional[int] = None
    level: Optional[str] = None        # ✅ FIX 2 (leave → level)
    is_active: Optional[bool] = True


class CourseResponse(CourseCreate):
    id: int
    created_at: datetime               # ✅ FIX 3

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
