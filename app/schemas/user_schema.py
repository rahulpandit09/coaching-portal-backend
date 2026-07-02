from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)

class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True
