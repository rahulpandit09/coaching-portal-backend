import logging
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from app.database import get_db
from app.schemas.dms.dms_sub_folder_schema import (
    DmsSubFolderCreate,
    DmsSubFolderUpdate,
    DmsSubFolderResponse,
    DmsSubFolderMoveRequest,
    DmsSubFolderMovePreviewResponse,
    DmsSubFolderMoveResponse,
)
from app.crud.dms.dms_sub_folder_crud import (
    create_dms_sub_folder,
    update_dms_sub_folder,
    get_dms_sub_folder,
    get_all_dms_sub_folders,
    get_dms_sub_folders_by_folder,
    soft_delete_dms_sub_folder,
    get_dms_sub_folder_move_preview,
    move_dms_sub_folder,
    update_dms_sub_folder_status,
)
from app.crud.dms.dms_auth import verify_dms_admin, NotFoundError, get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dms-sub-folder", tags=["DMS Sub Folder"])


# -------------------------------------------------
# RESPONSE MODELS
# -------------------------------------------------
class SubFolderIdResponse(BaseModel):
    status: str = "success"
    message: str = "DMS Sub Folder created successfully"
    sub_folder_id: int


class MessageResponse(BaseModel):
    status: str = "success"
    message: str


class SingleSubFolderResponse(BaseModel):
    status: str = "success"
    data: DmsSubFolderResponse


class PaginatedSubFoldersResponse(BaseModel):
    status: str = "success"
    count: int
    total_count: int
    page: int
    limit: int
    data: List[DmsSubFolderResponse]


