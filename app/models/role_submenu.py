from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class RoleSubMenu(Base):
    __tablename__ = "role_submenu"

    id = Column(Integer, primary_key=True, index=True)

    role_id = Column(
        Integer,
        ForeignKey("role.id"),
        nullable=False
    )

    submenu_id = Column(
        Integer,
        ForeignKey("submenu.id"),
        nullable=False
    )

    role = relationship(
        "Role",
        back_populates="role_submenus"
    )

    submenu = relationship(
        "SubMenu",
        back_populates="roles"
    )


