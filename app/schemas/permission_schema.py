from pydantic import BaseModel, ConfigDict, Field

class PermissionCreate(BaseModel):
    name: str
    code: str

class PermissionUpdate(BaseModel):
    name: str
    code: str

class PermissionResponse(BaseModel):
    permissionId: int = Field(validation_alias="id")
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class PermissionListResponse(BaseModel):
    count: int
    data: list[PermissionResponse]