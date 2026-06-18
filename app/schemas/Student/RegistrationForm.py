from pydantic import BaseModel, EmailStr, StringConstraints
from typing import Optional, Annotated

PhoneStr = Annotated[
    str,
    StringConstraints(
        min_length=10,
        max_length=10,
        pattern="^[0-9]+$"
    )
]

class StudentCreate(BaseModel):
    fullName: str
    email: EmailStr
    phone: PhoneStr
    dob: str
    gender: str

    address: str

    course: str
    batch: str
    mode: str
    qualification: str
    school: str

    parentContact: PhoneStr
    agree: bool


class StudentResponse(BaseModel):
    id: int
    fullName: str
    email: EmailStr
    phone: PhoneStr
    dob: str
    gender: str
    address: str
    course: str
    batch: str
    mode: str
    qualification: str
    school: str
    parentContact: Optional[PhoneStr]
    agree: bool

    class Config:
        from_attributes  = True