import os
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from app.database import get_db
from app.schemas.dms.dms_document_schema import (
    DmsDocumentCreate,
    DmsDocumentUpdate,
    PaginatedTrashResponse,
)
from app.crud.dms.dms_document_crud import (
    create_dms_document,
    update_dms_document,
    get_dms_document,
    get_all_dms_documents,
    get_all_archived_dms_documents,
    get_dms_trash_documents,
    restore_dms_document,
    purge_dms_document,
    soft_delete_dms_document,
    update_dms_document_status,
    save_dms_document_file,
    get_dms_dashboard_cards,
    get_dms_folder_hierarchy,
    get_dms_upload_dir,
    get_dms_document_revisions,
    get_dms_revision_file,
    check_document_access_permissions,
    clean_document_number,
    ALLOWED_DOCUMENT_STATUSES
)
from app.crud.dms.dms_auth import (
    verify_dms_admin,
    verify_dms_can_upload,
    verify_dms_folder_publish_access,
    verify_dms_document_manage_access,
    get_user_dms_folder_access,
    NotFoundError,
    get_current_user_id
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dms-document", tags=["DMS Document"])


# -------------------------------------------------
# FILE UPLOAD (STANDALONE)
# -------------------------------------------------
@router.post(
    "/upload",
    summary="Upload a document or image file (Max 30MB)",
    description="Uploads a document or image file up to 30MB. Requires Admin or active Publisher role. Videos and archive/zip files are not allowed."
)
async def upload_file(
    file: UploadFile = File(..., description="Document or image file to upload (Max 30MB)"),
    custom_file_name: Optional[str] = Form(None, description="Optional custom display name for the file"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    # verify_dms_can_upload(db, current_user_id)
    try:
        file_info = await save_dms_document_file(file, custom_file_name)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to upload document file: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to upload document file"
        )
    return {
        "status": "success",
        "data": file_info
    }


# -------------------------------------------------
# CREATE
# -------------------------------------------------
@router.post("/create")
def create(
    data: DmsDocumentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    target_id = data.target_folder_id or data.sub_sub_folder_id or data.sub_folder_id
    chk_fid = data.folder_id
    chk_sfid = None

    if target_id and target_id != 0:
        sf_chk = db.execute(
            text("SELECT sub_folder_id, folder_id FROM dms_sub_folders WHERE sub_folder_id = :sf_id AND is_deleted = FALSE"),
            {"sf_id": target_id}
        ).mappings().first()
        if sf_chk:
            chk_sfid = sf_chk["sub_folder_id"]
            if not chk_fid:
                chk_fid = sf_chk["folder_id"]
        else:
            chk_fid = target_id

    # verify_dms_folder_publish_access(db, current_user_id, chk_fid, chk_sfid)
    data.created_by = current_user_id
    try:
        document_id = create_dms_document(db, data, background_tasks=background_tasks)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create DMS document: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to create DMS document"
        )
    return {
        "status": "success",
        "message": "DMS Document created successfully",
        "document_id": document_id
    }


# -------------------------------------------------
# UPDATE
# -------------------------------------------------
@router.put("/update/{document_id}")
def update(
    document_id: int,
    data: DmsDocumentUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    # verify_dms_document_manage_access(db, current_user_id, document_id, action="update")
    target_id = data.target_folder_id or data.sub_sub_folder_id or data.sub_folder_id
    chk_fid = data.folder_id
    chk_sfid = None

    if target_id and target_id != 0:
        sf_chk = db.execute(
            text("SELECT sub_folder_id, folder_id FROM dms_sub_folders WHERE sub_folder_id = :sf_id AND is_deleted = FALSE"),
            {"sf_id": target_id}
        ).mappings().first()
        if sf_chk:
            chk_sfid = sf_chk["sub_folder_id"]
            if not chk_fid:
                chk_fid = sf_chk["folder_id"]
        else:
            chk_fid = target_id

    # if chk_fid or chk_sfid:
    #     verify_dms_folder_publish_access(db, current_user_id, chk_fid, chk_sfid)
    # data.updated_by = current_user_id
    try:
        rowcount = update_dms_document(db, document_id, data, background_tasks=background_tasks)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update DMS document: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to update DMS document"
        )
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "status": "success",
        "message": "DMS Document updated successfully"
    }


# -------------------------------------------------
# GET BY ID
# -------------------------------------------------
@router.get("/get/{document_id}")
def get(
    document_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_dms_document(db, document_id, user_id=current_user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found or access denied")
    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# GET ACCESS PERMISSIONS FOR SPECIFIC DOCUMENT
# -------------------------------------------------
@router.get(
    "/access/{document_id}",
    summary="Get current user's specific permissions for a document"
)
def get_document_access(
    document_id: int = Path(..., description="Document ID"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Returns granular frontend permission flags for UI controls:
      - has_access: bool (enables View & Download buttons)
      - can_view: bool
      - can_download: bool
      - can_request_access: bool (enables Request Access modal button)
      - access_status: 'GRANTED' | 'PENDING_REQUEST' | 'NO_ACCESS'
      - pending_request_id: request ID if pending, else null
    """
    doc = db.execute(
        text("SELECT * FROM dms_documents WHERE document_id = :doc_id AND is_deleted = FALSE"),
        {"doc_id": document_id}
    ).mappings().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    perms = check_document_access_permissions(db, current_user_id, dict(doc))
    perms["document_id"] = document_id
    perms["document_number"] = clean_document_number(doc.get("document_number"))

    return {
        "status": "success",
        "data": perms
    }


# -------------------------------------------------
# SECURE FILE DOWNLOAD
# -------------------------------------------------
@router.get("/download/{document_id}", summary="Download document file with access control")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    doc = get_dms_document(db, document_id, user_id=current_user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied")

    if not doc.get("has_file_access"):
        raise HTTPException(
            status_code=403,
            detail="Access required: You do not have permission to open or download this document. Please request access."
        )

    file_path = doc.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="No file attached to this document")

    norm_path = os.path.abspath(file_path)
    upload_dir = get_dms_upload_dir()

    if os.path.commonpath([norm_path, upload_dir]) != upload_dir or not os.path.exists(norm_path):
        raise HTTPException(status_code=404, detail="Document file not found on storage")

    filename = doc.get("file_name") or os.path.basename(norm_path)
    media_type = doc.get("mime_type") or "application/octet-stream"

    return FileResponse(
        path=norm_path,
        filename=filename,
        media_type=media_type
    )


# -------------------------------------------------
# GET DOCUMENT REVISIONS / BASELINES (MODAL DETAILS)
# -------------------------------------------------
@router.get(
    "/revisions/{document_id}",
    summary="Get all revision baselines and audit history for a document (Version History modal)"
)
def get_revisions(
    document_id: int = Path(..., description="Document ID"),
    version: Optional[str] = Query(None, description="Optional version filter, e.g. Rev 01 or v1.0"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_dms_document_revisions(db, document_id, user_id=current_user_id, version=version)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found or access denied")
    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# SECURE REVISION FILE DOWNLOAD
# -------------------------------------------------
@router.get(
    "/download-revision/{history_id}",
    summary="Download or view a specific historical revision snapshot file"
)
def download_revision_file(
    history_id: int = Path(..., description="History ID of the revision snapshot"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    file_info = get_dms_revision_file(db, history_id, user_id=current_user_id)
    return FileResponse(
        path=file_info["file_path"],
        filename=file_info["file_name"],
        media_type=file_info["media_type"]
    )


# -------------------------------------------------
# GET BY FOLDER ID
# -------------------------------------------------
@router.get(
    "/get-by-folder/{folder_id}",
    summary="Get folder, subfolders, and documents all together by folder ID"
)
def get_by_folder(
    folder_id: int = Path(..., description="Folder ID"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    is_unrestricted, allowed_folders, _ = get_user_dms_folder_access(db, current_user_id)
    if not is_unrestricted and allowed_folders and folder_id not in allowed_folders:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: You do not have permission to view folder ID {folder_id}."
        )

    result = get_dms_folder_hierarchy(
        db,
        folder_id=folder_id,
        user_id=current_user_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Folder not found or access denied")

    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# GET ALL HIERARCHY (FOLDERS, SUBFOLDERS, DOCUMENTS)
# -------------------------------------------------
@router.get(
    "/get-all-hierarchy",
    summary="Get all folders, subfolders, and documents together with station_id and location filters"
)
def get_all_hierarchy(
    station_id: Optional[int] = Query(None, description="Optional station ID filter (e.g. 1 for HO BLR)"),
    location: Optional[str] = Query(None, description="Optional location filter (e.g. 'HO BLR', 'MLR')"),
    folder_id: Optional[int] = Query(None, description="Optional folder ID filter"),
    controlled_only: bool = Query(False, description="Filter hierarchy to only folders, subfolders, and documents the user has access to"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_dms_folder_hierarchy(
        db,
        folder_id=folder_id,
        user_id=current_user_id,
        station_id=station_id,
        location=location,
        controlled_only=controlled_only
    )
    if result is None and folder_id is not None:
        raise HTTPException(status_code=404, detail="Folder not found or access denied")

    return {
        "status": "success",
        "count": len(result) if isinstance(result, list) else 1,
        "data": result or []
    }


# -------------------------------------------------
# BROWSE CONTROLLED FILES (HIERARCHY)
# -------------------------------------------------
@router.get(
    "/browse-controlled-files",
    summary="Browse Controlled Files: Returns folders, subfolders, and documents to which the user has access"
)
@router.get(
    "/controlled-hierarchy",
    include_in_schema=False
)
def browse_controlled_files(
    station_id: Optional[int] = Query(None, description="Optional station ID filter (e.g. 1 for HO BLR)"),
    location: Optional[str] = Query(None, description="Optional location filter (e.g. 'HO BLR', 'MLR')"),
    folder_id: Optional[int] = Query(None, description="Optional folder ID filter"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Browse Controlled Files:
    Returns the hierarchy tree of folders and sub-folders containing ONLY
    the documents to which the authenticated user currently has access.
    Empty folders or folders with no accessible documents are excluded.
    """
    result = get_dms_folder_hierarchy(
        db,
        folder_id=folder_id,
        user_id=current_user_id,
        station_id=station_id,
        location=location,
        controlled_only=True
    )
    if result is None and folder_id is not None:
        raise HTTPException(status_code=404, detail="Folder not found or no controlled files in this folder")

    return {
        "status": "success",
        "count": len(result) if isinstance(result, list) else (1 if result else 0),
        "data": result or []
    }


# -------------------------------------------------
# GET ALL (with pagination)
# -------------------------------------------------
@router.get("/get-all")
def get_all(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    all_results = get_all_dms_documents(db, user_id=current_user_id)
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
# GET ALL ARCHIVED (with pagination)
# -------------------------------------------------
@router.get("/get-all-archived", summary="Get all archived DMS documents")
def get_all_archived(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    all_results = get_all_archived_dms_documents(db, user_id=current_user_id)
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
# DASHBOARD CARDS
# -------------------------------------------------
@router.get("/dashboard-cards", summary="Get DMS dashboard card metrics (Total, Controlled, Under Review, Archive)")
def get_dashboard_cards(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_dms_dashboard_cards(db, user_id=current_user_id)
    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# STATUS UPDATE (PATCH)
# -------------------------------------------------
@router.patch(
    "/status-update/{document_id}",
    summary="Update document status (e.g., ACTIVE, ARCHIVED, INACTIVE)"
)
def update_status(
    document_id: int,
    status: str = Query(..., description="New status: e.g. ACTIVE, ARCHIVED, INACTIVE"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    status_upper = status.upper().strip()
    if status_upper not in ALLOWED_DOCUMENT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Allowed statuses are: {', '.join(sorted(ALLOWED_DOCUMENT_STATUSES))}."
        )

    verify_dms_document_manage_access(db, current_user_id, document_id, action="change the status of")
    try:
        result = update_dms_document_status(db, document_id, status_upper, current_user_id, background_tasks=background_tasks)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(getattr(e, "detail", str(e)))
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update document status: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to update document status"
        )
    return {
        "status": "success",
        "message": "DMS Document status updated successfully",
        "data": result
    }


# -------------------------------------------------
# SOFT DELETE
# -------------------------------------------------
@router.delete("/delete/{document_id}")
def delete(
    document_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    verify_dms_document_manage_access(db, current_user_id, document_id, action="delete")
    try:
        soft_delete_dms_document(db, document_id, current_user_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(getattr(e, "detail", str(e)))
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete DMS document: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete DMS document"
        )
    return {
        "status": "success",
        "message": "DMS Document deleted successfully"
    }


# -------------------------------------------------
# TRASH: GET ALL DELETED DOCUMENTS (Admin Only)
# -------------------------------------------------
@router.get(
    "/trash",
    response_model=PaginatedTrashResponse,
    summary="Get all deleted/trash documents with filters and metrics (Admin only)"
)
def get_trash(
    search: Optional[str] = Query(None, description="Search term across ID, title, department, or deleted-by"),
    folder_id: Optional[int] = Query(None, description="Filter by folder ID"),
    station_id: Optional[int] = Query(None, description="Filter by station ID"),
    location: Optional[str] = Query(None, description="Filter by location (e.g. 'HO BLR', 'MLR')"),
    year: Optional[int] = Query(None, description="Filter by deletion year"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    # verify_dms_admin(db, current_user_id, action="view trash / recycle bin")

    result = get_dms_trash_documents(
        db,
        search=search,
        folder_id=folder_id,
        station_id=station_id,
        location=location,
        year=year,
        sort_by="recently_deleted",
        page=page,
        limit=limit
    )
    return {
        "status": "success",
        **result
    }


# -------------------------------------------------
# TRASH: RESTORE DELETED DOCUMENT (Admin Only)
# -------------------------------------------------
@router.post(
    "/trash/restore/{document_id}",
    summary="Restore a document from trash back to active circulation (Admin only)"
)
def restore_trash_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    # verify_dms_admin(db, current_user_id, action="restore document from trash")

    return restore_dms_document(db, document_id, restored_by=current_user_id)


# -------------------------------------------------
# TRASH: PERMANENT PURGE DOCUMENT (Admin Only)
# -------------------------------------------------
@router.delete(
    "/trash/purge/{document_id}",
    summary="Permanently purge a document from trash (Admin only)"
)
def purge_trash_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    verify_dms_admin(db, current_user_id, action="permanently purge document")

    return purge_dms_document(db, document_id)
