from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


# Create Role
class RoleCreate(BaseModel):
    name: str


# Update Role
class RoleUpdate(BaseModel):
    name: str


# Response Role
class RoleResponse(BaseModel):
    roleId: int = Field(validation_alias="id")
    name: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# List Response
class RoleListResponse(BaseModel):
    count: int
    data: list[RoleResponse]


# Role Access Schemas
class RoleAccessSubMenuResponse(BaseModel):
    subMenuId: int = Field(validation_alias="id")
    title: str
    path: Optional[str] = None
    icon: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RoleAccessMenuResponse(BaseModel):
    menuId: int = Field(validation_alias="id")
    title: str
    path: Optional[str] = None
    icon: Optional[str] = None
    subMenus: list[RoleAccessSubMenuResponse] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RoleAccessPermissionResponse(BaseModel):
    permissionId: int = Field(validation_alias="id")
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RoleAccessResponse(BaseModel):
    roleId: int
    roleName: str
    menus: list[RoleAccessMenuResponse] = []
    permissions: list[RoleAccessPermissionResponse] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RoleAccessUpdate(BaseModel):
    menuIds: list[int] = []
    subMenuIds: list[int] = []
    permissionIds: list[int] = []