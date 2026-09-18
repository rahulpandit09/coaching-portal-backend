from pydantic import BaseModel, ConfigDict, Field

#Create Role

class RoleCreate(BaseModel):
    name: str

#Update Role

class RoleUpdate(BaseModel):
    name: str

#Response Role

class RoleResponse(BaseModel):
    roleId: int = Field(validation_alias="id")
    name: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

#List Response
class RoleListResponse(BaseModel):
    count: int
    data: list[RoleResponse]