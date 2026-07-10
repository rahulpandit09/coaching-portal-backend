from pydantic import BaseModel, ConfigDict

class PermissionCreate(BaseModel):
    name: str
    code: str

class PermissionUpdate(BaseModel):
    name: str
    code: str

class PermissionResponse(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attribute=True)

class PermissionListResponse(BaseModel):
    count: int
    data: list[PermissionResponse]