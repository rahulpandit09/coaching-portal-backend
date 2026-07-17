from pydantic import BaseModel, ConfigDict

#Create Role

class RoleCreate(BaseModel):
    name: str

#Update Role

class RoleUpdate(BaseModel):
    name: str

#Response Role

class RoleResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attribute=True)

#List Response
class RoleListResponse(BaseModel):
    count: int
    data: list[RoleResponse]