from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from app.models.userManagement.parent import ParentDetail
from app.models.user import User
from app.schemas.userManagement.parent import ParentDetailCreate, ParentDetailUpdate


def get_parent_by_id(db: Session, parent_id: int) -> Optional[ParentDetail]:
    return db.query(ParentDetail).filter(ParentDetail.id == parent_id).first()


def get_parent_by_user_id(db: Session, user_id: int) -> Optional[ParentDetail]:
    return db.query(ParentDetail).filter(ParentDetail.user_id == user_id).first()


def get_all_parents(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
) -> List[ParentDetail]:
    query = db.query(ParentDetail).join(User, ParentDetail.user_id == User.id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_filter),
                User.last_name.ilike(search_filter),
                User.email.ilike(search_filter),
                ParentDetail.relationship.ilike(search_filter),
                ParentDetail.occupation.ilike(search_filter),
                ParentDetail.company_name.ilike(search_filter)
            )
        )
    return query.offset(skip).limit(limit).all()


def create_parent_detail(
    db: Session,
    user_id: int,
    parent_data: ParentDetailCreate
) -> ParentDetail:
    db_parent = ParentDetail(
        user_id=user_id,
        **parent_data.model_dump(exclude_unset=True)
    )
    db.add(db_parent)
    db.commit()
    db.refresh(db_parent)
    return db_parent


def update_parent_detail(
    db: Session,
    user_id: int,
    parent_data: ParentDetailUpdate
) -> Optional[ParentDetail]:
    db_parent = get_parent_by_user_id(db, user_id)
    if not db_parent:
        return None

    update_data = parent_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_parent, field, value)

    db.commit()
    db.refresh(db_parent)
    return db_parent


def delete_parent_detail(db: Session, user_id: int) -> bool:
    db_parent = get_parent_by_user_id(db, user_id)
    if not db_parent:
        return False

    db.delete(db_parent)
    db.commit()
    return True
