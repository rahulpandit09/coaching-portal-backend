import logging
from typing import List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.dms.dms_folder_schema import (
    DmsFolderCreate,
    DmsFolderUpdate,
    DmsFolderResponse
)
from app.crud.dms.dms_folder_crud import (
    create_dms_folder,
    update_dms_folder,
    get_dms_folder,
    get_all_dms_folders,
    soft_delete_dms_folder
)
from app.crud.dms.dms_auth import verify_dms_admin, NotFoundError, get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dms-folder", tags=["DMS Folder"])


# -------------------------------------------------
# RESPONSE MODELS
# -------------------------------------------------
class FolderIdResponse(BaseModel):
    status: str = "success"
    message: str = "DMS Folder created successfully"
    folder_id: int


class MessageResponse(BaseModel):
    status: str = "success"
    message: str


class SingleFolderResponse(BaseModel):
    status: str = "success"
    data: DmsFolderResponse


class PaginatedFoldersResponse(BaseModel):
    status: str = "success"
    count: int
    total_count: int
    page: int
    limit: int
    data: List[DmsFolderResponse]


# -------------------------------------------------
# CREATE
# -------------------------------------------------
@router.post("/create", response_model=FolderIdResponse)
def create(
    data: DmsFolderCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    # verify_dms_admin(db, current_user_id, action="create folder")
    data.created_by = current_user_id
    try:
        folder_id = create_dms_folder(db, data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create DMS folder: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create DMS folder"
        )
    return {
        "status": "success",
        "message": "DMS Folder created successfully",
        "folder_id": folder_id
    }


# -------------------------------------------------
# UPDATE
# -------------------------------------------------
@router.put("/update/{folder_id}", response_model=MessageResponse)
def update(
    folder_id: int,
    data: DmsFolderUpdate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    # verify_dms_admin(db, current_user_id, action="update folder")
    data.updated_by = current_user_id
    try:
        rowcount = update_dms_folder(db, folder_id, data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update DMS folder: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to update DMS folder"
        )
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {
        "status": "success",
        "message": "DMS Folder updated successfully"
    }


# -------------------------------------------------
# GET BY ID
# -------------------------------------------------
@router.get("/get/{folder_id}", response_model=SingleFolderResponse)
def get(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_dms_folder(db, folder_id, user_id=current_user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Folder not found or access denied")
    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# GET ALL (with pagination)
# -------------------------------------------------
@router.get("/get-all", response_model=PaginatedFoldersResponse)
def get_all(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    all_results = get_all_dms_folders(db, user_id=current_user_id)
    total_count = len(all_results)
    start = (page - 1) * limit
    paginated_data = all_results[start:start + limit]
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
@router.delete("/delete/{folder_id}", response_model=MessageResponse)
def delete(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    # verify_dms_admin(db, current_user_id, action="delete folder")
    try:
        soft_delete_dms_folder(db, folder_id, deleted_by=current_user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(getattr(e, "detail", str(e))))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete DMS folder: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete DMS folder"
        )
    return {
        "status": "success",
        "message": "DMS Folder deleted successfully"
    }