# -------------------------------------------------
# CREATE
# -------------------------------------------------
@router.post("/create", response_model=SubFolderIdResponse)
def create(
    data: DmsSubFolderCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    # verify_dms_admin(db, current_user_id, action="create sub-folder")
    data.created_by = current_user_id
    try:
        sub_folder_id = create_dms_sub_folder(db, data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create DMS sub folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create DMS sub folder")
    return {
        "status": "success",
        "message": "DMS Sub Folder created successfully",
        "sub_folder_id": sub_folder_id,
    }


# -------------------------------------------------
# UPDATE
# -------------------------------------------------
@router.put("/update/{sub_folder_id}", response_model=MessageResponse)
def update(
    sub_folder_id: int,
    data: DmsSubFolderUpdate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    # verify_dms_admin(db, current_user_id, action="update sub-folder")
    data.updated_by = current_user_id
    try:
        rowcount = update_dms_sub_folder(db, sub_folder_id, data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update DMS sub folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update DMS sub folder")
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Sub folder not found")
    return {"status": "success", "message": "DMS Sub Folder updated successfully"}


# -------------------------------------------------
# GET BY ID
# -------------------------------------------------
@router.get("/get/{sub_folder_id}", response_model=SingleSubFolderResponse)
def get(
    sub_folder_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    result = get_dms_sub_folder(db, sub_folder_id, user_id=current_user_id)
    if not result:
        raise HTTPException(
            status_code=404, detail="Sub folder not found or access denied"
        )
    return {"status": "success", "data": result}


# -------------------------------------------------
# GET ALL (with pagination)
# -------------------------------------------------
@router.get("/get-all", response_model=PaginatedSubFoldersResponse)
def get_all(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    all_results = get_all_dms_sub_folders(db, user_id=current_user_id)
    total_count = len(all_results)
    start = (page - 1) * limit
    paginated_data = all_results[start : start + limit]
    return {
        "status": "success",
        "count": len(paginated_data),
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "data": paginated_data,
    }


# -------------------------------------------------
# GET BY FOLDER ID (OR ALL IF OMITTED)
# -------------------------------------------------
@router.get(
    "/get-by-folder",
    response_model=PaginatedSubFoldersResponse,
    summary="Get sub-folders (filtered by folder_id, parent_sub_folder_id, or all if omitted)",
)
def get_by_folder(
    folder_id: Optional[int] = Query(None, description="Optional folder ID filter"),
    parent_sub_folder_id: Optional[int] = Query(
        None, description="Optional parent sub-folder ID filter to get its child sub-folders"
    ),
    flat: Optional[bool] = Query(
        False, description="Return flat list of all subfolders without tree filtering"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if folder_id is not None:
        # Verify parent folder exists and is not deleted
        parent_folder = db.execute(
            text(
                "SELECT folder_id FROM dms_folders WHERE folder_id = :folder_id AND is_deleted = FALSE"
            ),
            {"folder_id": folder_id},
        ).first()
        if not parent_folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        all_results = get_dms_sub_folders_by_folder(
            db,
            folder_id,
            parent_sub_folder_id=parent_sub_folder_id,
            user_id=current_user_id,
            flat=flat,
        )
    else:
        # If folder_id is not passed, act like get-all with folder and sub-folder data
        all_results = get_all_dms_sub_folders(db, user_id=current_user_id)

    total_count = len(all_results)
    start = (page - 1) * limit
    paginated_data = all_results[start : start + limit]
    return {
        "status": "success",
        "count": len(paginated_data),
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "data": paginated_data,
    }


# -------------------------------------------------
# SOFT DELETE
# -------------------------------------------------
@router.delete("/delete/{sub_folder_id}", response_model=MessageResponse)
def delete(
    sub_folder_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    # verify_dms_admin(db, current_user_id, action="delete sub-folder")
    try:
        soft_delete_dms_sub_folder(db, sub_folder_id, deleted_by=current_user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(getattr(e, "detail", str(e))))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete DMS sub folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete DMS sub folder")
    return {"status": "success", "message": "DMS Sub Folder deleted successfully"}


# -------------------------------------------------
# MOVE PREVIEW (GET)
# -------------------------------------------------
@router.get(
    "/move-preview/{sub_folder_id}",
    response_model=DmsSubFolderMovePreviewResponse,
    summary="Get preview before moving a sub-folder to any destination in the hierarchy",
)
def get_move_preview(
    sub_folder_id: int,
    destination_folder_id: int = Query(..., description="Target destination primary folder ID"),
    parent_sub_folder_id: Optional[int] = Query(
        None,
        description="Optional destination parent sub-folder ID at any nesting depth. Null = root of primary folder.",
    ),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    # verify_dms_admin(db, current_user_id, action="move sub-folder preview")
    data = get_dms_sub_folder_move_preview(
        db, sub_folder_id, destination_folder_id, parent_sub_folder_id=parent_sub_folder_id
    )
    return {"status": "success", "data": data}


# -------------------------------------------------
# MOVE SUB-FOLDER (POST)
# -------------------------------------------------
@router.post(
    "/move/{sub_folder_id}",
    response_model=DmsSubFolderMoveResponse,
    summary="Move sub-folder to any destination in the hierarchy (primary folder root or any nested subfolder)",
)
def move_sub_folder_endpoint(
    sub_folder_id: int,
    payload: DmsSubFolderMoveRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    # verify_dms_admin(db, current_user_id, action="move sub-folder")
    data = move_dms_sub_folder(
        db,
        sub_folder_id,
        payload.destination_folder_id,
        parent_sub_folder_id=payload.parent_sub_folder_id,
        user_id=current_user_id,
    )
    return {
        "status": "success",
        "message": "Sub-folder moved successfully",
        "data": data,
    }


# -------------------------------------------------
# STATUS CHANGE (Admin Only)
# -------------------------------------------------
@router.put(
    "/status-change/{sub_folder_id}",
    response_model=MessageResponse,
    summary="Change ACTIVE / INACTIVE status for DMS sub-folder (Admin only)",
)
def change_status(
    sub_folder_id: int,
    status: str = Query(..., description="New status: ACTIVE or INACTIVE"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    # verify_dms_admin(db, current_user_id, action="change sub-folder status")
    status_upper = status.upper().strip()
    if status_upper not in ("ACTIVE", "INACTIVE"):
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Allowed values are 'ACTIVE' or 'INACTIVE'.",
        )
    try:
        update_dms_sub_folder_status(
            db, sub_folder_id, status_upper, updated_by=current_user_id
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(getattr(e, "detail", str(e))))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update DMS sub folder status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to update DMS sub folder status"
        )
    return {"status": "success", "message": "DMS Sub Folder status updated successfully"}

