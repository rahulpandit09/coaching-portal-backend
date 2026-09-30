from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class RolePermission(Base):
    __tablename__ = "role_permission"

    id = Column(Integer, primary_key=True, index=True)

    role_id = Column(
        Integer,
        ForeignKey("role.id"),
        nullable=False
    )

    permission_id = Column(
        Integer,
        ForeignKey("permission.id"),
        nullable=False
    )

    role = relationship(
        "Role",
        back_populates="permissions"
    )

    permission = relationship(
        "Permission",
        back_populates="roles"
    )