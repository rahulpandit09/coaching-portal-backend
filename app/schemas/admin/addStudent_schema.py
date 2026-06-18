from pydantic import BaseModel
from datetime import date


class StudentCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None
    address: str | None = None
    course: str
    batch: str
    admission_date: date | None = None
    total_fees: float
    paid_amount: float
    payment_mode: str | None = None
    comments: str | None = None
