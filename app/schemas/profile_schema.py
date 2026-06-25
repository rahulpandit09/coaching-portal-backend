from pydantic import BaseModel
from typing import Optional

class ProfileUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None