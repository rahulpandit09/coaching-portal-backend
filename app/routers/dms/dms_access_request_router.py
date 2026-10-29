import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from app.database import get_db
from app.schemas.dms.dms_access_request_schema import (
    DmsAccessRequestCreate,
    DmsAccessRequestUpdate,
    DmsAccessRequestAction
)
from app.crud.dms.dms_access_request_crud import (
    create_dms_access_request,
    update_dms_access_request,
    action_dms_access_request,
    get_dms_access_request,
    get_all_dms_access_requests,
    get_dms_access_request_counts,
    soft_delete_dms_access_request
)
from app.crud.dms.dms_auth import (
    is_user_dms_admin,
    is_user_folder_publisher,
    get_user_dms_folder_access,
    NotFoundError,
    get_current_user_id
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dms-access-request", tags=["DMS Access & Custody Requests"])


# -------------------------------------------------
# CREATE
# -------------------------------------------------
@router.post("/create", summary="Create a new access & custody request")
def create(
    data: DmsAccessRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    data.requester_id = current_user_id
    data.created_by = current_user_id
    try:
        request_id = create_dms_access_request(db, data, background_tasks=background_tasks)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create DMS access request: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to create DMS access request"
        )
    return {
        "status": "success",
        "message": "DMS access request created successfully",
        "request_id": request_id
    }


# -------------------------------------------------
# UPDATE
# -------------------------------------------------
@router.put("/update/{request_id}", summary="Update an access request")
def update(
    request_id: int,
    data: DmsAccessRequestUpdate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    existing = get_dms_access_request(db, request_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Access request not found")

    # Restrict update to the requester or an Admin
    is_admin = is_user_dms_admin(db, current_user_id)
    if not is_admin and existing.get("requester_id") != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Permission denied: You can only update your own access requests, unless you are an Admin."
        )

    # Restrict update to PENDING requests
    curr_status = (existing.get("status") or "").upper()
    if curr_status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update request: Request is currently in '{existing.get('status')}' status, but only PENDING requests can be updated."
        )

    data.updated_by = current_user_id
    try:
        rowcount = update_dms_access_request(db, request_id, data)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update DMS access request: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to update DMS access request"
        )
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Access request not found")
    return {
        "status": "success",
        "message": "DMS access request updated successfully"
    }


# -------------------------------------------------
# ACTION (APPROVE / REJECT)
# -------------------------------------------------
@router.patch("/action/{request_id}", summary="Approve or Reject an access request")
def action(
    request_id: int,
    data: DmsAccessRequestAction,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    existing = get_dms_access_request(db, request_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Access request not found")

    # Only pending requests can be approved or rejected
    curr_status = (existing.get("status") or "").upper().strip()
    if curr_status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot action request: Request is currently in '{existing.get('status')}' status, but only PENDING requests can be approved or rejected."
        )

    # Document publisher/custodian, assigned folder publisher, or DMS Admin only
    is_admin = is_user_dms_admin(db, current_user_id)
    if not is_admin:
        doc_id = existing.get("document_id")
        doc = db.execute(
            text("SELECT document_id, created_by, custodian_id, folder_id, sub_folder_id FROM dms_documents WHERE document_id = :doc_id AND is_deleted = FALSE"),
            {"doc_id": doc_id}
        ).mappings().first()

        is_publisher = doc and (doc.get("created_by") == current_user_id or doc.get("custodian_id") == current_user_id)
        if not is_publisher and doc:
            is_publisher = is_user_folder_publisher(db, current_user_id, doc.get("folder_id"), doc.get("sub_folder_id"))

        if not is_publisher:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: Only DMS Admins, the document's publisher/custodian, or assigned folder publishers can approve or reject access requests."
            )

    # Requesters cannot approve or reject their own access requests (separation of duties)
    if existing.get("requester_id") == current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Permission denied: Requesters cannot approve or reject their own access requests."
        )

    # Do not trust data.reviewed_by or reviewed_by_name supplied by the client; bind reviewer ID to authenticated user
    data.reviewed_by = current_user_id
    data.reviewed_by_name = None

    try:
        rowcount = action_dms_access_request(db, request_id, data, background_tasks=background_tasks)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to process DMS access request action: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to process DMS access request action"
        )
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Access request not found or is no longer pending")

    status_upper = (data.status or "").upper()
    action_verb = "approved" if status_upper in ("APPROVE", "APPROVED") else "rejected"
    return {
        "status": "success",
        "message": f"DMS access request {action_verb} successfully"
    }


