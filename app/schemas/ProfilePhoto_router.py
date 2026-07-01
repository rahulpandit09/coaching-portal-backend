from pydantic import BaseModel
from typing import Optional


class ProfileResponse(BaseModel):
    role_id: int
    full_name: str
    email: str
    profile_image: Optional[str]

    class Config:
        from_attributes = True