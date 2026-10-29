import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.dms.dms_group_schema import (
    DmsGroupCreate,
    DmsGroupUpdate
)
from app.crud.dms.dms_auth import NotFoundError, get_current_user_id
from app.crud.dms.dms_group_crud import (
    create_dms_group,
    update_dms_group,
    get_dms_group,
    get_all_dms_groups,
    soft_delete_dms_group,
    get_engineer_dropdown_users,
    get_dms_group_dashboard_counts
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dms-group", tags=["DMS Group"])


# -------------------------------------------------
# DASHBOARD COUNTS (ONE GET API FOR 4 CARDS)
# -------------------------------------------------
@router.get(
    "/dashboard-counts",
    summary="Get DMS Engineer Groups Dashboard metrics (4 Summary Cards)"
)
def get_dashboard_counts(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_dms_group_dashboard_counts(db)
    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# CREATE
# -------------------------------------------------
@router.post("/create")
def create(
    data: DmsGroupCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    data.created_by = current_user_id
    try:
        group_id = create_dms_group(db, data)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create DMS group: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to create DMS group"
        )
    return {
        "status": "success",
        "group_id": group_id
    }


# -------------------------------------------------
# UPDATE
# -------------------------------------------------
@router.put("/update/{group_id}")
def update(
    group_id: int,
    data: DmsGroupUpdate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    data.updated_by = current_user_id
    try:
        rowcount = update_dms_group(db, group_id, data)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update DMS group: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to update DMS group"
        )
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Group not found")
    return {
        "status": "success",
        "message": "DMS Group updated successfully"
    }


# -------------------------------------------------
# GET BY ID
# -------------------------------------------------
@router.get("/get/{group_id}")
def get(
    group_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_dms_group(db, group_id)
    if not result:
        raise HTTPException(status_code=404, detail="Group not found")
    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# GET ALL
# -------------------------------------------------
@router.get("/get-all")
def get_all(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_all_dms_groups(db)
    total_count = len(result)
    start = (page - 1) * limit
    paginated_data = result[start:start + limit]
    return {
        "status": "success",
        "count": len(paginated_data),
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "data": paginated_data
    }


# -------------------------------------------------
# SOFT DELETE
# -------------------------------------------------
@router.delete("/delete/{group_id}")
def delete(
    group_id: int,
    deleted_by: Optional[int] = Query(None, description="User ID performing the deletion"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    acting_user = current_user_id
    try:
        soft_delete_dms_group(db, group_id, acting_user)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete DMS group: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete DMS group"
        )
    return {
        "status": "success",
        "message": "DMS Group deleted successfully"
    }


# -------------------------------------------------
# GET DROPDOWN (ENGINEERS WITH MODULE ACCESS)
# -------------------------------------------------
@router.get("/dropdown")
def get_engineers_dropdown(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_engineer_dropdown_users(db)
    return {
        "status": "success",
        "count": len(result),
        "data": result
    }
