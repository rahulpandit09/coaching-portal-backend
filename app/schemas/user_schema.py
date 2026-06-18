# from pydantic import BaseModel, EmailStr, Field

# class UserCreate(BaseModel):
#     username: str
#     email: EmailStr
#     password: str = Field(min_length=6, max_length=72)
#     role: str

# class UserOut(BaseModel):
#     id: int
#     full_name: str
#     email: EmailStr
#     role: str

#     class Config:
#         from_attributes = True


from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)

class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True
