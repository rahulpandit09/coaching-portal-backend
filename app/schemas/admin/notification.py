from pydantic import BaseModel
from typing import Optional

class NotificationCreate(BaseModel):
    title: str
    message: str
    role: Optional[str] = None
    user_id: Optional[int] = None
    batch_id: Optional[int] = None