# -------------------------------------------------
# COUNTS SUMMARY (FOR UI TABS)
# -------------------------------------------------
@router.get("/counts", summary="Get request counts by status for UI tabs")
def get_counts(
    scope: Optional[str] = Query(None, description="'my_requests' or 'approvals'"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    if scope == "my_requests":
        result = get_dms_access_request_counts(db, requester_id=current_user_id)
    else:
        # Default view for this module: only access requests for documents published by the current user
        result = get_dms_access_request_counts(db, publisher_user_id=current_user_id)
    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# GET BY ID
# -------------------------------------------------
@router.get("/get/{request_id}", summary="Get access request by ID")
def get_by_id(
    request_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    result = get_dms_access_request(db, request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Access request not found")

    # Requesters can see their own requests.
    # Document publishers/custodians can see requests for their documents.
    if result.get("requester_id") != current_user_id:
        doc_id = result.get("document_id")
        doc = db.execute(
            text("SELECT document_id, created_by, custodian_id, folder_id, sub_folder_id FROM dms_documents WHERE document_id = :doc_id AND is_deleted = FALSE"),
            {"doc_id": doc_id}
        ).mappings().first()
        is_publisher = doc and (doc.get("created_by") == current_user_id or doc.get("custodian_id") == current_user_id)
        if not is_publisher and doc:
            is_publisher = is_user_folder_publisher(db, current_user_id, doc.get("folder_id"), doc.get("sub_folder_id"), is_admin=False, is_unrestricted=False)
        if not is_publisher:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only view your own access requests or requests for documents you published or have publisher privileges for."
            )

    return {
        "status": "success",
        "data": result
    }


# -------------------------------------------------
# GET ALL (with pagination & ownership isolation)
# -------------------------------------------------
@router.get("/get-all", summary="Get all access requests with filters")
def get_all(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED, ALL)"),
    document_id: Optional[int] = Query(None, description="Filter by document ID"),
    requester_id: Optional[int] = Query(None, description="Filter by requester user ID"),
    search: Optional[str] = Query(None, description="Search requester name, doc number, doc title, or justification"),
    scope: Optional[str] = Query(None, description="'my_requests' to view requests you submitted, 'approvals' to view requests for documents you published"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    if scope == "my_requests":
        effective_requester_id = current_user_id
        publisher_user_id = None
    else:
        # Default view: only access requests for documents published by the current user
        publisher_user_id = current_user_id
        effective_requester_id = requester_id

    all_results = get_all_dms_access_requests(
        db,
        status=status,
        document_id=document_id,
        requester_id=effective_requester_id,
        publisher_user_id=publisher_user_id,
        search=search
    )
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
# SOFT DELETE / CANCEL
# -------------------------------------------------
@router.delete("/delete/{request_id}", summary="Soft delete or cancel an access request")
def delete(
    request_id: int,
    deleted_by: Optional[int] = Query(None, description="Optional override user ID performing the deletion"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    existing = get_dms_access_request(db, request_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Access request not found")

    is_admin = is_user_dms_admin(db, current_user_id)
    acting_user = current_user_id
    if is_admin and deleted_by is not None:
        acting_user = deleted_by

    # Non-admins can only delete/cancel their own PENDING requests
    if not is_admin:
        if existing.get("requester_id") != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: You can only delete or cancel your own access requests."
            )
        curr_status = (existing.get("status") or "").upper()
        if curr_status != "PENDING":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete request: Request is in '{existing.get('status')}' status. Requesters can only cancel PENDING requests."
            )

    try:
        rowcount = soft_delete_dms_access_request(db, request_id, acting_user)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete DMS access request: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete DMS access request"
        )
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Access request not found")
    return {
        "status": "success",
        "message": "DMS access request deleted successfully"
    }
