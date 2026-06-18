from pydantic import BaseModel

class LectureCreate(BaseModel):
    title: str
    video_url: str
