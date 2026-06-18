from pydantic import BaseModel

class EnrollRequest(BaseModel):
    course_id: int
