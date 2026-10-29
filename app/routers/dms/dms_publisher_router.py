import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.dms.dms_publisher_schema import (
    DmsPublisherCreate,
    DmsPublisherUpdate
)
from app.crud.dms.dms_auth import verify_dms_admin, NotFoundError, get_current_user_id
from app.crud.dms.dms_publisher_crud import (
    create_dms_publisher,
    update_dms_publisher,
    get_dms_publisher,
    get_all_dms_publishers,
    get_dms_publishers_by_user,
    soft_delete_dms_publisher,
    update_dms_publisher_status,
    get_publisher_dropdown_users,
    get_dms_publisher_dashboard_counts
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dms-publisher", tags=["DMS Publisher"])


# -------------------------------------------------
# 1. DASHBOARD COUNTS (ONE GET API FOR 4 CARDS)
# -------------------------------------------------
@router.get(
    "/dashboard-counts",
    summary="Get DMS Publisher Dashboard metrics (4 Summary Cards)"
)
def get_dashboard_counts(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_dms_publisher_dashboard_counts(db)
    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# CREATE
# -------------------------------------------------
@router.post("/create")
def create(
    data: DmsPublisherCreate,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    data.created_by = current_user_id
    # verify_dms_admin(db, current_user_id, action="create publishers and assign folder access")
    try:
        publisher_id = create_dms_publisher(db, data, background_tasks=background_tasks)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create DMS publisher: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to create DMS publisher"
        )
    return {
        "status": "success",
        "publisher_id": publisher_id
    }


# -------------------------------------------------
# UPDATE
# -------------------------------------------------
@router.put("/update/{publisher_id}")
def update(
    publisher_id: int,
    data: DmsPublisherUpdate,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    data.updated_by = current_user_id
    # verify_dms_admin(db, current_user_id, action="update publisher folder access")
    try:
        rowcount = update_dms_publisher(db, publisher_id, data, background_tasks=background_tasks)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update DMS publisher: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to update DMS publisher"
        )
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Publisher not found")
    return {
        "status": "success",
        "message": "DMS Publisher updated successfully"
    }


# -------------------------------------------------
# 2. GET BY ID
# -------------------------------------------------
@router.get("/get/{publisher_id}")
def get(
    publisher_id: int,
    format: Optional[str] = Query(None, description="Optional format: 'tree' to return folder hierarchy directly in data"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_dms_publisher(db, publisher_id)
    if not result:
        raise HTTPException(status_code=404, detail="Publisher not found")
    if format == "tree":
        return {
            "status": "success",
            "data": result.get("assigned_folders") or []
        }
    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# 3. GET PUBLISHER FOLDERS
# -------------------------------------------------
@router.get(
    "/get-folders/{publisher_id}",
    summary="Get hierarchical assigned folders for a publisher"
)
@router.get(
    "/folders/{publisher_id}",
    summary="Get hierarchical assigned folders for a publisher (alias)"
)
def get_publisher_folders(
    publisher_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_dms_publisher(db, publisher_id)
    if not result:
        raise HTTPException(status_code=404, detail="Publisher not found")
    return {
        "status": "success",
        "data": result.get("assigned_folders") or []
    }


# -------------------------------------------------
# 4. GET ALL
# -------------------------------------------------
@router.get("/get-all")
def get_all(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_all_dms_publishers(db)
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
# 5. GET ALL BY USER
# -------------------------------------------------
@router.get("/get-by-user/{user_id}")
def get_by_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_dms_publishers_by_user(db, user_id)
    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# 6. SOFT DELETE
# -------------------------------------------------
@router.delete("/delete/{publisher_id}")
def delete(
    publisher_id: int,
    deleted_by: Optional[int] = Query(None, description="User ID performing the deletion"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    acting_user = current_user_id
    # verify_dms_admin(db, acting_user, action="delete publishers")
    try:
        soft_delete_dms_publisher(db, publisher_id, acting_user)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete DMS publisher: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete DMS publisher"
        )
    return {
        "status": "success",
        "message": "DMS Publisher deleted successfully"
    }


# -------------------------------------------------
# STATUS CHANGE (ACTIVE / INACTIVE)
# -------------------------------------------------
@router.put(
    "/status-change/{publisher_id}",
    summary="Change ACTIVE / INACTIVE status for DMS publisher"
)
def change_status(
    publisher_id: int,
    status: str = Query(..., description="New status: ACTIVE or INACTIVE"),
    updated_by: Optional[int] = Query(None, description="User ID performing the status change"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    acting_user = current_user_id
    # verify_dms_admin(db, acting_user, action="change publisher status")

    try:
        result = update_dms_publisher_status(db, publisher_id, status, updated_by=acting_user)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update DMS publisher status: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to update DMS publisher status"
        )
    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# 7. GET DROPDOWN (ALL EMPLOYEES FROM USERS TABLE)
# -------------------------------------------------
@router.get(
    "/dropdown",
    summary="Get all active employees dropdown for publisher assignment"
)
def get_publishers_dropdown(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_publisher_dropdown_users(db)
    return {
        "status": "success",
        "count": len(result),
        "data": result
    }
