import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.sql import text, bindparam

from app.schemas.dms.dms_access_request_schema import (
    DmsAccessRequestCreate,
    DmsAccessRequestUpdate,
    DmsAccessRequestAction
)
from app.crud.dms.dms_auth import NotFoundError, get_user_dms_folder_access
from app.crud.dms.dms_document_crud import clean_document_number
from app.utils.time_utils import to_iso_ist, IST

logger = logging.getLogger(__name__)


def _parse_datetime(d: Any) -> Optional[datetime]:
    """Parse date or string into datetime object."""
    if not d:
        return None
    if isinstance(d, datetime):
        return d
    if isinstance(d, date):
        return datetime.combine(d, datetime.min.time())
    if isinstance(d, str):
        try:
            return datetime.fromisoformat(d.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def _format_row(row: dict) -> dict:
    """Format row datetime/date fields to ISO IST strings."""
    d = dict(row)
    d["created_at"] = to_iso_ist(d.get("created_at"))
    d["updated_at"] = to_iso_ist(d.get("updated_at"))
    d["requested_on"] = to_iso_ist(d.get("requested_on"))
    d["reviewed_at"] = to_iso_ist(d.get("reviewed_at"))
    if d.get("valid_from"):
        d["valid_from"] = str(d["valid_from"])
    if d.get("valid_to"):
        d["valid_to"] = str(d["valid_to"])
    if d.get("document_number") and isinstance(d["document_number"], str):
        d["document_number"] = clean_document_number(d["document_number"])
    return d


# ==============================================================================
# MAIN CRUD OPERATIONS
# ==============================================================================

# -------------------------------------------------
# 1. CREATE ACCESS REQUEST
# -------------------------------------------------
def create_dms_access_request(
    db: Session,
    data: DmsAccessRequestCreate,
    background_tasks: Optional[BackgroundTasks] = None,
) -> int:
    """Create a new access request in master table and log initial snapshot in history."""
    payload = data.model_dump()

    doc_id = payload.get("document_id")
    if not doc_id:
        raise ValueError("document_id is required to create an access request.")

    # 1. Validate that the document exists and isn't deleted
    doc = db.execute(
        text("""
            SELECT document_id, document_number, document_title, security_classification, confidential_document 
            FROM dms_documents 
            WHERE document_id = :doc_id AND is_deleted = FALSE
        """),
        {"doc_id": doc_id}
    ).mappings().first()
    if not doc:
        raise ValueError("Invalid document_id: Document does not exist or has been deleted.")

    # Access requests are not applicable for confidential documents (per governance rules)
    is_conf = bool(doc.get("confidential_document"))
    sec_class = (doc.get("security_classification") or "").upper()
    if is_conf or sec_class in ("CONFIDENTIAL", "SECRET", "RESTRICTED"):
        raise ValueError("Access requests are not applicable for confidential documents. Access is assigned directly by the publisher.")

    # 2. Always resolve document details & security classification from the document, not client
    payload["document_number"] = clean_document_number(doc.get("document_number"))
    payload["document_title"] = doc.get("document_title")
    payload["security_classification"] = doc.get("security_classification")

    # 3. Block client-set status on create (always force PENDING)
    payload["status"] = "PENDING"

    # 4. Prevent duplicate pending requests for the same user and document
    req_id = payload.get("requester_id")
    if req_id:
        existing_pending = db.execute(
            text("""
                SELECT request_id FROM dms_access_requests
                WHERE requester_id = :req_id
                  AND document_id = :doc_id
                  AND UPPER(status) = 'PENDING'
                  AND is_deleted = FALSE
            """),
            {"req_id": req_id, "doc_id": doc_id}
        ).first()
        if existing_pending:
            raise ValueError("A pending access request already exists for this document by this requester.")

    # Auto-resolve requester details from users if not provided
    if req_id and not payload.get("requester_name"):
        user = db.execute(
            text("SELECT TRIM(CONCAT_WS(' ', first_name, last_name)) AS full_name, designation FROM users WHERE id = :uid"),
            {"uid": req_id}
        ).mappings().first()
        if user:
            payload["requester_name"] = user.get("full_name")
            if not payload.get("requester_designation"):
                payload["requester_designation"] = user.get("designation")

    insert_master = text("""
        INSERT INTO dms_access_requests (
            requester_id,
            requester_name,
            requester_designation,
            requester_department,
            document_id,
            document_number,
            document_title,
            security_classification,
            justification,
            status,
            permission_model,
            valid_from,
            valid_to,
            is_deleted,
            created_by
        )
        VALUES (
            :requester_id,
            :requester_name,
            :requester_designation,
            :requester_department,
            :document_id,
            :document_number,
            :document_title,
            :security_classification,
            :justification,
            'PENDING',
            COALESCE(:permission_model, 'TIME_BOUNDED'),
            :valid_from,
            :valid_to,
            FALSE,
            :created_by
        )
        RETURNING request_id
    """)

    insert_history = text("""
        INSERT INTO dms_access_requests_history (
            request_id,
            requester_id,
            requester_name,
            requester_designation,
            requester_department,
            document_id,
            document_number,
            document_title,
            security_classification,
            justification,
            status,
            permission_model,
            requested_on,
            valid_from,
            valid_to,
            is_deleted,
            created_by,
            created_at
        )
        SELECT
            request_id,
            requester_id,
            requester_name,
            requester_designation,
            requester_department,
            document_id,
            document_number,
            document_title,
            security_classification,
            justification,
            status,
            permission_model,
            requested_on,
            valid_from,
            valid_to,
            is_deleted,
            created_by,
            created_at
        FROM dms_access_requests
        WHERE request_id = :request_id
    """)

    try:
        res = db.execute(insert_master, payload)
        request_id = res.scalar()
        db.execute(insert_history, {"request_id": request_id})
        db.commit()

        # Trigger notification to custodian and folder publishers
        try:
            from app.crud.dms.dms_notification_crud import notify_access_request_submitted
            notify_access_request_submitted(
                db=db,
                request_id=request_id,
                requester_id=data.requester_id or data.created_by,
                document_id=data.document_id,
                reason=getattr(data, "justification", None),
                background_tasks=background_tasks,
            )
        except Exception as ne:
            logger.debug("[dms_access_request] Notification dispatch error: %s", ne)

        return request_id
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create DMS access request: {e}", exc_info=True)
        raise Exception(f"Failed to create DMS access request: {str(e)}")


# -------------------------------------------------
# 2. UPDATE ACCESS REQUEST
# -------------------------------------------------
def update_dms_access_request(db: Session, request_id: int, data: DmsAccessRequestUpdate) -> int:
    """Update fields on an access request and append history snapshot."""
    payload = data.model_dump(exclude_unset=True)

    # Never allow updating creation audit fields on PUT calls
    payload.pop("created_at", None)
    payload.pop("created_by", None)

    # Strip status, review_remarks, permission_model, reviewed_* - only /action should change those
    for forbidden_key in (
        "status", "review_remarks", "permission_model",
        "reviewed_by", "reviewed_by_name", "reviewed_at"
    ):
        payload.pop(forbidden_key, None)

    if not payload:
        return 0

    field_map = {
        "requester_id": "requester_id",
        "requester_name": "requester_name",
        "requester_designation": "requester_designation",
        "requester_department": "requester_department",
        "document_id": "document_id",
        "document_number": "document_number",
        "document_title": "document_title",
        "security_classification": "security_classification",
        "justification": "justification",
        "valid_from": "valid_from",
        "valid_to": "valid_to",
        "updated_by": "updated_by"
    }

    set_clauses = []
    params = {"request_id": request_id}
    for key, col in field_map.items():
        if key in payload:
            set_clauses.append(f"{col} = :{key}")
            params[key] = payload[key]

    if not set_clauses:
        return 0

    set_clauses.append("updated_at = NOW()")

    update_sql = f"""
        UPDATE dms_access_requests
        SET {', '.join(set_clauses)}
        WHERE request_id = :request_id AND is_deleted = FALSE AND UPPER(status) = 'PENDING'
    """

    history_sql = text("""
        INSERT INTO dms_access_requests_history (
            request_id,
            requester_id,
            requester_name,
            requester_designation,
            requester_department,
            document_id,
            document_number,
            document_title,
            security_classification,
            justification,
            status,
            permission_model,
            requested_on,
            valid_from,
            valid_to,
            reviewed_by,
            reviewed_by_name,
            reviewed_at,
            review_remarks,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        )
        SELECT
            request_id,
            requester_id,
            requester_name,
            requester_designation,
            requester_department,
            document_id,
            document_number,
            document_title,
            security_classification,
            justification,
            status,
            permission_model,
            requested_on,
            valid_from,
            valid_to,
            reviewed_by,
            reviewed_by_name,
            reviewed_at,
            review_remarks,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM dms_access_requests
        WHERE request_id = :request_id
    """)

    try:
        result = db.execute(text(update_sql), params)
        if result.rowcount > 0:
            db.execute(history_sql, {"request_id": request_id})
        db.commit()
        return result.rowcount
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update DMS access request: {e}", exc_info=True)
        raise Exception(f"Failed to update DMS access request: {str(e)}")


# -------------------------------------------------
# 3. ACTION (APPROVE / REJECT) ACCESS REQUEST
# -------------------------------------------------
def action_dms_access_request(
    db: Session,
    request_id: int,
    data: DmsAccessRequestAction,
    background_tasks: Optional[BackgroundTasks] = None,
) -> int:
    """Approve or reject a pending access request and log snapshot in history."""
    payload = data.model_dump(exclude_unset=True)

    status = (payload.get("status") or "").upper().strip()
    if status in ("APPROVE", "APPROVED"):
        status = "APPROVED"
    elif status in ("REJECT", "REJECTED"):
        status = "REJECTED"
    else:
        raise ValueError("Status must be either 'APPROVED' or 'REJECTED'")

    # 1. Require request to exist and be currently in PENDING status before action
    curr = db.execute(
        text("SELECT request_id, status, requester_id, permission_model FROM dms_access_requests WHERE request_id = :request_id AND is_deleted = FALSE"),
        {"request_id": request_id}
    ).mappings().first()
    if not curr:
        raise ValueError("Access request not found or has been deleted.")

    curr_status = (curr.get("status") or "").upper().strip()
    if curr_status != "PENDING":
        raise ValueError(
            f"Cannot action request: Request is currently in '{curr.get('status')}' status, but only PENDING requests can be approved or rejected."
        )

    # 2. Reject invalid permission models
    perm_model = payload.get("permission_model")
    if perm_model:
        perm_model = perm_model.upper().strip()
    elif status == "APPROVED":
        perm_model = (curr.get("permission_model") or "TIME_BOUNDED").upper().strip()

    ALLOWED_PERMISSION_MODELS = {"TIME_BOUNDED", "LIFETIME"}
    if perm_model and perm_model not in ALLOWED_PERMISSION_MODELS:
        raise ValueError(
            f"Invalid permission model '{perm_model}'. Allowed models are: {', '.join(sorted(ALLOWED_PERMISSION_MODELS))}."
        )

    # 3. Reject invalid date ranges
    valid_from = payload.get("valid_from")
    valid_to = payload.get("valid_to")

    if status == "APPROVED":
        today_date = datetime.now(IST).date()

        if perm_model == "LIFETIME":
            valid_to = None
            if not valid_from:
                valid_from = today_date
            else:
                vf_dt = _parse_datetime(valid_from)
                if not vf_dt:
                    raise ValueError(f"Invalid valid_from date format: '{valid_from}'. Must be a valid date (YYYY-MM-DD).")
        elif perm_model == "TIME_BOUNDED":
            if not valid_to:
                raise ValueError("valid_to expiration date is required for TIME_BOUNDED access approval.")

            if not valid_from:
                valid_from = today_date

            vf_dt = _parse_datetime(valid_from)
            vt_dt = _parse_datetime(valid_to)

            if not vt_dt:
                raise ValueError(f"Invalid valid_to date format: '{valid_to}'. Must be a valid date (YYYY-MM-DD).")
            if valid_from and not vf_dt:
                raise ValueError(f"Invalid valid_from date format: '{valid_from}'. Must be a valid date (YYYY-MM-DD).")

            if vf_dt and vt_dt and vt_dt.date() < vf_dt.date():
                raise ValueError(f"valid_to ({valid_to}) cannot be earlier than valid_from ({valid_from}).")

            if vt_dt and vt_dt.date() < today_date:
                raise ValueError(f"valid_to ({valid_to}) cannot be in the past.")

    # 4. Reviewer validation: Always resolve reviewer name from database, never trust client input
    rev_by = payload.get("reviewed_by")
    if not rev_by:
        raise ValueError("Reviewer ID (reviewed_by) is required.")

    # Reject the action if reviewed_by == requester_id (separation of duties)
    if curr.get("requester_id") is not None and curr.get("requester_id") == rev_by:
        raise ValueError("Requesters cannot review, approve, or reject their own access requests.")

    user = db.execute(
        text("SELECT TRIM(CONCAT_WS(' ', first_name, last_name)) AS full_name FROM users WHERE id = :uid"),
        {"uid": rev_by}
    ).mappings().first()
    rev_name = user.get("full_name") if user else f"User {rev_by}"

    update_sql = text("""
        UPDATE dms_access_requests
        SET
            status = :status,
            permission_model = COALESCE(:permission_model, permission_model),
            valid_from = CASE WHEN :status = 'APPROVED' THEN COALESCE(:valid_from, valid_from) ELSE valid_from END,
            valid_to = CASE 
                WHEN :permission_model = 'LIFETIME' THEN NULL
                WHEN :status = 'APPROVED' AND :permission_model = 'TIME_BOUNDED' AND :valid_to IS NOT NULL THEN :valid_to
                ELSE valid_to 
            END,
            review_remarks = COALESCE(:review_remarks, review_remarks),
            reviewed_by = :reviewed_by,
            reviewed_by_name = :reviewed_by_name,
            reviewed_at = NOW(),
            updated_by = :reviewed_by,
            updated_at = NOW()
        WHERE request_id = :request_id AND is_deleted = FALSE AND UPPER(status) = 'PENDING'
    """)

    history_sql = text("""
        INSERT INTO dms_access_requests_history (
            request_id,
            requester_id,
            requester_name,
            requester_designation,
            requester_department,
            document_id,
            document_number,
            document_title,
            security_classification,
            justification,
            status,
            permission_model,
            requested_on,
            valid_from,
            valid_to,
            reviewed_by,
            reviewed_by_name,
            reviewed_at,
            review_remarks,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        )
        SELECT
            request_id,
            requester_id,
            requester_name,
            requester_designation,
            requester_department,
            document_id,
            document_number,
            document_title,
            security_classification,
            justification,
            status,
            permission_model,
            requested_on,
            valid_from,
            valid_to,
            reviewed_by,
            reviewed_by_name,
            reviewed_at,
            review_remarks,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM dms_access_requests
        WHERE request_id = :request_id
    """)

    try:
        params = {
            "request_id": request_id,
            "status": status,
            "permission_model": perm_model,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "review_remarks": payload.get("review_remarks"),
            "reviewed_by": rev_by,
            "reviewed_by_name": rev_name
        }
        res = db.execute(update_sql, params)
        if res.rowcount == 0:
            raise ValueError("Cannot action request: Request was not found, was already processed, or is no longer in PENDING status.")
        db.execute(history_sql, {"request_id": request_id})
        db.commit()

        # Trigger notification to requester (APPROVED or REJECTED)
        try:
            from app.crud.dms.dms_notification_crud import notify_access_request_action
            notify_access_request_action(
                db=db,
                request_id=request_id,
                action=status,
                action_by=rev_by,
                remarks=payload.get("review_remarks"),
                access_end_date=valid_to,
                background_tasks=background_tasks,
            )
        except Exception as ne:
            logger.debug("[dms_access_request] Notification action dispatch error: %s", ne)

        return res.rowcount
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to process DMS access request action: {e}", exc_info=True)
        raise


# -------------------------------------------------
# 4. GET ACCESS REQUEST BY ID
# -------------------------------------------------
def get_dms_access_request(db: Session, request_id: int) -> Optional[dict]:
    """Retrieve an access request by ID with full requester/reviewer display names."""
    query = text("""
        SELECT
            r.request_id,
            r.requester_id,
            r.requester_name,
            r.requester_designation,
            r.requester_department,
            r.document_id,
            r.document_number,
            r.document_title,
            r.security_classification,
            r.justification,
            r.status,
            r.permission_model,
            r.requested_on,
            r.valid_from,
            r.valid_to,
            r.reviewed_by,
            COALESCE(r.reviewed_by_name, TRIM(CONCAT_WS(' ', ur.first_name, ur.last_name))) AS reviewed_by_name,
            r.reviewed_at,
            r.review_remarks,
            r.is_deleted,
            r.created_at,
            r.created_by,
            TRIM(CONCAT_WS(' ', uc.first_name, uc.last_name)) AS created_by_name,
            r.updated_at,
            r.updated_by,
            TRIM(CONCAT_WS(' ', uu.first_name, uu.last_name)) AS updated_by_name
        FROM dms_access_requests r
        LEFT JOIN users uc ON uc.id = r.created_by
        LEFT JOIN users uu ON uu.id = r.updated_by
        LEFT JOIN users ur ON ur.id = r.reviewed_by
        WHERE r.request_id = :request_id AND r.is_deleted = FALSE
    """)
    row = db.execute(query, {"request_id": request_id}).mappings().first()
    if not row:
        return None
    return _format_row(row)


# -------------------------------------------------
# 5. GET ALL ACCESS REQUESTS
# -------------------------------------------------
def get_all_dms_access_requests(
    db: Session,
    status: Optional[str] = None,
    document_id: Optional[int] = None,
    requester_id: Optional[int] = None,
    publisher_user_id: Optional[int] = None,
    search: Optional[str] = None
) -> List[dict]:
    """Retrieve all access requests with multi-parameter filtering and search."""
    where_clauses = ["r.is_deleted = FALSE"]
    params: Dict[str, Any] = {}

    if status and status.upper() != "ALL":
        where_clauses.append("UPPER(r.status) = :status")
        params["status"] = status.upper()

    if document_id:
        where_clauses.append("r.document_id = :document_id")
        params["document_id"] = document_id

    if requester_id:
        where_clauses.append("r.requester_id = :requester_id")
        params["requester_id"] = requester_id

    expanding_params: List[str] = []

    # Automatically transition any lapsed requests (including expired pending requests) to EXPIRED
    try:
        auto_expire_dms_access_requests(db)
    except Exception as e:
        logger.warning(f"auto_expire_dms_access_requests in get_all failed: {e}")

    if publisher_user_id:
        _, allowed_folders, allowed_subfolders = get_user_dms_folder_access(db, publisher_user_id, ignore_admin=True)
        pub_conditions = ["d.created_by = :publisher_user_id", "d.custodian_id = :publisher_user_id"]
        params["publisher_user_id"] = publisher_user_id
        if allowed_folders:
            params["allowed_fids"] = list(allowed_folders)
            expanding_params.append("allowed_fids")
            if allowed_subfolders:
                params["allowed_sfids"] = list(allowed_subfolders)
                expanding_params.append("allowed_sfids")
                pub_conditions.append("(d.folder_id IN :allowed_fids AND (d.sub_folder_id IS NULL OR d.sub_folder_id = 0 OR d.sub_folder_id IN :allowed_sfids))")
            else:
                pub_conditions.append("d.folder_id IN :allowed_fids")
        where_clauses.append(f"""EXISTS (
            SELECT 1 FROM dms_documents d
            WHERE d.document_id = r.document_id
              AND d.is_deleted = FALSE
              AND ({' OR '.join(pub_conditions)})
        )""")

    # Escape % and _ in search query
    if search:
        escaped_search = (
            search.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        where_clauses.append("""(
            r.requester_name ILIKE :search ESCAPE '\\' OR
            r.document_number ILIKE :search ESCAPE '\\' OR
            r.document_title ILIKE :search ESCAPE '\\' OR
            r.justification ILIKE :search ESCAPE '\\'
        )""")
        params["search"] = f"%{escaped_search}%"

    where_sql = " AND ".join(where_clauses)

    query = text(f"""
        SELECT
            r.request_id,
            r.requester_id,
            r.requester_name,
            r.requester_designation,
            r.requester_department,
            r.document_id,
            r.document_number,
            r.document_title,
            r.security_classification,
            r.justification,
            r.status,
            r.permission_model,
            r.requested_on,
            r.valid_from,
            r.valid_to,
            r.reviewed_by,
            COALESCE(r.reviewed_by_name, TRIM(CONCAT_WS(' ', ur.first_name, ur.last_name))) AS reviewed_by_name,
            r.reviewed_at,
            r.review_remarks,
            r.is_deleted,
            r.created_at,
            r.created_by,
            TRIM(CONCAT_WS(' ', uc.first_name, uc.last_name)) AS created_by_name,
            r.updated_at,
            r.updated_by,
            TRIM(CONCAT_WS(' ', uu.first_name, uu.last_name)) AS updated_by_name
        FROM dms_access_requests r
        LEFT JOIN users uc ON uc.id = r.created_by
        LEFT JOIN users uu ON uu.id = r.updated_by
        LEFT JOIN users ur ON ur.id = r.reviewed_by
        WHERE {where_sql}
        ORDER BY r.requested_on DESC NULLS LAST, r.request_id DESC
    """)
    for p in expanding_params:
        query = query.bindparams(bindparam(p, expanding=True))

    rows = db.execute(query, params).mappings().all()
    return [_format_row(r) for r in rows]


# -------------------------------------------------
# 6. GET ACCESS REQUEST COUNTS
# -------------------------------------------------
def get_dms_access_request_counts(
    db: Session,
    publisher_user_id: Optional[int] = None,
    requester_id: Optional[int] = None
) -> dict:
    """Get aggregated tab counts for access requests by status."""
    try:
        auto_expire_dms_access_requests(db)
    except Exception as e:
        logger.warning(f"auto_expire_dms_access_requests in get_counts failed: {e}")

    where_clauses = ["r.is_deleted = FALSE"]
    params: Dict[str, Any] = {}
    expanding_params: List[str] = []

    if requester_id:
        where_clauses.append("r.requester_id = :requester_id")
        params["requester_id"] = requester_id

    if publisher_user_id:
        _, allowed_folders, allowed_subfolders = get_user_dms_folder_access(db, publisher_user_id, ignore_admin=True)
        pub_conditions = ["d.created_by = :publisher_user_id", "d.custodian_id = :publisher_user_id"]
        params["publisher_user_id"] = publisher_user_id
        if allowed_folders:
            params["allowed_fids"] = list(allowed_folders)
            expanding_params.append("allowed_fids")
            if allowed_subfolders:
                params["allowed_sfids"] = list(allowed_subfolders)
                expanding_params.append("allowed_sfids")
                pub_conditions.append("(d.folder_id IN :allowed_fids AND (d.sub_folder_id IS NULL OR d.sub_folder_id = 0 OR d.sub_folder_id IN :allowed_sfids))")
            else:
                pub_conditions.append("d.folder_id IN :allowed_fids")
        where_clauses.append(f"""EXISTS (
            SELECT 1 FROM dms_documents d
            WHERE d.document_id = r.document_id
              AND d.is_deleted = FALSE
              AND ({' OR '.join(pub_conditions)})
        )""")

    where_sql = " AND ".join(where_clauses)
    query = text(f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE UPPER(r.status) = 'PENDING') AS pending,
            COUNT(*) FILTER (WHERE UPPER(r.status) IN ('APPROVED', 'ACCESS GRANTED')) AS approved,
            COUNT(*) FILTER (WHERE UPPER(r.status) = 'REJECTED') AS rejected,
            COUNT(*) FILTER (WHERE UPPER(r.status) = 'EXPIRED') AS expired
        FROM dms_access_requests r
        WHERE {where_sql}
    """)
    for p in expanding_params:
        query = query.bindparams(bindparam(p, expanding=True))

    row = db.execute(query, params).mappings().first()
    return {
        "all": row["total"] if row else 0,
        "pending": row["pending"] if row else 0,
        "approved": row["approved"] if row else 0,
        "rejected": row["rejected"] if row else 0,
        "expired": row["expired"] if row else 0
    }


# -------------------------------------------------
# 7. SOFT DELETE ACCESS REQUEST
# -------------------------------------------------
def soft_delete_dms_access_request(db: Session, request_id: int, deleted_by: Optional[int]) -> int:
    """Soft delete an access request and append history snapshot."""
    update_sql = text("""
        UPDATE dms_access_requests
        SET is_deleted = TRUE,
            updated_by = :deleted_by,
            updated_at = NOW()
        WHERE request_id = :request_id AND is_deleted = FALSE
    """)

    history_sql = text("""
        INSERT INTO dms_access_requests_history (
            request_id,
            requester_id,
            requester_name,
            requester_designation,
            requester_department,
            document_id,
            document_number,
            document_title,
            security_classification,
            justification,
            status,
            permission_model,
            requested_on,
            valid_from,
            valid_to,
            reviewed_by,
            reviewed_by_name,
            reviewed_at,
            review_remarks,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        )
        SELECT
            request_id,
            requester_id,
            requester_name,
            requester_designation,
            requester_department,
            document_id,
            document_number,
            document_title,
            security_classification,
            justification,
            status,
            permission_model,
            requested_on,
            valid_from,
            valid_to,
            reviewed_by,
            reviewed_by_name,
            reviewed_at,
            review_remarks,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM dms_access_requests
        WHERE request_id = :request_id
    """)

    try:
        result = db.execute(update_sql, {"request_id": request_id, "deleted_by": deleted_by})
        if result.rowcount == 0:
            raise NotFoundError("Access request not found or already deleted")
        db.execute(history_sql, {"request_id": request_id})
        db.commit()
        return result.rowcount
    except NotFoundError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete DMS access request: {e}", exc_info=True)
        raise Exception(f"Failed to delete DMS access request: {str(e)}")


# -------------------------------------------------
# 8. AUTO EXPIRE ACCESS REQUESTS (SCHEDULED JOB)
# -------------------------------------------------
def auto_expire_dms_access_requests(db: Optional[Session] = None) -> int:
    """Daily cron job: Transitions expired approved requests to EXPIRED and records history."""
    should_close_session = False
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
        should_close_session = True

    try:
        today = datetime.now(IST).date()

        find_sql = text("""
            SELECT request_id, requester_id, document_id, valid_to
            FROM dms_access_requests
            WHERE is_deleted = FALSE
              AND UPPER(status) IN ('APPROVED', 'ACCESS GRANTED', 'PENDING')
              AND valid_to IS NOT NULL
              AND valid_to < :today
        """)
        rows = db.execute(find_sql, {"today": today}).fetchall()
        if not rows:
            logger.info("auto_expire_dms_access_requests: No expired access requests found.")
            return 0

        expired_ids = [r[0] for r in rows]

        update_sql = text("""
            UPDATE dms_access_requests
            SET status = 'EXPIRED',
                updated_at = NOW()
            WHERE request_id = ANY(:req_ids)
              AND is_deleted = FALSE
        """)
        db.execute(update_sql, {"req_ids": expired_ids})

        history_sql = text("""
            INSERT INTO dms_access_requests_history (
                request_id,
                requester_id,
                requester_name,
                requester_designation,
                requester_department,
                document_id,
                document_number,
                document_title,
                security_classification,
                justification,
                status,
                permission_model,
                requested_on,
                valid_from,
                valid_to,
                reviewed_by,
                reviewed_by_name,
                reviewed_at,
                review_remarks,
                is_deleted,
                created_by,
                created_at,
                updated_by,
                updated_at
            )
            SELECT
                request_id,
                requester_id,
                requester_name,
                requester_designation,
                requester_department,
                document_id,
                document_number,
                document_title,
                security_classification,
                justification,
                status,
                permission_model,
                requested_on,
                valid_from,
                valid_to,
                reviewed_by,
                reviewed_by_name,
                reviewed_at,
                review_remarks,
                is_deleted,
                created_by,
                created_at,
                updated_by,
                updated_at
            FROM dms_access_requests
            WHERE request_id = ANY(:req_ids)
        """)
        db.execute(history_sql, {"req_ids": expired_ids})
        db.commit()
        logger.info(
            f"auto_expire_dms_access_requests: Successfully transitioned {len(expired_ids)} request(s) to 'EXPIRED'. IDs: {expired_ids}"
        )

        # Trigger notification to each expired requester
        try:
            from app.crud.dms.dms_notification_crud import notify_access_request_expired
            for r in rows:
                req_id = r[0]
                requester_id = r[1]
                doc_id = r[2]
                v_to = r[3]
                if requester_id and doc_id:
                    notify_access_request_expired(
                        db=db,
                        request_id=req_id,
                        requester_id=requester_id,
                        document_id=doc_id,
                        valid_to=v_to,
                    )
        except Exception as ne:
            logger.debug("[dms_access_request] Auto-expire notification error: %s", ne)

        return len(expired_ids)
    except Exception as e:
        db.rollback()
        logger.exception(f"auto_expire_dms_access_requests failed: {e}")
        raise
    finally:
        if should_close_session:
            db.close()
