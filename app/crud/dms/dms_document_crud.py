import os
import re
import uuid
import json
import mimetypes
import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Set, Union
from app.utils.time_utils import to_iso_ist, IST
from fastapi import UploadFile, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.sql import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import exc as sa_exc

from app.schemas.dms.dms_document_schema import DmsDocumentCreate, DmsDocumentUpdate
from app.crud.dms.dms_auth import (
    is_user_dms_admin,
    is_user_dms_publisher,
    is_user_folder_publisher,
    get_user_dms_folder_access,
    NotFoundError,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# CONSTANTS & CONFIGURATION
# ==============================================================================

MAX_FILE_SIZE = 30 * 1024 * 1024  # 30 MB
DMS_UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../uploads/dms/documents")
)

ALLOWED_EXTENSIONS = {
    # Documents
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".txt",
    ".csv",
    ".rtf",
    ".odt",
    ".ods",
    ".odp",
    # Images (SVG explicitly excluded for security)
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".tiff",
    ".tif",
}

DISALLOWED_EXTENSIONS = {
    # Vectors / Executables
    ".svg",
    ".exe",
    ".sh",
    ".bat",
    ".cmd",
    ".vbs",
    ".js",
    # Videos
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".flv",
    ".wmv",
    ".webm",
    ".m4v",
    ".3gp",
    ".mpeg",
    ".mpg",
    # Archives / Zip
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".iso",
}

ALLOWED_DOCUMENT_STATUSES = {
    "ACTIVE",
    "UNDER REVIEW",
    "IN REVIEW",
    "REVIEW",
    "PENDING",
    "ARCHIVED",
    "DRAFT",
    "INACTIVE",
}

MAGIC_SIGNATURES: Dict[str, List[bytes]] = {
    ".pdf": [b"%PDF"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".gif": [b"GIF87a", b"GIF89a"],
    ".bmp": [b"BM"],
    ".docx": [b"PK\x03\x04"],
    ".xlsx": [b"PK\x03\x04"],
    ".pptx": [b"PK\x03\x04"],
    ".odt": [b"PK\x03\x04"],
    ".ods": [b"PK\x03\x04"],
    ".odp": [b"PK\x03\x04"],
    ".doc": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    ".xls": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    ".ppt": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    ".rtf": [b"{\\rtf"],
    ".tiff": [b"II*\x00", b"MM\x00*"],
    ".tif": [b"II*\x00", b"MM\x00*"],
}

CANONICAL_MIME_MAP: Dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".rtf": "application/rtf",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
}


# ==============================================================================
# HELPERS, FORMATTERS & EXCEPTIONS
# ==============================================================================


class DocumentNotFoundException(NotFoundError, HTTPException):
    def __init__(self, detail: str = "Document not found"):
        super().__init__(status_code=404, detail=detail)



def get_dms_upload_dir() -> str:
    """Lazy absolute upload directory resolver."""
    os.makedirs(DMS_UPLOAD_DIR, exist_ok=True)
    return DMS_UPLOAD_DIR


def clean_document_number(val: Optional[str]) -> Optional[str]:
    """
    Normalize and remove unwanted spaces in document numbers.
    E.g.:
      'PMHBL - P1 - OP - 10/2026 - 087' -> 'PMHBL-P1-OP-10/2026-087'
      'PMHBL  -  P1  -  OP  -  10/2026  -  087' -> 'PMHBL-P1-OP-10/2026-087'
      'PMHBL - P1 - OP - 10 / 2026 - 087' -> 'PMHBL-P1-OP-10/2026-087'
    Removes any spacing around hyphens and slashes, and trims leading/trailing whitespace.
    """
    if not val or not isinstance(val, str):
        return val
    cleaned = re.sub(r"\s*-\s*", "-", val)
    cleaned = re.sub(r"\s*/\s*", "/", cleaned)
    return cleaned.strip()


def _format_document_row(row) -> Optional[dict]:
    """Format row datetime/date fields to ISO IST strings."""
    if not row:
        return None
    r = dict(row)
    if r.get("created_at"):
        r["created_at"] = to_iso_ist(r["created_at"])
    if r.get("updated_at"):
        r["updated_at"] = to_iso_ist(r["updated_at"])
    if r.get("open_date"):
        r["open_date"] = str(r["open_date"])
    if r.get("close_date"):
        r["close_date"] = str(r["close_date"])
    if r.get("latest_revision_date"):
        r["latest_revision_date"] = to_iso_ist(r["latest_revision_date"])
    if r.get("document_number") and isinstance(r["document_number"], str):
        # Normalize loose spacing in reference numbers (e.g. 'PMHBL - P1 - OP - ...' -> 'PMHBL-P1-OP-...')
        r["document_number"] = clean_document_number(r["document_number"])
    return r


def get_document_folder_breadcrumbs(db: Session, folder_id: Optional[int], sub_folder_id: Optional[int]) -> dict:
    """
    Builds the complete breadcrumb chain and human-readable folder path for a document.
    Works for any arbitrary nesting depth.
    """
    breadcrumbs = []
    names = []

    # 1. Fetch root folder details
    root_folder = None
    if folder_id:
        root_folder = db.execute(
            text("SELECT folder_id, folder_name FROM dms_folders WHERE folder_id = :fid"),
            {"fid": folder_id}
        ).mappings().first()

    if root_folder:
        breadcrumbs.append({
            "id": root_folder["folder_id"],
            "name": root_folder["folder_name"],
            "type": "folder",
            "level": 1
        })
        names.append(root_folder["folder_name"])

    # 2. Walk up sub-folder lineage to construct root-to-leaf path
    if sub_folder_id:
        curr_sf_id = sub_folder_id
        sf_chain = []
        visited = set()

        while curr_sf_id and curr_sf_id not in visited:
            visited.add(curr_sf_id)
            sf_row = db.execute(
                text("""
                    SELECT sub_folder_id, folder_id, parent_sub_folder_id, sub_folder_name
                    FROM dms_sub_folders
                    WHERE sub_folder_id = :sfid
                """),
                {"sfid": curr_sf_id}
            ).mappings().first()

            if not sf_row:
                break

            sf_chain.append(dict(sf_row))
            curr_sf_id = sf_row.get("parent_sub_folder_id")

        # Reverse chain so it goes from highest parent to destination leaf
        sf_chain.reverse()
        base_level = len(breadcrumbs) + 1
        for idx, sf in enumerate(sf_chain):
            breadcrumbs.append({
                "id": sf["sub_folder_id"],
                "name": sf["sub_folder_name"],
                "type": "sub_folder",
                "level": base_level + idx
            })
            names.append(sf["sub_folder_name"])

    folder_path = " / ".join(names) if names else None
    dest_sf_name = breadcrumbs[-1]["name"] if breadcrumbs and breadcrumbs[-1]["type"] == "sub_folder" else None
    root_f_name = root_folder["folder_name"] if root_folder else (breadcrumbs[0]["name"] if breadcrumbs else None)

    return {
        "folder_name": root_f_name,
        "sub_folder_name": dest_sf_name,
        "folder_path": folder_path,
        "breadcrumbs": breadcrumbs
    }


def format_datetime_ist_display(val: Any) -> Optional[str]:
    """Format datetime into 'DD Mon YYYY · HH:MM' in IST."""
    if not val:
        return None
    if isinstance(val, str):
        try:
            val = datetime.fromisoformat(val)
        except Exception:
            return val
    if isinstance(val, (datetime, date)):
        if isinstance(val, datetime):
            if val.tzinfo is None:
                val = val.replace(tzinfo=IST)
            else:
                val = val.astimezone(IST)
            return val.strftime("%d %b %Y · %H:%M")
        return val.strftime("%d %b %Y")
    return str(val)


def format_file_size(size_in_bytes: int) -> str:
    """Format file size in bytes to B / KB / MB string representation."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{round(size_in_bytes / 1024, 2)} KB"
    else:
        return f"{round(size_in_bytes / (1024 * 1024), 2)} MB"


def _write_chunks_to_file(filepath: str, chunks: List[bytes]) -> None:
    """Write binary chunk list directly to disk."""
    with open(filepath, "wb") as f:
        for chunk in chunks:
            f.write(chunk)


def _clean_payload_value(val: Optional[str]) -> Optional[str]:
    """Clean redundant 'Other...' prefixes from payload strings."""
    if not val:
        return None
    s = str(val).strip()
    cleaned = (
        re.sub(
            r"^(?:others|other)(?:\.{3}|\.+|[-:/,\(\)\s])*", "", s, flags=re.IGNORECASE
        )
        .strip()
        .rstrip(")")
    )
    if not cleaned or cleaned.upper() in ["OTHER", "OTHERS", "OTHER..."]:
        return None
    return cleaned


def _validate_file_path(file_path: Optional[str]) -> None:
    """Validate that file_path resolves strictly inside DMS_UPLOAD_DIR."""
    if not file_path:
        return
    upload_dir = os.path.realpath(get_dms_upload_dir())

    # Resolve absolute path or relative to upload_dir / cwd
    if os.path.isabs(file_path):
        resolved = os.path.realpath(file_path)
    else:
        # Check if relative path points inside upload_dir
        cwd_resolved = os.path.realpath(os.path.join(os.getcwd(), file_path))
        try:
            if os.path.commonpath([cwd_resolved, upload_dir]) == upload_dir:
                resolved = cwd_resolved
            else:
                resolved = os.path.realpath(os.path.join(upload_dir, file_path))
        except (ValueError, Exception):
            resolved = os.path.realpath(os.path.join(upload_dir, file_path))

    try:
        common = os.path.commonpath([resolved, upload_dir])
        if common != upload_dir or resolved == upload_dir:
            raise HTTPException(
                status_code=400,
                detail="Invalid file_path: File path must resolve inside DMS_UPLOAD_DIR.",
            )
    except (ValueError, Exception):
        raise HTTPException(
            status_code=400,
            detail="Invalid file_path: File path must resolve inside DMS_UPLOAD_DIR.",
        )


def _get_user_approved_document_ids(db: Session, user_id: Optional[int]) -> Set[int]:
    """Fetch set of document IDs for which the user has an active approved access request."""
    if not user_id:
        return set()
    acc_rows = db.execute(
        text(
            """
            SELECT document_id FROM dms_access_requests
            WHERE requester_id = :uid
              AND UPPER(status) = 'APPROVED'
              AND is_deleted = FALSE
              AND (valid_to IS NULL OR valid_to >= CURRENT_DATE)
              AND (valid_from IS NULL OR valid_from <= CURRENT_DATE)
        """
        ),
        {"uid": user_id},
    ).fetchall()
    return {r[0] for r in acc_rows if r[0] is not None}


def _get_user_pending_document_ids(
    db: Session, user_id: Optional[int]
) -> Dict[int, int]:
    """Fetch mapping of document_id -> request_id for user's pending access requests."""
    if not user_id:
        return {}
    rows = db.execute(
        text(
            """
            SELECT document_id, request_id FROM dms_access_requests
            WHERE requester_id = :uid
              AND UPPER(status) = 'PENDING'
              AND is_deleted = FALSE
        """
        ),
        {"uid": user_id},
    ).fetchall()
    return {r[0]: r[1] for r in rows if r[0] is not None}


def _is_user_in_assigned_engineers(
    db: Session,
    user_id: Optional[int],
    doc: dict,
    user_identity_cache: Optional[Dict[int, Set[str]]] = None,
) -> bool:
    """Check if user_id or user identity matches individual_engineer or custody_list assigned by the publisher."""
    if not user_id:
        return False

    user_identifiers = {str(user_id)}
    if user_identity_cache is not None and user_id in user_identity_cache:
        user_identifiers = user_identity_cache[user_id]
    elif db:
        u_row = (
            db.execute(
                text(
                    "SELECT TRIM(CONCAT_WS(' ', first_name, last_name)) AS full_name, username, email FROM users WHERE id = :uid"
                ),
                {"uid": user_id},
            )
            .mappings()
            .first()
        )
        if u_row:
            if u_row.get("full_name"):
                user_identifiers.add(u_row["full_name"].strip().lower())
            if u_row.get("username"):
                user_identifiers.add(u_row["username"].strip().lower())
            if u_row.get("email"):
                user_identifiers.add(u_row["email"].strip().lower())
        if user_identity_cache is not None:
            user_identity_cache[user_id] = user_identifiers

    for field in ("individual_engineer", "custody_list"):
        val = doc.get(field)
        if not val:
            continue
        if isinstance(val, str):
            val_clean = val.strip()
            if val_clean.startswith("[") or val_clean.startswith("{"):
                try:
                    val = json.loads(val_clean)
                except Exception:
                    pass
            else:
                if val_clean.lower() in user_identifiers:
                    return True
                for part in val_clean.split(","):
                    if part.strip().lower() in user_identifiers:
                        return True

        if isinstance(val, list):
            for item in val:
                if isinstance(item, int) and str(item) in user_identifiers:
                    return True
                elif isinstance(item, dict):
                    uid = item.get("user_id") or item.get("id")
                    if uid and str(uid) in user_identifiers:
                        return True
                    uname = item.get("user_name") or item.get("name")
                    if uname and str(uname).strip().lower() in user_identifiers:
                        return True
                elif isinstance(item, str):
                    if item.strip().lower() in user_identifiers:
                        return True
    return False


def _check_confidential_access(
    db: Session,
    user_id: Optional[int],
    doc: dict,
    approved_doc_ids: Optional[Set[int]] = None,
    is_admin: Optional[bool] = None,
    user_identity_cache: Optional[Dict[int, Set[str]]] = None,
    allowed_folders: Optional[Set[int]] = None,
    allowed_subfolders: Optional[Set[int]] = None,
    is_unrestricted: Optional[bool] = None,
) -> bool:
    """Returns True if the user has permission to view metadata of a confidential / restricted document."""
    is_confidential = bool(doc.get("confidential_document"))
    sec_class = (doc.get("security_classification") or "").upper()
    is_restricted = is_confidential or sec_class in (
        "CONFIDENTIAL",
        "SECRET",
        "RESTRICTED",
    )
    if not is_restricted:
        return True
    if not user_id:
        return False

    # Note: Admin does NOT get default access to another publisher's confidential documents.
    # Only the creator, assigned folder publishers, assigned custodian, explicitly assigned engineers, or users with approved requests can access.
    created_by_val = doc.get("created_by")
    custodian_id_val = doc.get("custodian_id")
    if (created_by_val is not None and str(created_by_val).strip() == str(user_id).strip()) or (
        custodian_id_val is not None and str(custodian_id_val).strip() == str(user_id).strip()
    ):
        return True

    # Note: Folder publishers do NOT get automatic access to confidential documents.
    # Only creator, assigned custodian, explicitly assigned engineers / custody list,
    # or users with approved access requests can access confidential documents.

    if _is_user_in_assigned_engineers(
        db, user_id, doc, user_identity_cache=user_identity_cache
    ):
        return True

    doc_id = doc.get("document_id")
    if not doc_id:
        return False

    if approved_doc_ids is not None:
        return doc_id in approved_doc_ids

    acc = db.execute(
        text(
            """
            SELECT request_id FROM dms_access_requests
            WHERE requester_id = :uid
              AND document_id = :doc_id
              AND UPPER(status) = 'APPROVED'
              AND is_deleted = FALSE
              AND (valid_to IS NULL OR valid_to >= CURRENT_DATE)
              AND (valid_from IS NULL OR valid_from <= CURRENT_DATE)
        """
        ),
        {"uid": user_id, "doc_id": doc_id},
    ).first()
    return acc is not None


def check_document_file_access(
    db: Session,
    user_id: Optional[int],
    doc: dict,
    approved_doc_ids: Optional[Set[int]] = None,
    user_identity_cache: Optional[Dict[int, Set[str]]] = None,
    allowed_folders: Optional[Set[int]] = None,
    allowed_subfolders: Optional[Set[int]] = None,
    is_admin: Optional[bool] = None,
    is_unrestricted: Optional[bool] = None,
) -> bool:
    """
    Returns True if the user has permission to open, preview, and download the document file.
    Access is granted when:
      1. User is the publisher / creator who uploaded the document (created_by == user_id).
      2. User has folder-based publisher privileges (assigned to the folder/subfolder).
      3. User is the designated custodian (custodian_id == user_id).
      4. User is explicitly in assigned individual_engineer or custody_list by the publisher.
      5. User has an active approved access request in dms_access_requests.
    """
    if not user_id:
        return False

    # 1. The publisher who created / uploaded the document has default access
    created_by_val = doc.get("created_by")
    if created_by_val is not None and str(created_by_val).strip() == str(user_id).strip():
        return True

    # 2. Folder-Based Publisher Privileges: Assigned folder publishers have publisher privileges
    # for all files uploaded within that folder, regardless of which publisher uploaded the file.
    # Note: Folder publisher assignment only grants file access to NON-RESTRICTED documents.
    # For confidential / restricted documents, only creator, custodian, assigned engineer, or approved request grants access.
    is_conf = bool(doc.get("confidential_document"))
    sec_class = (doc.get("security_classification") or "").upper()
    is_restricted = is_conf or sec_class in ("CONFIDENTIAL", "SECRET", "RESTRICTED")

    if not is_restricted:
        _pub_fids = allowed_folders if (is_unrestricted is not True and not is_admin) else None
        _pub_sfids = allowed_subfolders if (is_unrestricted is not True and not is_admin) else None

        if is_user_folder_publisher(
            db,
            user_id,
            folder_id=doc.get("folder_id"),
            sub_folder_id=doc.get("sub_folder_id"),
            allowed_folders=_pub_fids,
            allowed_subfolders=_pub_sfids,
            is_admin=False,
            is_unrestricted=False,
        ):
            return True

    # 3. Custodian assigned to the document has direct access
    custodian_id_val = doc.get("custodian_id")
    if custodian_id_val is not None and str(custodian_id_val).strip() == str(user_id).strip():
        return True

    # 4. Assigned engineers have direct access
    if _is_user_in_assigned_engineers(
        db, user_id, doc, user_identity_cache=user_identity_cache
    ):
        return True

    doc_id = doc.get("document_id")
    if not doc_id:
        return False

    # 5. Approved access requests in dms_access_requests
    if approved_doc_ids is not None:
        return doc_id in approved_doc_ids

    acc = db.execute(
        text(
            """
            SELECT request_id FROM dms_access_requests
            WHERE requester_id = :uid
              AND document_id = :doc_id
              AND UPPER(status) = 'APPROVED'
              AND is_deleted = FALSE
              AND (valid_to IS NULL OR valid_to >= CURRENT_DATE)
              AND (valid_from IS NULL OR valid_from <= CURRENT_DATE)
        """
        ),
        {"uid": user_id, "doc_id": doc_id},
    ).first()
    return acc is not None


def check_document_access_permissions(
    db: Session,
    user_id: Optional[int],
    doc: dict,
    approved_doc_ids: Optional[Set[int]] = None,
    pending_doc_map: Optional[Dict[int, int]] = None,
    user_identity_cache: Optional[Dict[int, Set[str]]] = None,
    allowed_folders: Optional[Set[int]] = None,
    allowed_subfolders: Optional[Set[int]] = None,
    is_admin: Optional[bool] = None,
    is_unrestricted: Optional[bool] = None,
    **kwargs,
) -> dict:
    """
    Returns rich frontend access permission flags for a document:
      - has_access: bool (can view & download)
      - can_view: bool
      - can_download: bool
      - can_request_access: bool (eligible for request access modal)
      - access_status: 'GRANTED' | 'PENDING_REQUEST' | 'NO_ACCESS'
      - pending_request_id: Optional[int]
      - is_publisher: bool (has publisher privileges for this document)
      - has_publisher_privileges: bool (has access to File Publisher Privileges section)
      - can_manage: bool (can edit/revise/manage this document)
    """
    if not user_id:
        return {
            "has_access": False,
            "can_view": False,
            "can_download": False,
            "can_request_access": False,
            "access_status": "NO_ACCESS",
            "pending_request_id": None,
            "is_publisher": False,
            "has_publisher_privileges": False,
            "can_manage": False,
        }

    # Determine publisher privileges:
    # Only creator or explicitly assigned folder publisher has publisher privileges
    created_by_val = doc.get("created_by")
    custodian_id_val = doc.get("custodian_id")
    is_creator = (created_by_val is not None and str(created_by_val).strip() == str(user_id).strip())
    is_custodian = (custodian_id_val is not None and str(custodian_id_val).strip() == str(user_id).strip())

    is_conf = bool(doc.get("confidential_document"))
    sec_class = (doc.get("security_classification") or "").upper()
    is_restricted = is_conf or sec_class in ("CONFIDENTIAL", "SECRET", "RESTRICTED")

    _pub_fids = allowed_folders if (is_unrestricted is not True and not is_admin) else None
    _pub_sfids = allowed_subfolders if (is_unrestricted is not True and not is_admin) else None

    is_folder_pub = False
    if not is_restricted:
        is_folder_pub = is_user_folder_publisher(
            db,
            user_id,
            folder_id=doc.get("folder_id"),
            sub_folder_id=doc.get("sub_folder_id"),
            allowed_folders=_pub_fids,
            allowed_subfolders=_pub_sfids,
            is_admin=False,
            is_unrestricted=False,
        )
    has_pub_privileges = bool(is_folder_pub or is_creator)

    has_acc = check_document_file_access(
        db,
        user_id,
        doc,
        approved_doc_ids=approved_doc_ids,
        user_identity_cache=user_identity_cache,
        allowed_folders=allowed_folders,
        allowed_subfolders=allowed_subfolders,
        is_admin=is_admin,
        is_unrestricted=is_unrestricted,
    )
    doc_id = doc.get("document_id")

    if has_acc:
        return {
            "has_access": True,
            "can_view": True,
            "can_download": True,
            "can_request_access": False,
            "access_status": "GRANTED",
            "pending_request_id": None,
            "is_publisher": has_pub_privileges,
            "has_publisher_privileges": has_pub_privileges,
            "can_manage": bool(has_pub_privileges or is_custodian),
        }

    # If user does not have access, check if a request is already pending
    pending_req_id = None
    if pending_doc_map is not None:
        pending_req_id = pending_doc_map.get(doc_id)
    elif doc_id:
        row = db.execute(
            text(
                """
                SELECT request_id FROM dms_access_requests
                WHERE requester_id = :uid
                  AND document_id = :doc_id
                  AND UPPER(status) = 'PENDING'
                  AND is_deleted = FALSE
                LIMIT 1
            """
            ),
            {"uid": user_id, "doc_id": doc_id},
        ).first()
        if row:
            pending_req_id = row[0]

    # Any document without access can be requested unless a request is already pending
    can_req = (pending_req_id is None)

    return {
        "has_access": False,
        "can_view": False,
        "can_download": False,
        "can_request_access": can_req,
        "access_status": "PENDING_REQUEST" if pending_req_id else "NO_ACCESS",
        "pending_request_id": pending_req_id,
        "is_publisher": has_pub_privileges,
        "has_publisher_privileges": has_pub_privileges,
        "can_manage": bool(has_pub_privileges or is_custodian),
    }


DOCUMENT_BASE_SELECT = """
    SELECT
        d.document_id,
        d.document_number,
        d.document_title,
        d.document_subject,
        d.target_folder,
        d.folder_id,
        d.sub_folder_id,
        d.sub_sub_folder_id,
        d.department,
        d.location,
        d.station_id,
        d.category,
        d.document_type,
        d.custodian_id,
        d.custodian_name,
        d.open_date,
        d.close_date,
        d.volume,
        d.security_classification,
        d.retention_class,
        d.confidential_document,
        COALESCE(d.revision, 'Rev 01') AS revision,
        COALESCE(d.revision_number, 1) AS revision_number,
        d.revision_note,
        COALESCE(rev_stat.revision_count, 1) AS revision_count,
        rev_stat.latest_revision_date,
        d.physical_rack,
        d.physical_shelf,
        d.physical_box,
        d.status,
        d.custody_list,
        d.individual_engineer,
        d.file_path,
        d.file_name,
        d.file_size,
        d.file_type,
        d.description,
        d.tags,
        d.is_deleted,
        d.created_at,
        d.created_by,
        TRIM(CONCAT_WS(' ', uc.first_name, uc.last_name)) AS created_by_name,
        d.updated_at,
        d.updated_by,
        TRIM(CONCAT_WS(' ', uu.first_name, uu.last_name)) AS updated_by_name
    FROM dms_documents d
    LEFT JOIN users uc ON uc.id = d.created_by
    LEFT JOIN users uu ON uu.id = d.updated_by
    LEFT JOIN (
        SELECT document_id, 
               COUNT(*) AS revision_count, 
               MAX(COALESCE(history_created_at, updated_at, created_at)) AS latest_revision_date
        FROM dms_documents_history
        WHERE document_id IS NOT NULL
        GROUP BY document_id
    ) rev_stat ON rev_stat.document_id = d.document_id
"""

DOCUMENT_HISTORY_INSERT_SQL = text(
    """
    INSERT INTO dms_documents_history (
        document_id,
        document_number,
        document_title,
        document_subject,
        target_folder,
        folder_id,
        sub_folder_id,
        sub_sub_folder_id,
        department,
        location,
        station_id,
        category,
        document_type,
        custodian_id,
        custodian_name,
        open_date,
        close_date,
        volume,
        security_classification,
        retention_class,
        confidential_document,
        status,
        revision,
        revision_number,
        revision_note,
        physical_rack,
        physical_shelf,
        physical_box,
        custody_list,
        individual_engineer,
        file_path,
        file_name,
        file_size,
        file_type,
        description,
        tags,
        is_deleted,
        created_by,
        created_at,
        updated_by,
        updated_at
    )
    SELECT
        document_id,
        document_number,
        document_title,
        document_subject,
        target_folder,
        folder_id,
        sub_folder_id,
        sub_sub_folder_id,
        department,
        location,
        station_id,
        category,
        document_type,
        custodian_id,
        custodian_name,
        open_date,
        close_date,
        volume,
        security_classification,
        retention_class,
        confidential_document,
        status,
        revision,
        revision_number,
        revision_note,
        physical_rack,
        physical_shelf,
        physical_box,
        custody_list,
        individual_engineer,
        file_path,
        file_name,
        file_size,
        file_type,
        description,
        tags,
        is_deleted,
        created_by,
        created_at,
        updated_by,
        updated_at
    FROM dms_documents
    WHERE document_id = :document_id
"""
)


def generate_dms_document_number(db: Session, payload: dict) -> str:
    """
    Auto-generate document number with format:
    PMHBL - {TARGET_FOLDER} - {DEPARTMENT} - {MM/YYYY} - {ID:03d}
    """
    # 1. Target Folder segment
    tf_code = ""
    sf_id = payload.get("sub_folder_id")
    if sf_id:
        sf_row = (
            db.execute(
                text(
                    "SELECT sub_folder_code FROM dms_sub_folders WHERE sub_folder_id = :sf_id"
                ),
                {"sf_id": sf_id},
            )
            .mappings()
            .first()
        )
        if sf_row and sf_row.get("sub_folder_code"):
            candidate_code = str(sf_row["sub_folder_code"]).strip().upper()
            if candidate_code not in ["OTHER", "OTHERS", "OTHER..."]:
                tf_code = candidate_code

    if not tf_code:
        tf_raw = payload.get("target_folder") or ""
        fid = payload.get("folder_id")
        if not tf_raw and fid:
            f_row = (
                db.execute(
                    text("SELECT folder_name FROM dms_folders WHERE folder_id = :fid"),
                    {"fid": fid},
                )
                .mappings()
                .first()
            )
            if f_row and f_row.get("folder_name"):
                tf_raw = f_row["folder_name"]

        clean_tf = str(tf_raw).strip().upper()
        if "REGULATION" in clean_tf or "STANDARD" in clean_tf or "ACT" in clean_tf:
            tf_code = "ACT"
        elif "IMS" in clean_tf:
            tf_code = "IMS"
        elif "POLICY" in clean_tf or "POLICIES" in clean_tf:
            tf_code = "POL"
        elif "PROCEDURE" in clean_tf:
            tf_code = "PRC"
        elif "MANUAL" in clean_tf:
            tf_code = "MAN"
        elif "DRAWING" in clean_tf or "ALIGNMENT" in clean_tf:
            tf_code = "DWG"
        elif "FORM" in clean_tf or "TEMPLATE" in clean_tf:
            tf_code = "FMT"
        elif clean_tf and clean_tf not in ["OTHER", "OTHERS", "OTHER..."]:
            tf_code = clean_tf
        else:
            tf_code = "DOC"

    # Clean any internal whitespace
    tf_code = tf_code.replace(" ", "")

    # 2. Department / Location segment (directly take extracted code from payload)
    dept_val = (
        str(payload.get("department") or payload.get("location") or "HO")
        .strip()
        .upper()
    )
    if dept_val in ["OTHER", "OTHERS", "OTHER..."] or not dept_val:
        dept_val = str(payload.get("location") or "HO").strip().upper()
    if dept_val in ["OTHER", "OTHERS", "OTHER..."] or not dept_val:
        dept_val = "HO"
    dept_code = dept_val.replace(" ", "")

    # 3. Month/Year segment (MM/YYYY)
    open_d = payload.get("open_date")
    if open_d:
        if isinstance(open_d, (datetime, date)):
            my_str = open_d.strftime("%m/%Y")
        elif isinstance(open_d, str):
            try:
                dt = date.fromisoformat(open_d[:10])
                my_str = dt.strftime("%m/%Y")
            except Exception:
                my_str = datetime.now(IST).strftime("%m/%Y")
        else:
            my_str = datetime.now(IST).strftime("%m/%Y")
    else:
        my_str = datetime.now(IST).strftime("%m/%Y")

    # 4. Sequential ID (3 digits)
    # Check both compact pattern and legacy spaced pattern to maintain continuous numbering without conflict
    prefix_pattern_compact = f"PMHBL-{tf_code}-{dept_code}-{my_str}-%"
    prefix_pattern_spaced = f"PMHBL - {tf_code} - {dept_code} - {my_str} - %"
    max_num_seq = (
        db.execute(
            text(
                """
            SELECT COALESCE(
                MAX(
                    NULLIF(regexp_replace(document_number, '^.*-\\s*(\\d+)$', '\\1'), '')::integer
                ), 0
            ) AS max_seq
            FROM dms_documents
            WHERE document_number LIKE :prefix_pattern_compact
               OR document_number LIKE :prefix_pattern_spaced
        """
            ),
            {
                "prefix_pattern_compact": prefix_pattern_compact,
                "prefix_pattern_spaced": prefix_pattern_spaced,
            },
        ).scalar()
        or 0
    )

    if max_num_seq > 0:
        next_seq = max_num_seq + 1
    else:
        max_id = (
            db.execute(
                text("SELECT COALESCE(MAX(document_id), 0) FROM dms_documents")
            ).scalar()
            or 0
        )
        next_seq = max_id + 1

    candidate = f"PMHBL-{tf_code}-{dept_code}-{my_str}-{next_seq:03d}"
    return clean_document_number(candidate)


# ==============================================================================
# MAIN CRUD OPERATIONS
# ==============================================================================


def create_dms_document(
    db: Session,
    data: DmsDocumentCreate,
    background_tasks: Optional[BackgroundTasks] = None,
):
    """Create a new DMS document master record and initialize baseline revision history."""
    payload = data.model_dump()
    if payload.get("folder_id") == 0:
        payload["folder_id"] = None
    if payload.get("sub_folder_id") == 0:
        payload["sub_folder_id"] = None
    if payload.get("sub_sub_folder_id") == 0:
        payload["sub_sub_folder_id"] = None

    # 0. Resolve target_folder_id / sub_sub_folder_id / sub_folder_id
    raw_target_id = payload.get("target_folder_id")
    if raw_target_id == 0:
        raw_target_id = None

    if raw_target_id is not None:
        # Check if target_folder_id points to a sub-folder (at any nesting level)
        sf_target = db.execute(
            text("SELECT sub_folder_id, folder_id FROM dms_sub_folders WHERE sub_folder_id = :sf_id AND is_deleted = FALSE"),
            {"sf_id": raw_target_id}
        ).mappings().first()

        if sf_target:
            payload["sub_folder_id"] = sf_target["sub_folder_id"]
            payload["sub_sub_folder_id"] = sf_target["sub_folder_id"]
            if not payload.get("folder_id"):
                payload["folder_id"] = sf_target["folder_id"]
            elif payload["folder_id"] != sf_target["folder_id"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid target_folder_id {raw_target_id}: Destination sub-folder belongs to folder {sf_target['folder_id']}, not folder {payload['folder_id']}."
                )
        else:
            # Check if target_folder_id points to a root folder
            f_target = db.execute(
                text("SELECT folder_id FROM dms_folders WHERE folder_id = :fid AND is_deleted = FALSE"),
                {"fid": raw_target_id}
            ).first()
            if f_target:
                payload["folder_id"] = f_target[0]
                payload["sub_folder_id"] = None
                payload["sub_sub_folder_id"] = None
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid target_folder_id {raw_target_id}: Folder or sub-folder does not exist or has been deleted."
                )
    else:
        # Backward compatibility for legacy clients passing sub_sub_folder_id or sub_folder_id
        deepest_sf_id = payload.get("sub_sub_folder_id") or payload.get("sub_folder_id")
        if deepest_sf_id:
            sf_target = db.execute(
                text("SELECT sub_folder_id, folder_id FROM dms_sub_folders WHERE sub_folder_id = :sf_id AND is_deleted = FALSE"),
                {"sf_id": deepest_sf_id}
            ).mappings().first()
            if sf_target:
                payload["sub_folder_id"] = sf_target["sub_folder_id"]
                payload["sub_sub_folder_id"] = sf_target["sub_folder_id"]
                if not payload.get("folder_id"):
                    payload["folder_id"] = sf_target["folder_id"]
                elif payload["folder_id"] != sf_target["folder_id"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid sub_folder_id {deepest_sf_id}: Sub-folder belongs to folder {sf_target['folder_id']}, not folder {payload['folder_id']}."
                    )

    created_by = payload.get("created_by")
    folder_id = payload.get("folder_id")
    sub_folder_id = payload.get("sub_folder_id")

    # 1. Validate that parent folder exists and is not deleted
    if folder_id:
        f_row = db.execute(
            text(
                "SELECT folder_id FROM dms_folders WHERE folder_id = :folder_id AND is_deleted = FALSE"
            ),
            {"folder_id": folder_id},
        ).first()
        if not f_row:
            raise HTTPException(
                status_code=400,
                detail="Invalid folder_id: Folder does not exist or has been deleted.",
            )

    # 3. Validate that sub_folder_id belongs to folder_id
    if sub_folder_id:
        sf_row = (
            db.execute(
                text(
                    "SELECT sub_folder_id, folder_id FROM dms_sub_folders WHERE sub_folder_id = :sf_id AND is_deleted = FALSE"
                ),
                {"sf_id": sub_folder_id},
            )
            .mappings()
            .first()
        )
        if not sf_row:
            raise HTTPException(
                status_code=400,
                detail="Invalid sub_folder_id: Sub-folder does not exist or has been deleted.",
            )
        if folder_id and sf_row["folder_id"] != folder_id:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sub_folder_id {sub_folder_id}: Sub-folder belongs to folder {sf_row['folder_id']}, not folder {folder_id}.",
            )

    # 4. Validate file_path
    _validate_file_path(payload.get("file_path"))

    # Validate unique document_title (case-insensitive & trimmed) in the same folder / sub-folder scope
    doc_title = payload.get("document_title")
    if doc_title and str(doc_title).strip():
        clean_doc_title = str(doc_title).strip()
        where_conds = [
            "LOWER(TRIM(document_title)) = LOWER(TRIM(:doc_title))",
            "is_deleted = FALSE",
        ]
        params = {"doc_title": clean_doc_title}
        if folder_id is not None:
            where_conds.append("folder_id = :folder_id")
            params["folder_id"] = folder_id
        else:
            where_conds.append("folder_id IS NULL")

        if sub_folder_id is not None:
            where_conds.append("sub_folder_id = :sub_folder_id")
            params["sub_folder_id"] = sub_folder_id
        else:
            where_conds.append("sub_folder_id IS NULL")

        existing_doc = db.execute(
            text(
                f"SELECT document_id FROM dms_documents WHERE {' AND '.join(where_conds)} LIMIT 1"
            ),
            params,
        ).first()
        if existing_doc:
            raise HTTPException(
                status_code=400,
                detail=f"Document title '{clean_doc_title}' already exists in this folder / sub-folder",
            )
        payload["document_title"] = clean_doc_title

    # 5. Validate status against enum
    status_val = (payload.get("status") or "ACTIVE").upper()
    if status_val not in ALLOWED_DOCUMENT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.get('status')}'. Allowed statuses are: {', '.join(sorted(ALLOWED_DOCUMENT_STATUSES))}.",
        )
    payload["status"] = status_val

    # Clean any "Other..." label directly from payload using shared helper
    if "department" in payload:
        payload["department"] = _clean_payload_value(payload.get("department"))
    if "location" in payload:
        payload["location"] = _clean_payload_value(payload.get("location"))
    if "target_folder" in payload and str(
        payload.get("target_folder")
    ).strip().lower() in ["other...", "other", "others"]:
        payload["target_folder"] = None

    # 6. Auto-generate document_number
    if not payload.get("document_number"):
        payload["document_number"] = generate_dms_document_number(db, payload)
    else:
        payload["document_number"] = clean_document_number(str(payload["document_number"]))

    # 7. Set initial revision baseline
    if not payload.get("revision"):
        payload["revision"] = "Rev 01"
    if not payload.get("revision_number"):
        payload["revision_number"] = 1
    if not payload.get("revision_note"):
        payload["revision_note"] = (
            payload.get("description") or "Initial Baseline Deposit"
        )

    insert_master = text(
        """
        INSERT INTO dms_documents (
            document_number,
            document_title,
            document_subject,
            target_folder,
            folder_id,
            sub_folder_id,
            sub_sub_folder_id,
            department,
            location,
            station_id,
            category,
            document_type,
            custodian_id,
            custodian_name,
            open_date,
            close_date,
            volume,
            security_classification,
            retention_class,
            confidential_document,
            revision,
            revision_number,
            revision_note,
            physical_rack,
            physical_shelf,
            physical_box,
            status,
            custody_list,
            individual_engineer,
            file_path,
            file_name,
            file_size,
            file_type,
            description,
            tags,
            is_deleted,
            created_by
        )
        VALUES (
            :document_number,
            :document_title,
            :document_subject,
            :target_folder,
            :folder_id,
            :sub_folder_id,
            :sub_sub_folder_id,
            :department,
            :location,
            :station_id,
            :category,
            :document_type,
            :custodian_id,
            :custodian_name,
            :open_date,
            :close_date,
            :volume,
            :security_classification,
            :retention_class,
            :confidential_document,
            :revision,
            :revision_number,
            :revision_note,
            :physical_rack,
            :physical_shelf,
            :physical_box,
            :status,
            :custody_list,
            :individual_engineer,
            :file_path,
            :file_name,
            :file_size,
            :file_type,
            :description,
            :tags,
            FALSE,
            :created_by
        )
        RETURNING document_id
    """
    ).bindparams(
        bindparam("custody_list", type_=JSONB),
        bindparam("individual_engineer", type_=JSONB),
        bindparam("tags", type_=JSONB),
    )

    try:
        document_id = db.execute(insert_master, payload).scalar()
        db.commit()

        # Trigger notification to custodian and folder publishers
        try:
            from app.crud.dms.dms_notification_crud import notify_document_created
            notify_document_created(
                db=db,
                document_id=document_id,
                creator_id=data.created_by,
                background_tasks=background_tasks,
            )
        except Exception as ne:
            logger.debug("[dms_document] Notification create dispatch error: %s", ne)

        return document_id
    except HTTPException:
        db.rollback()
        fp = payload.get("file_path")
        if fp:
            try:
                norm_fp = os.path.abspath(fp)
                upload_dir = get_dms_upload_dir()
                if os.path.commonpath(
                    [norm_fp, upload_dir]
                ) == upload_dir and os.path.exists(norm_fp):
                    os.remove(norm_fp)
            except OSError:
                pass
        raise
    except sa_exc.DataError as e:
        # DB constraint violation – e.g. value too long for a VARCHAR column.
        # Return 400 so the caller knows it sent bad data, not a server crash.
        db.rollback()
        fp = payload.get("file_path")
        if fp:
            try:
                norm_fp = os.path.abspath(fp)
                upload_dir = get_dms_upload_dir()
                if os.path.commonpath(
                    [norm_fp, upload_dir]
                ) == upload_dir and os.path.exists(norm_fp):
                    os.remove(norm_fp)
            except OSError:
                pass
        orig = str(e.orig) if hasattr(e, "orig") else str(e)
        logger.warning(f"DMS document create – data validation error: {orig}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid field value: {orig}"
        )
    except Exception as e:
        db.rollback()
        fp = payload.get("file_path")
        if fp:
            try:
                norm_fp = os.path.abspath(fp)
                upload_dir = get_dms_upload_dir()
                if os.path.commonpath(
                    [norm_fp, upload_dir]
                ) == upload_dir and os.path.exists(norm_fp):
                    os.remove(norm_fp)
            except OSError:
                pass
        logger.error(f"Failed to create DMS document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create DMS document")


def update_dms_document(
    db: Session,
    document_id: int,
    data: DmsDocumentUpdate,
    background_tasks: Optional[BackgroundTasks] = None,
):
    """Update an existing DMS document and record revision change in history."""
    # Verify document exists and is not deleted
    curr_doc = (
        db.execute(
            text(
                "SELECT document_id, folder_id, sub_folder_id, status, file_path, file_name, revision, revision_number, confidential_document, security_classification, created_by, custodian_id FROM dms_documents WHERE document_id = :doc_id AND is_deleted = FALSE"
            ),
            {"doc_id": document_id},
        )
        .mappings()
        .first()
    )
    if not curr_doc:
        raise DocumentNotFoundException("Document not found")

    payload = data.model_dump(exclude_unset=True)

    # Never allow updating creation audit fields on PUT calls
    payload.pop("created_at", None)
    payload.pop("created_by", None)

    if not payload:
        return 0

    if payload.get("folder_id") == 0:
        payload["folder_id"] = None
    if payload.get("sub_folder_id") == 0:
        payload["sub_folder_id"] = None
    if payload.get("sub_sub_folder_id") == 0:
        payload["sub_sub_folder_id"] = None

    updated_by = payload.get("updated_by")
    if updated_by and not _check_confidential_access(db, updated_by, dict(curr_doc)):
        raise HTTPException(
            status_code=403,
            detail="Access Denied: This document is confidential. An approved access request is required.",
        )

    # 0. Resolve target_folder_id if supplied
    raw_target_id = payload.get("target_folder_id")
    if raw_target_id == 0:
        raw_target_id = None

    if raw_target_id is not None:
        sf_target = db.execute(
            text("SELECT sub_folder_id, folder_id FROM dms_sub_folders WHERE sub_folder_id = :sf_id AND is_deleted = FALSE"),
            {"sf_id": raw_target_id}
        ).mappings().first()

        if sf_target:
            payload["sub_folder_id"] = sf_target["sub_folder_id"]
            payload["sub_sub_folder_id"] = sf_target["sub_folder_id"]
            if not payload.get("folder_id"):
                payload["folder_id"] = sf_target["folder_id"]
            elif payload["folder_id"] != sf_target["folder_id"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid target_folder_id {raw_target_id}: Destination sub-folder belongs to folder {sf_target['folder_id']}, not folder {payload['folder_id']}."
                )
        else:
            f_target = db.execute(
                text("SELECT folder_id FROM dms_folders WHERE folder_id = :fid AND is_deleted = FALSE"),
                {"fid": raw_target_id}
            ).first()
            if f_target:
                payload["folder_id"] = f_target[0]
                payload["sub_folder_id"] = None
                payload["sub_sub_folder_id"] = None
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid target_folder_id {raw_target_id}: Folder or sub-folder does not exist or has been deleted."
                )
    elif "sub_sub_folder_id" in payload or "sub_folder_id" in payload:
        deepest_sf_id = payload.get("sub_sub_folder_id") or payload.get("sub_folder_id")
        if deepest_sf_id:
            sf_target = db.execute(
                text("SELECT sub_folder_id, folder_id FROM dms_sub_folders WHERE sub_folder_id = :sf_id AND is_deleted = FALSE"),
                {"sf_id": deepest_sf_id}
            ).mappings().first()
            if sf_target:
                payload["sub_folder_id"] = sf_target["sub_folder_id"]
                payload["sub_sub_folder_id"] = sf_target["sub_folder_id"]
                if not payload.get("folder_id"):
                    payload["folder_id"] = sf_target["folder_id"]
                elif payload["folder_id"] != sf_target["folder_id"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid sub_folder_id {deepest_sf_id}: Sub-folder belongs to folder {sf_target['folder_id']}, not folder {payload['folder_id']}."
                    )

    # 1. Validate folder existence if changed
    target_folder_id = payload.get("folder_id", curr_doc.get("folder_id"))
    if "folder_id" in payload and payload["folder_id"]:
        f_row = db.execute(
            text(
                "SELECT folder_id FROM dms_folders WHERE folder_id = :folder_id AND is_deleted = FALSE"
            ),
            {"folder_id": payload["folder_id"]},
        ).first()
        if not f_row:
            raise HTTPException(
                status_code=400,
                detail="Invalid folder_id: Folder does not exist or has been deleted.",
            )

    # 3. Validate that sub_folder_id belongs to target_folder_id
    if "sub_folder_id" in payload and payload["sub_folder_id"]:
        sf_row = (
            db.execute(
                text(
                    "SELECT sub_folder_id, folder_id FROM dms_sub_folders WHERE sub_folder_id = :sf_id AND is_deleted = FALSE"
                ),
                {"sf_id": payload["sub_folder_id"]},
            )
            .mappings()
            .first()
        )
        if not sf_row:
            raise HTTPException(
                status_code=400,
                detail="Invalid sub_folder_id: Sub-folder does not exist or has been deleted.",
            )
        if target_folder_id and sf_row["folder_id"] != target_folder_id:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sub_folder_id {payload['sub_folder_id']}: Sub-folder belongs to folder {sf_row['folder_id']}, not folder {target_folder_id}.",
            )

    # 4. Validate file_path
    if "file_path" in payload:
        _validate_file_path(payload["file_path"])

    # 5. Validate status against enum if provided
    if "status" in payload and payload["status"]:
        status_val = payload["status"].upper()
        if status_val not in ALLOWED_DOCUMENT_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{payload['status']}'. Allowed statuses are: {', '.join(sorted(ALLOWED_DOCUMENT_STATUSES))}.",
            )
        payload["status"] = status_val

    # Clean any "Other..." label directly from payload using shared helper
    if "department" in payload:
        payload["department"] = _clean_payload_value(payload.get("department"))
    if "location" in payload:
        payload["location"] = _clean_payload_value(payload.get("location"))
    if "target_folder" in payload and str(
        payload.get("target_folder")
    ).strip().lower() in ["other...", "other", "others"]:
        payload["target_folder"] = None

    payload["document_id"] = document_id

    # Validate unique document_title if document_title, folder_id, or sub_folder_id is updated
    target_folder_id = payload.get("folder_id", curr_doc.get("folder_id"))
    target_sub_folder_id = payload.get("sub_folder_id", curr_doc.get("sub_folder_id"))
    target_doc_title = payload.get("document_title", curr_doc.get("document_title"))

    if target_doc_title and (
        "document_title" in payload
        or "folder_id" in payload
        or "sub_folder_id" in payload
    ):
        clean_doc_title = str(target_doc_title).strip()
        where_conds = [
            "LOWER(TRIM(document_title)) = LOWER(TRIM(:doc_title))",
            "document_id != :document_id",
            "is_deleted = FALSE",
        ]
        params = {"doc_title": clean_doc_title, "document_id": document_id}
        if target_folder_id is not None:
            where_conds.append("folder_id = :folder_id")
            params["folder_id"] = target_folder_id
        else:
            where_conds.append("folder_id IS NULL")

        if target_sub_folder_id is not None:
            where_conds.append("sub_folder_id = :sub_folder_id")
            params["sub_folder_id"] = target_sub_folder_id
        else:
            where_conds.append("sub_folder_id IS NULL")

        existing_doc = db.execute(
            text(
                f"SELECT document_id FROM dms_documents WHERE {' AND '.join(where_conds)} LIMIT 1"
            ),
            params,
        ).first()
        if existing_doc:
            raise HTTPException(
                status_code=400,
                detail=f"Document title '{clean_doc_title}' already exists in this folder / sub-folder",
            )
        if "document_title" in payload:
            payload["document_title"] = clean_doc_title

    # 6. Revision Auto-management
    new_fp = payload.get("file_path")
    curr_fp = curr_doc.get("file_path")
    if new_fp and new_fp != curr_fp and "revision" not in payload:
        curr_r_num = curr_doc.get("revision_number") or 1
        new_r_num = curr_r_num + 1
        payload["revision_number"] = new_r_num
        payload["revision"] = f"Rev {new_r_num:02d}"
    elif (
        "revision" in payload
        and payload["revision"]
        and "revision_number" not in payload
    ):
        m = re.search(r"\d+", str(payload["revision"]))
        if m:
            payload["revision_number"] = int(m.group(0))

    # Build dynamic SET clause (without COALESCE to allow clearing fields)
    set_clauses = []
    field_map = {
        "document_title": "document_title",
        "document_subject": "document_subject",
        "target_folder": "target_folder",
        "folder_id": "folder_id",
        "sub_folder_id": "sub_folder_id",
        "sub_sub_folder_id": "sub_sub_folder_id",
        "department": "department",
        "location": "location",
        "station_id": "station_id",
        "category": "category",
        "document_type": "document_type",
        "custodian_id": "custodian_id",
        "custodian_name": "custodian_name",
        "open_date": "open_date",
        "close_date": "close_date",
        "volume": "volume",
        "security_classification": "security_classification",
        "retention_class": "retention_class",
        "confidential_document": "confidential_document",
        "revision": "revision",
        "revision_number": "revision_number",
        "revision_note": "revision_note",
        "physical_rack": "physical_rack",
        "physical_shelf": "physical_shelf",
        "physical_box": "physical_box",
        "status": "status",
        "custody_list": "custody_list",
        "individual_engineer": "individual_engineer",
        "file_path": "file_path",
        "file_name": "file_name",
        "file_size": "file_size",
        "file_type": "file_type",
        "description": "description",
        "tags": "tags",
        "updated_by": "updated_by",
    }

    bind_params = []
    for key, col in field_map.items():
        if key in payload:
            set_clauses.append(f"{col} = :{key}")
            if key in ("custody_list", "individual_engineer", "tags"):
                bind_params.append(bindparam(key, type_=JSONB))

    if not set_clauses:
        return 0

    set_clauses.append("updated_at = NOW()")

    update_sql = f"""
        UPDATE dms_documents
        SET {', '.join(set_clauses)}
        WHERE document_id = :document_id AND is_deleted = FALSE
    """

    update_query = text(update_sql)
    for bp in bind_params:
        update_query = update_query.bindparams(bp)

    try:
        result = db.execute(update_query, payload)
        if result.rowcount == 0:
            raise DocumentNotFoundException("Document not found")
        db.commit()

        # Trigger revision notification if file or revision was updated
        if "file_path" in payload or "revision" in payload or "revision_number" in payload:
            try:
                from app.crud.dms.dms_notification_crud import notify_document_revision
                rev_val = payload.get("revision_number") or payload.get("revision") or curr_doc.get("revision_number") or 1
                notify_document_revision(
                    db=db,
                    document_id=document_id,
                    revision_number=rev_val,
                    actor_id=updated_by,
                    background_tasks=background_tasks,
                )
            except Exception as ne:
                logger.debug("[dms_document] Notification revision error: %s", ne)

        return result.rowcount
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update DMS document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update DMS document")


def get_dms_document(db: Session, document_id: int, user_id: Optional[int] = None):
    """Fetch single DMS document by ID with confidentiality, folder access, and file access validation."""
    query = text(
        f"""
        {DOCUMENT_BASE_SELECT}
        WHERE d.document_id = :document_id AND d.is_deleted = FALSE
    """
    )

    row = db.execute(query, {"document_id": document_id}).mappings().first()
    if not row:
        return None

    # Enforce folder and sub-folder access permissions
    is_unrestricted, allowed_folders, allowed_subfolders = (
        get_user_dms_folder_access(db, user_id) if user_id else (False, set(), set())
    )
    if user_id and not is_unrestricted:
        doc_fid = row.get("folder_id")
        doc_sfid = row.get("sub_folder_id")

        # Check if user has explicit document-level authorization (author, custodian, assigned engineer, or approved request)
        created_by_val = row.get("created_by")
        custodian_id_val = row.get("custodian_id")
        is_author = (
            created_by_val is not None and str(created_by_val).strip() == str(user_id).strip()
        ) or (
            custodian_id_val is not None and str(custodian_id_val).strip() == str(user_id).strip()
        )
        approved_doc_ids = _get_user_approved_document_ids(db, user_id)
        has_doc_override = (
            is_author
            or (document_id in approved_doc_ids)
            or _is_user_in_assigned_engineers(db, user_id, row)
        )

        if not has_doc_override:
            folder_ok = allowed_folders is not None and doc_fid in allowed_folders
            subfolder_ok = (doc_sfid is None) or (
                allowed_subfolders is not None and doc_sfid in allowed_subfolders
            )
            if not (folder_ok and subfolder_ok):
                raise HTTPException(
                    status_code=403,
                    detail="Access Denied: You do not have permission to view documents in this folder or subfolder.",
                )

    # Enforce confidentiality & security classification
    # is_admin is intentionally NOT passed — admins have no blanket bypass for confidential docs.
    if not _check_confidential_access(
        db,
        user_id,
        row,
        allowed_folders=allowed_folders,
        allowed_subfolders=allowed_subfolders,
        is_admin=False,
        is_unrestricted=False,
    ):
        raise HTTPException(
            status_code=403,
            detail="Access Denied: This document is confidential. An approved access request is required.",
        )

    formatted = _format_document_row(row)
    perms = check_document_access_permissions(
        db,
        user_id,
        row,
        allowed_folders=allowed_folders,
        allowed_subfolders=allowed_subfolders,
        is_unrestricted=is_unrestricted,
    )
    formatted.update(perms)
    formatted["has_file_access"] = perms["has_access"]
    if not perms["has_access"]:
        formatted["file_path"] = None  # Mask path if file access is not granted

    # Attach breadcrumbs, folder path, and lineage for arbitrary nesting depth
    b_data = get_document_folder_breadcrumbs(
        db, formatted.get("folder_id"), formatted.get("sub_folder_id")
    )
    formatted.update(b_data)
    formatted["target_folder_id"] = formatted.get("sub_folder_id") or formatted.get("folder_id")

    return formatted


def get_all_dms_documents(db: Session, user_id: Optional[int] = None):
    """Fetch all active DMS documents with folder/subfolder access filtering, confidentiality checks, and frontend access flags."""
    is_admin = is_user_dms_admin(db, user_id) if user_id else False
    is_unrestricted, allowed_folders, allowed_subfolders = (
        get_user_dms_folder_access(db, user_id) if user_id else (False, set(), set())
    )

    where_clauses = ["d.is_deleted = FALSE"]
    params: Dict[str, Any] = {}
    expanding_params: List[str] = []

    # Always pre-fetch approved doc IDs (needed for confidential filter for ALL users, including admins)
    approved_doc_ids_for_conf = _get_user_approved_document_ids(db, user_id) if user_id else set()

    # DB-level confidential guard — applies to ALL users including admins.
    # Confidential/restricted docs are only visible to: creator, custodian, approved access, or publisher-assigned folder/subfolder.
    # Admins do NOT have a blanket bypass for confidential documents.
    if user_id:
        _uid_param_set = False
        _conf_exc: List[str] = ["d.created_by = :conf_uid", "d.custodian_id = :conf_uid"]
        params["conf_uid"] = user_id
        if approved_doc_ids_for_conf:
            params["conf_approved_ids"] = list(approved_doc_ids_for_conf)
            expanding_params.append("conf_approved_ids")
            _conf_exc.append("d.document_id IN :conf_approved_ids")
        # Publisher folder/subfolder access (real assigned folders, NOT admin bypass)
        _, _pub_fids, _pub_sfids = get_user_dms_folder_access(db, user_id, ignore_admin=True)
        if _pub_fids:
            params["conf_fids"] = list(_pub_fids)
            expanding_params.append("conf_fids")
            if _pub_sfids:
                params["conf_sfids"] = list(_pub_sfids)
                expanding_params.append("conf_sfids")
                _conf_exc.append(
                    "(d.folder_id IN :conf_fids AND (d.sub_folder_id IS NULL OR d.sub_folder_id IN :conf_sfids))"
                )
            else:
                _conf_exc.append("(d.folder_id IN :conf_fids AND d.sub_folder_id IS NULL)")
        elif _pub_sfids:
            params["conf_sfids"] = list(_pub_sfids)
            expanding_params.append("conf_sfids")
            _conf_exc.append("d.sub_folder_id IN :conf_sfids")
        _conf_exc_sql = " OR ".join(_conf_exc)
        where_clauses.append(
            "(d.confidential_document = FALSE "
            "AND UPPER(COALESCE(d.security_classification, '')) "
            "NOT IN ('CONFIDENTIAL', 'SECRET', 'RESTRICTED') "
            f"OR ({_conf_exc_sql}))"
        )

    if not is_unrestricted:
        if not user_id:
            return []

        approved_doc_ids = _get_user_approved_document_ids(db, user_id)
        folder_conditions = ["d.created_by = :uid", "d.custodian_id = :uid"]
        params["uid"] = user_id

        if approved_doc_ids:
            params["approved_ids"] = list(approved_doc_ids)
            expanding_params.append("approved_ids")
            folder_conditions.append("d.document_id IN :approved_ids")

        if allowed_folders:
            params["allowed_fids"] = list(allowed_folders)
            expanding_params.append("allowed_fids")
            if allowed_subfolders:
                params["allowed_sfids"] = list(allowed_subfolders)
                expanding_params.append("allowed_sfids")
                folder_conditions.append(
                    "(d.folder_id IN :allowed_fids AND (d.sub_folder_id IS NULL OR d.sub_folder_id IN :allowed_sfids))"
                )
            else:
                # Publisher assigned to folder(s) with NO subfolder assignments:
                # only root-level docs (sub_folder_id IS NULL) from their folders.
                folder_conditions.append(
                    "(d.folder_id IN :allowed_fids AND d.sub_folder_id IS NULL)"
                )
        elif allowed_subfolders:
            params["allowed_sfids"] = list(allowed_subfolders)
            expanding_params.append("allowed_sfids")
            folder_conditions.append("d.sub_folder_id IN :allowed_sfids")

        where_clauses.append(f"({' OR '.join(folder_conditions)})")

        # DB-level safety net: exclude confidential/restricted docs for non-privileged users.
        # Exceptions: creator, custodian, approved access requests, or publisher-assigned folder/subfolder.
        _conf_exceptions = ["d.created_by = :uid", "d.custodian_id = :uid"]
        if approved_doc_ids:
            _conf_exceptions.append("d.document_id IN :approved_ids")
        if allowed_folders and allowed_subfolders:
            _conf_exceptions.append(
                "(d.folder_id IN :allowed_fids AND (d.sub_folder_id IS NULL OR d.sub_folder_id IN :allowed_sfids))"
            )
        elif allowed_folders:
            _conf_exceptions.append("(d.folder_id IN :allowed_fids AND d.sub_folder_id IS NULL)")
        elif allowed_subfolders:
            _conf_exceptions.append("d.sub_folder_id IN :allowed_sfids")
        _exceptions_sql = " OR ".join(_conf_exceptions)
        where_clauses.append(
            "(d.confidential_document = FALSE "
            "AND UPPER(COALESCE(d.security_classification, '')) "
            "NOT IN ('CONFIDENTIAL', 'SECRET', 'RESTRICTED') "
            f"OR ({_exceptions_sql}))"
        )

    where_sql = " AND ".join(where_clauses)
    query = text(
        f"""
        {DOCUMENT_BASE_SELECT}
        WHERE {where_sql}
        ORDER BY d.document_id DESC
    """
    )
    for p in expanding_params:
        query = query.bindparams(bindparam(p, expanding=True))

    rows = db.execute(query, params).mappings().all()

    approved_doc_ids = (
        _get_user_approved_document_ids(db, user_id) if user_id else set()
    )
    pending_doc_map = _get_user_pending_document_ids(db, user_id) if user_id else {}
    user_identity_cache: Dict[int, Set[str]] = {}

    # Enforce confidentiality: exclude confidential documents unless user has approved access
    results = []
    for r in rows:
        if _check_confidential_access(
            db,
            user_id,
            r,
            approved_doc_ids=approved_doc_ids,
            is_admin=is_admin,
            user_identity_cache=user_identity_cache,
            allowed_folders=allowed_folders,
            allowed_subfolders=allowed_subfolders,
            is_unrestricted=is_unrestricted,
        ):
            formatted = _format_document_row(r)
            perms = check_document_access_permissions(
                db,
                user_id,
                r,
                approved_doc_ids=approved_doc_ids,
                pending_doc_map=pending_doc_map,
                user_identity_cache=user_identity_cache,
                allowed_folders=allowed_folders,
                allowed_subfolders=allowed_subfolders,
                is_admin=is_admin,
                is_unrestricted=is_unrestricted,
            )
            formatted.update(perms)
            formatted["has_file_access"] = perms["has_access"]
            if not perms["has_access"]:
                formatted["file_path"] = None
            results.append(formatted)
    return results


def get_all_archived_dms_documents(db: Session, user_id: Optional[int] = None):
    """
    Fetch archived DMS documents with access filtering and flags:
      - Admin: Can view all archived records across all folders (excluding confidential records without explicit access).
      - All other users: Can only view their own archived records (created_by, updated_by, or custodian_id).
      - Confidential records: Neither Admin nor any other user can view confidential archived records without explicit access.
    """
    is_admin = is_user_dms_admin(db, user_id) if user_id else False
    is_unrestricted, allowed_folders, allowed_subfolders = (
        get_user_dms_folder_access(db, user_id) if user_id else (False, set(), set())
    )

    if not is_admin and not user_id:
        return []

    where_clauses = ["d.is_deleted = FALSE", "UPPER(d.status) = 'ARCHIVED'"]
    params: Dict[str, Any] = {}
    expanding_params: List[str] = []

    # Non-admin users see ONLY their own archived records
    if not is_admin:
        where_clauses.append(
            "(d.created_by = :uid OR d.updated_by = :uid OR d.custodian_id = :uid)"
        )
        params["uid"] = user_id

    where_sql = " AND ".join(where_clauses)
    query = text(
        f"""
        {DOCUMENT_BASE_SELECT}
        WHERE {where_sql}
        ORDER BY d.document_id DESC
    """
    )
    for p in expanding_params:
        query = query.bindparams(bindparam(p, expanding=True))

    rows = db.execute(query, params).mappings().all()
    approved_doc_ids = (
        _get_user_approved_document_ids(db, user_id) if user_id else set()
    )
    pending_doc_map = _get_user_pending_document_ids(db, user_id) if user_id else {}
    user_identity_cache: Dict[int, Set[str]] = {}

    results = []
    for r in rows:
        if _check_confidential_access(
            db,
            user_id,
            r,
            approved_doc_ids=approved_doc_ids,
            is_admin=is_admin,
            user_identity_cache=user_identity_cache,
            allowed_folders=allowed_folders,
            allowed_subfolders=allowed_subfolders,
            is_unrestricted=is_unrestricted,
        ):
            formatted = _format_document_row(r)
            perms = check_document_access_permissions(
                db,
                user_id,
                r,
                approved_doc_ids=approved_doc_ids,
                pending_doc_map=pending_doc_map,
                user_identity_cache=user_identity_cache,
                allowed_folders=allowed_folders,
                allowed_subfolders=allowed_subfolders,
                is_admin=is_admin,
                is_unrestricted=is_unrestricted,
            )
            formatted.update(perms)
            formatted["has_file_access"] = perms["has_access"]
            if not perms["has_access"]:
                formatted["file_path"] = None
            results.append(formatted)
    return results


def get_dms_dashboard_cards(db: Session, user_id: Optional[int] = None):
    """
    Fetch dashboard summary metrics according to DMS governance rules:
      - Admin: Sees platform-wide total records, controlled records, and archived records.
      - Non-Admin (Publisher / Engineer / User): Only sees counts of documents they have permission to access:
          1. Total Records: sum of all documents the user has access to.
          2. Controlled: sum of active/controlled documents the user has access to (excluding ARCHIVED, DRAFT, DELETED).
          3. Under Review: total number of documents for which the user has requested access (pending access requests).
          4. Archive: total number of archived documents the user has access to.
    """
    is_admin = is_user_dms_admin(db, user_id) if user_id else False

    if user_id:
        # Count only documents the user has access to (enforcing confidentiality and folder permissions for all users, including Admin)
        accessible_docs = get_all_dms_documents(db, user_id=user_id)
        total_records = len(accessible_docs)
        controlled = sum(
            1
            for d in accessible_docs
            if (d.get("status") or "").upper() not in ("ARCHIVED", "DRAFT", "DELETED")
        )
        archived_docs = get_all_archived_dms_documents(db, user_id=user_id)
        archive = len(archived_docs)

        under_review = (
            db.execute(
                text(
                    """
                SELECT COUNT(DISTINCT document_id) FROM dms_access_requests
                WHERE requester_id = :uid
                  AND UPPER(status) = 'PENDING'
                  AND is_deleted = FALSE
                  AND document_id IS NOT NULL
            """
                ),
                {"uid": user_id},
            ).scalar()
            or 0
        )
    else:
        total_records = 0
        controlled = 0
        under_review = 0
        archive = 0

    return {
        "total_records": total_records,
        "controlled": controlled,
        "under_review": under_review,
        "archive": archive,
    }


def soft_delete_dms_document(db: Session, document_id: int, deleted_by: int = None):
    """Soft-delete a DMS document and record change in history."""
    # Verify document exists
    doc = (
        db.execute(
            text(
                "SELECT document_id, folder_id, sub_folder_id, confidential_document, security_classification, created_by, custodian_id FROM dms_documents WHERE document_id = :doc_id AND is_deleted = FALSE"
            ),
            {"doc_id": document_id},
        )
        .mappings()
        .first()
    )
    if not doc:
        raise DocumentNotFoundException("Document not found or already deleted")

    if deleted_by and not _check_confidential_access(db, deleted_by, dict(doc)):
        raise HTTPException(
            status_code=403,
            detail="Access Denied: This document is confidential. An approved access request is required.",
        )

    update_query = text(
        """
        UPDATE dms_documents
        SET
            is_deleted = TRUE,
            status = 'DELETED',
            updated_by = :deleted_by,
            updated_at = NOW()
        WHERE document_id = :document_id AND is_deleted = FALSE
    """
    )

    try:
        result = db.execute(
            update_query, {"document_id": document_id, "deleted_by": deleted_by}
        )
        if result.rowcount == 0:
            raise DocumentNotFoundException("Document not found or already deleted")
        db.commit()
        return result.rowcount
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete DMS document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete DMS document")


def get_dms_trash_documents(
    db: Session,
    search: Optional[str] = None,
    folder_id: Optional[int] = None,
    station_id: Optional[int] = None,
    location: Optional[str] = None,
    year: Optional[int] = None,
    sort_by: Optional[str] = "recently_deleted",
    page: int = 1,
    limit: int = 10,
):
    """Fetch paginated soft-deleted documents from trash with filters."""
    total_deleted = (
        db.execute(
            text("SELECT COUNT(1) FROM dms_documents WHERE is_deleted = TRUE")
        ).scalar()
        or 0
    )

    where_clauses = ["d.is_deleted = TRUE"]
    params: Dict[str, Any] = {}

    if folder_id:
        where_clauses.append("d.folder_id = :folder_id")
        params["folder_id"] = folder_id

    if station_id:
        where_clauses.append("d.station_id = :station_id")
        params["station_id"] = station_id

    if location and location.strip():
        where_clauses.append("UPPER(d.location) = :location")
        params["location"] = location.strip().upper()

    if year:
        where_clauses.append("EXTRACT(YEAR FROM d.updated_at) = :year")
        params["year"] = year

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        term_compact = f"%{search.strip().lower().replace(' ', '')}%"
        where_clauses.append(
            """
            (
                LOWER(d.document_number) LIKE :term OR
                REPLACE(LOWER(d.document_number), ' ', '') LIKE :term_compact OR
                LOWER(d.document_title) LIKE :term OR
                LOWER(COALESCE(d.department, '')) LIKE :term OR
                LOWER(CONCAT_WS(' ', uu.first_name, uu.last_name)) LIKE :term
            )
        """
        )
        params["term"] = term
        params["term_compact"] = term_compact

    where_sql = " AND ".join(where_clauses)

    filtered_count = (
        db.execute(
            text(
                f"""
            SELECT COUNT(1)
            FROM dms_documents d
            LEFT JOIN users uu ON uu.id = d.updated_by
            WHERE {where_sql}
        """
            ),
            params,
        ).scalar()
        or 0
    )

    order_by = (
        "d.updated_at DESC" if sort_by == "recently_deleted" else "d.document_id DESC"
    )

    offset = (page - 1) * limit
    params["limit"] = limit
    params["offset"] = offset

    query = text(
        f"""
        SELECT
            d.*,
            f.folder_name,
            sf.sub_folder_name,
            TRIM(CONCAT_WS(' ', uc.first_name, uc.last_name)) AS created_by_name,
            TRIM(CONCAT_WS(' ', uu.first_name, uu.last_name)) AS deleted_by_name,
            d.updated_at AS deleted_at,
            d.updated_by AS deleted_by
        FROM dms_documents d
        LEFT JOIN dms_folders f ON f.folder_id = d.folder_id
        LEFT JOIN dms_sub_folders sf ON sf.sub_folder_id = d.sub_folder_id
        LEFT JOIN users uc ON uc.id = d.created_by
        LEFT JOIN users uu ON uu.id = d.updated_by
        WHERE {where_sql}
        ORDER BY {order_by}
        LIMIT :limit OFFSET :offset
    """
    )

    rows = db.execute(query, params).mappings().all()
    records = []
    for r in rows:
        row_dict = _format_document_row(r)
        if r.get("deleted_at"):
            row_dict["deleted_at"] = to_iso_ist(r.get("deleted_at"))
        row_dict["folder_name"] = r.get("folder_name")
        row_dict["sub_folder_name"] = r.get("sub_folder_name")
        row_dict["deleted_by"] = r.get("deleted_by")
        row_dict["deleted_by_name"] = r.get("deleted_by_name")
        records.append(row_dict)

    return {
        "total_deleted": total_deleted,
        "matching_filter_count": filtered_count,
        "page": page,
        "limit": limit,
        "data": records,
    }


def restore_dms_document(
    db: Session, document_id: int, restored_by: Optional[int] = None
):
    """Restore a soft-deleted document from trash back to active state."""
    doc = (
        db.execute(
            text(
                "SELECT document_id, document_number, document_title, folder_id, sub_folder_id FROM dms_documents WHERE document_id = :doc_id AND is_deleted = TRUE"
            ),
            {"doc_id": document_id},
        )
        .mappings()
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=404, detail="Deleted document not found in trash"
        )

    if doc.get("folder_id"):
        parent_f = db.execute(
            text("SELECT is_deleted FROM dms_folders WHERE folder_id = :fid"),
            {"fid": doc["folder_id"]},
        ).first()
        if parent_f and parent_f[0]:
            raise HTTPException(
                status_code=400,
                detail="Cannot restore document: Its parent folder is currently deleted. Please restore the folder first.",
            )

    update_query = text(
        """
        UPDATE dms_documents
        SET
            is_deleted = FALSE,
            status = 'ACTIVE',
            updated_by = :restored_by,
            updated_at = NOW()
        WHERE document_id = :doc_id AND is_deleted = TRUE
    """
    )

    try:
        db.execute(update_query, {"doc_id": document_id, "restored_by": restored_by})
        db.commit()
        return {
            "status": "success",
            "message": "Document restored successfully",
            "document_id": document_id,
        }
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to restore DMS document {document_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to restore document")


def purge_dms_document(db: Session, document_id: int):
    """Permanently purge a soft-deleted document and its revision history from storage."""
    doc = (
        db.execute(
            text(
                "SELECT document_id, file_path FROM dms_documents WHERE document_id = :doc_id AND is_deleted = TRUE"
            ),
            {"doc_id": document_id},
        )
        .mappings()
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=404, detail="Deleted document not found in trash"
        )

    try:
        db.execute(
            text("DELETE FROM dms_documents_history WHERE document_id = :doc_id"),
            {"doc_id": document_id},
        )
        db.execute(
            text("DELETE FROM dms_documents WHERE document_id = :doc_id"),
            {"doc_id": document_id},
        )
        db.commit()

        fp = doc.get("file_path")
        if fp and os.path.exists(fp):
            try:
                os.remove(fp)
            except Exception as fe:
                logger.warning(f"Could not delete physical file {fp}: {fe}")

        return {
            "status": "success",
            "message": "Document permanently purged",
            "document_id": document_id,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to purge DMS document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to permanently purge document"
        )


def update_dms_document_status(
    db: Session,
    document_id: int,
    status: str,
    updated_by: Optional[int] = None,
    background_tasks: Optional[BackgroundTasks] = None,
):
    """Update document status (ACTIVE / ARCHIVED / INACTIVE) and record change in history."""
    # Verify document exists
    doc = (
        db.execute(
            text(
                "SELECT document_id, folder_id, sub_folder_id, status, confidential_document, security_classification, created_by, custodian_id FROM dms_documents WHERE document_id = :doc_id AND is_deleted = FALSE"
            ),
            {"doc_id": document_id},
        )
        .mappings()
        .first()
    )
    if not doc:
        raise DocumentNotFoundException("Document not found or already deleted")

    if updated_by and not _check_confidential_access(db, updated_by, dict(doc)):
        raise HTTPException(
            status_code=403,
            detail="Access Denied: This document is confidential. An approved access request is required.",
        )

    # Validate status against enum
    status_val = status.upper().strip()
    if status_val not in ALLOWED_DOCUMENT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Allowed statuses are: {', '.join(sorted(ALLOWED_DOCUMENT_STATUSES))}.",
        )

    # Un-archive rule: Admin (all doc) + Publisher (only his archived doc)
    curr_status = (doc.get("status") or "").upper().strip()
    if curr_status == "ARCHIVED" and status_val != "ARCHIVED":
        if updated_by and not is_user_dms_admin(db, updated_by):
            if doc.get("created_by") != updated_by:
                raise HTTPException(
                    status_code=403,
                    detail="Permission denied: You can only un-archive documents published by you.",
                )

    update_query = text(
        """
        UPDATE dms_documents
        SET
            status = :status,
            updated_by = COALESCE(:updated_by, updated_by),
            updated_at = NOW()
        WHERE document_id = :document_id AND is_deleted = FALSE
    """
    )

    try:
        result = db.execute(
            update_query,
            {
                "document_id": document_id,
                "status": status_val,
                "updated_by": updated_by,
            },
        )
        if result.rowcount == 0:
            raise DocumentNotFoundException("Document not found or already deleted")
        db.commit()

        # Trigger notification if status transitioned to ARCHIVED or from ARCHIVED to ACTIVE
        if status_val == "ARCHIVED" or (curr_status == "ARCHIVED" and status_val == "ACTIVE"):
            try:
                from app.crud.dms.dms_notification_crud import notify_document_status_change
                notify_document_status_change(
                    db=db,
                    document_id=document_id,
                    new_status=status_val,
                    actor_id=updated_by,
                    background_tasks=background_tasks,
                )
            except Exception as ne:
                logger.debug("[dms_document] Status change notification error: %s", ne)

        return {"document_id": document_id, "status": status_val}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update DMS document status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to update DMS document status"
        )


async def save_dms_document_file(
    file: UploadFile, custom_file_name: str = None
) -> dict:
    """Validate and securely stream uploaded document file directly to local storage."""
    if not file or not getattr(file, "filename", None):
        raise HTTPException(status_code=400, detail="No file provided")

    # Use os.path.basename on original_name before building safe_name
    raw_name = (file.filename or "").strip()
    original_name = os.path.basename(raw_name)
    if not original_name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    _, ext = os.path.splitext(original_name)
    ext_lower = ext.lower()

    # Explicitly disallow SVGs, videos, archives, and executables
    if ext_lower == ".svg":
        raise HTTPException(
            status_code=400, detail="SVG files are prohibited due to security policies."
        )

    if ext_lower in DISALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Files with extension '{ext_lower}' are not allowed. Executables, videos, and archives are prohibited.",
        )

    if ext_lower not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only standard documents (PDF, Word, Excel, PowerPoint, Text, CSV) and static raster images are allowed.",
        )

    content_type = (file.content_type or "").lower()
    if content_type.startswith("video/") or content_type in (
        "application/zip",
        "application/x-zip-compressed",
        "application/x-rar-compressed",
        "application/x-7z-compressed",
        "application/x-tar",
        "application/gzip",
        "image/svg+xml",
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid file content type. Videos, archives, and SVG files are not permitted.",
        )

    # Disk storage path: Generate safe_name using UUID and validated extension
    upload_dir = get_dms_upload_dir()
    safe_name = f"{uuid.uuid4().hex}{ext_lower}"
    destination_path = os.path.join(upload_dir, safe_name)

    # Stream in chunks (64 KB) directly to disk (O(1) memory); abort and cleanup immediately if > 30MB
    CHUNK_SIZE = 64 * 1024  # 64 KB
    total_bytes = 0
    first_chunk = True

    try:
        with open(destination_path, "wb") as out_file:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break

                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail="File size exceeds the maximum allowed limit of 30MB.",
                    )

                # Validate magic bytes and content on the first chunk before proceeding
                if first_chunk:
                    first_chunk = False

                    # Reject executable binaries (ELF, DOS/Windows PE) regardless of extension
                    if chunk.startswith(b"\x7fELF") or chunk.startswith(b"MZ"):
                        raise HTTPException(
                            status_code=400,
                            detail="Executable file signatures (ELF, PE) are strictly prohibited.",
                        )

                    # Validate known format magic signatures
                    if ext_lower in MAGIC_SIGNATURES:
                        valid_magic = any(
                            chunk.startswith(sig) for sig in MAGIC_SIGNATURES[ext_lower]
                        )
                        if not valid_magic:
                            raise HTTPException(
                                status_code=400,
                                detail=f"File signature mismatch: File content does not match extension '{ext_lower}'.",
                            )

                    # Validate WebP signature (RIFF....WEBP)
                    elif ext_lower == ".webp":
                        if not (
                            chunk.startswith(b"RIFF")
                            and len(chunk) >= 12
                            and chunk[8:12] == b"WEBP"
                        ):
                            raise HTTPException(
                                status_code=400,
                                detail="File content does not match WebP image signature.",
                            )

                    # Validate plain text / CSV content
                    elif ext_lower in (".txt", ".csv"):
                        if b"\x00" in chunk:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Binary content detected in text file with extension '{ext_lower}'.",
                            )
                        sample_lower = chunk[:1024].lower()
                        if b"<svg" in sample_lower or (
                            b"<?xml" in sample_lower and b"svg" in sample_lower
                        ):
                            raise HTTPException(
                                status_code=400,
                                detail="SVG active content is prohibited.",
                            )

                out_file.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    except Exception:
        # Guarantee cleanup of partial/aborted file on disk
        if os.path.exists(destination_path):
            try:
                os.remove(destination_path)
            except OSError:
                pass
        raise

    # Canonical MIME resolution (never trust client-supplied content_type)
    canonical_mime = (
        CANONICAL_MIME_MAP.get(ext_lower)
        or mimetypes.guess_type(original_name)[0]
        or "application/octet-stream"
    )
    display_name = (
        os.path.basename(custom_file_name.strip())
        if custom_file_name
        else original_name
    )

    return {
        "file_name": display_name,
        "file_path": destination_path,
        "file_size": format_file_size(total_bytes),
        "file_type": canonical_mime,
    }


def get_dms_folder_hierarchy(
    db: Session,
    folder_id: Optional[int] = None,
    user_id: Optional[int] = None,
    station_id: Optional[int] = None,
    location: Optional[str] = None,
    controlled_only: bool = False,
) -> Optional[Union[dict, List[dict]]]:
    # -------------------------------------------------------------
    # 1. FETCH FOLDERS (Single Query)
    # -------------------------------------------------------------
    f_where = ["f.is_deleted = FALSE"]
    f_params: Dict[str, Any] = {}

    if folder_id is not None:
        f_where.append("f.folder_id = :folder_id")
        f_params["folder_id"] = folder_id

    folder_query = text(
        f"""
        SELECT
            f.folder_id,
            f.folder_name,
            f.folder_description,
            f.folder_icon,
            f.is_deleted,
            f.created_at,
            f.created_by,
            TRIM(CONCAT_WS(' ', uc.first_name, uc.last_name)) AS created_by_name,
            f.updated_at,
            f.updated_by,
            TRIM(CONCAT_WS(' ', uu.first_name, uu.last_name)) AS updated_by_name
        FROM dms_folders f
        LEFT JOIN users uc ON uc.id = f.created_by
        LEFT JOIN users uu ON uu.id = f.updated_by
        WHERE {' AND '.join(f_where)}
        ORDER BY f.folder_id ASC
    """
    )

    folder_rows = db.execute(folder_query, f_params).mappings().all()
    if not folder_rows:
        return None if folder_id is not None else []

    target_folder_ids = [r["folder_id"] for r in folder_rows]

    folders_map: Dict[int, dict] = {}
    for f in folder_rows:
        fd = dict(f)
        fd["created_at"] = to_iso_ist(fd.get("created_at"))
        fd["updated_at"] = to_iso_ist(fd.get("updated_at"))
        fd["total_sub_folders"] = 0
        fd["total_documents"] = 0
        fd["sub_folders"] = []
        fd["folder_documents"] = []
        fd["root_documents"] = fd["folder_documents"]
        folders_map[fd["folder_id"]] = fd

    # -------------------------------------------------------------
    # 2. FETCH SUB-FOLDERS (Single Bulk Query for all target folders)
    # -------------------------------------------------------------
    sf_params: Dict[str, Any] = {"target_fids": target_folder_ids}
    sf_where = ["sf.folder_id IN :target_fids", "sf.is_deleted = FALSE"]

    subfolder_query = text(
        f"""
        SELECT
            sf.sub_folder_id,
            sf.folder_id,
            sf.parent_sub_folder_id,
            sf.sub_folder_code,
            sf.sub_folder_name,
            sf.sub_folder_description,
            sf.status,
            sf.is_deleted,
            sf.created_at,
            sf.created_by,
            TRIM(CONCAT_WS(' ', uc.first_name, uc.last_name)) AS created_by_name,
            sf.updated_at,
            sf.updated_by,
            TRIM(CONCAT_WS(' ', uu.first_name, uu.last_name)) AS updated_by_name
        FROM dms_sub_folders sf
        LEFT JOIN users uc ON uc.id = sf.created_by
        LEFT JOIN users uu ON uu.id = sf.updated_by
        WHERE {' AND '.join(sf_where)}
        ORDER BY sf.folder_id ASC, sf.sub_folder_id ASC
    """
    ).bindparams(bindparam("target_fids", expanding=True))

    sf_rows = db.execute(subfolder_query, sf_params).mappings().all()

    sf_map: Dict[int, dict] = {}
    for sf in sf_rows:
        sf_dict = dict(sf)
        sf_dict["created_at"] = to_iso_ist(sf_dict.get("created_at"))
        sf_dict["updated_at"] = to_iso_ist(sf_dict.get("updated_at"))
        sf_dict["documents"] = []
        sf_dict["documents_count"] = 0
        sf_dict["children"] = []
        sf_dict["sub_sub_folders"] = sf_dict["children"]
        sf_map[sf_dict["sub_folder_id"]] = sf_dict

    # Build nested tree: attach children to parents, only top-level to folder
    for sf_dict in sf_map.values():
        fid = sf_dict["folder_id"]
        parent_sf_id = sf_dict.get("parent_sub_folder_id")

        if parent_sf_id and parent_sf_id in sf_map:
            # Nested sub-folder: attach to parent sub-folder
            sf_map[parent_sf_id]["children"].append(sf_dict)
        elif fid in folders_map:
            # Top-level sub-folder: attach to folder
            folders_map[fid]["sub_folders"].append(sf_dict)

        if fid in folders_map:
            folders_map[fid]["total_sub_folders"] += 1

    # -------------------------------------------------------------
    # 3. BULK PRE-FETCH APPROVED ACCESS & PENDING REQUESTS (Zero N+1)
    # -------------------------------------------------------------
    is_admin = is_user_dms_admin(db, user_id) if user_id else False
    is_unrestricted, allowed_folders, allowed_subfolders = (
        get_user_dms_folder_access(db, user_id) if user_id else (False, set(), set())
    )
    approved_doc_ids = (
        _get_user_approved_document_ids(db, user_id) if user_id else set()
    )
    pending_doc_map = _get_user_pending_document_ids(db, user_id) if user_id else {}
    user_identity_cache: Dict[int, Set[str]] = {}

    def _is_accessible(doc_item: dict) -> bool:
        # is_admin/is_unrestricted intentionally NOT forwarded — admins have no bypass for confidential docs
        return _check_confidential_access(
            db,
            user_id,
            doc_item,
            approved_doc_ids=approved_doc_ids,
            is_admin=False,
            user_identity_cache=user_identity_cache,
            allowed_folders=allowed_folders,
            allowed_subfolders=allowed_subfolders,
            is_unrestricted=False,
        )

    # -------------------------------------------------------------
    # 4. FETCH DOCUMENTS (Single Bulk Query for all target folders)
    # -------------------------------------------------------------
    doc_where = ["d.folder_id IN :target_fids", "d.is_deleted = FALSE"]
    doc_params: Dict[str, Any] = {"target_fids": target_folder_ids}

    if station_id is not None:
        doc_where.append("d.station_id = :station_id")
        doc_params["station_id"] = station_id

    if location:
        doc_where.append("UPPER(d.location) = :location")
        doc_params["location"] = location.strip().upper()

    doc_query = text(
        f"""
        {DOCUMENT_BASE_SELECT}
        WHERE {' AND '.join(doc_where)}
        ORDER BY d.folder_id ASC, d.sub_folder_id ASC, d.document_id DESC
    """
    ).bindparams(bindparam("target_fids", expanding=True))

    doc_rows = db.execute(doc_query, doc_params).mappings().all()

    # -------------------------------------------------------------
    # 5. IN-MEMORY ASSEMBLY (O(N) grouping, zero database queries)
    # -------------------------------------------------------------
    for doc in doc_rows:
        if not _is_accessible(doc):
            continue

        d_dict = _format_document_row(doc)
        perms = check_document_access_permissions(
            db,
            user_id,
            doc,
            approved_doc_ids=approved_doc_ids,
            pending_doc_map=pending_doc_map,
            user_identity_cache=user_identity_cache,
            allowed_folders=allowed_folders,
            allowed_subfolders=allowed_subfolders,
            is_admin=is_admin,
            is_unrestricted=is_unrestricted,
        )
        d_dict.update(perms)
        d_dict["has_file_access"] = perms["has_access"]
        if not perms["has_access"]:
            d_dict["file_path"] = (
                None  # Secure file path masking for unprivileged users
            )

        # If browsing controlled files only, exclude documents the user cannot view/access
        if controlled_only and not perms["has_access"]:
            continue

        fid = d_dict.get("folder_id")
        sf_id = d_dict.get("sub_sub_folder_id") or d_dict.get("sub_folder_id")

        if fid not in folders_map:
            continue

        folders_map[fid]["total_documents"] += 1

        if sf_id and sf_id in sf_map:
            sf_map[sf_id]["documents"].append(d_dict)
            sf_map[sf_id]["documents_count"] += 1
        else:
            folders_map[fid]["root_documents"].append(d_dict)

    def _has_documents_recursive(sf):
        """Check if a sub-folder or any of its children have documents."""
        if sf.get("documents_count", 0) > 0:
            return True
        return any(_has_documents_recursive(c) for c in sf.get("children", []))

    def _filter_children(sf):
        """Recursively prune empty sub-folders from children."""
        sf["children"] = [c for c in sf.get("children", []) if _has_documents_recursive(c)]
        sf["sub_sub_folders"] = sf["children"]
        for c in sf["children"]:
            _filter_children(c)

    if controlled_only:
        filtered_folders = []
        for f in folders_map.values():
            # Keep only sub-folders (and their nested children) that contain controlled documents
            f["sub_folders"] = [
                sf for sf in f["sub_folders"] if _has_documents_recursive(sf)
            ]
            for sf in f["sub_folders"]:
                _filter_children(sf)
            f["total_sub_folders"] = len(f["sub_folders"])
            # Keep folder only if it has controlled documents (either in sub-folders or root)
            if f.get("total_documents", 0) > 0:
                filtered_folders.append(f)

        if folder_id is not None:
            return next(
                (f for f in filtered_folders if f["folder_id"] == folder_id), None
            )
        return filtered_folders

    if folder_id is not None:
        return folders_map.get(folder_id)

    return list(folders_map.values())


def _build_dms_download_url(
    file_path: Optional[str], history_id: Optional[int] = None
) -> Optional[str]:
    base_url = (os.getenv("BackEndPath") or "").rstrip("/")
    if file_path:
        norm_fp = file_path.replace("\\", "/")
        if "/uploads/" in norm_fp:
            rel = norm_fp[norm_fp.index("/uploads/") :]
            return f"{base_url}{rel}"
        if norm_fp.startswith("uploads/"):
            return f"{base_url}/{norm_fp}"
    if history_id:
        return f"{base_url}/dms-document/download-revision/{history_id}"
    return None


def get_dms_document_revisions(
    db: Session,
    document_id: int,
    user_id: Optional[int] = None,
    version: Optional[str] = None,
) -> Optional[dict]:
    """
    Fetch all revision baselines and version history for a DMS document.
    Modeled after Circular Management version history pattern:
    Returns:
      - document_id: ID of the DMS document
      - versions: Chronological list of version objects, each containing:
          * version: (e.g. 'Rev 01', 'Rev 02')
          * version_date: Timestamp of version deposit/update
          * reason: Revision note or change reason
          * content: Document description / subject
          * master_data: Complete audit snapshot dictionary from dms_documents_history
          * target_audience: Structured custody and engineer audience mapping
          * attachments: Detailed file attachments list with absolute download URLs
      - document, oldest_baseline, revisions, action_urls: Backwards-compatible models
    """

    def _iso_or_val(val: Any) -> Any:
        if isinstance(val, (datetime, date)):
            return val.isoformat()
        return val

    # 1. Fetch document header with folder names
    doc_query = text(
        """
        SELECT
            d.document_id,
            d.document_number,
            d.document_title,
            d.document_subject,
            d.department,
            d.location,
            d.station_id,
            d.target_folder,
            d.folder_id,
            f.folder_name,
            d.sub_folder_id,
            sf.sub_folder_name,
            d.volume,
            d.security_classification,
            d.retention_class,
            d.confidential_document,
            d.status,
            COALESCE(d.revision, 'Rev 01') AS current_revision,
            COALESCE(d.revision_number, 1) AS current_revision_number,
            d.file_path AS current_file_path,
            d.file_name AS current_file_name,
            d.file_size AS current_file_size,
            d.file_type AS current_file_type,
            d.created_at,
            d.created_by,
            d.updated_at,
            d.updated_by,
            d.custodian_id
        FROM dms_documents d
        LEFT JOIN dms_folders f ON f.folder_id = d.folder_id
        LEFT JOIN dms_sub_folders sf ON sf.sub_folder_id = d.sub_folder_id
        WHERE d.document_id = :doc_id AND d.is_deleted = FALSE
    """
    )
    doc = db.execute(doc_query, {"doc_id": document_id}).mappings().first()
    if not doc:
        return None

    doc_dict = dict(doc)
    if not _check_confidential_access(db, user_id, doc_dict):
        raise HTTPException(
            status_code=403, detail="Permission denied: confidential document"
        )

    # 2. Check if a specific version cutoff was requested (like circular management)
    target_cutoff_date = None
    if version:
        cutoff_query = text(
            """
            SELECT COALESCE(h.updated_at, h.history_created_at, h.created_at) AS vdate
            FROM dms_documents_history h
            WHERE h.document_id = :doc_id
              AND (LOWER(TRIM(h.revision)) = LOWER(TRIM(:ver)) OR h.revision_number::text = TRIM(:ver))
            ORDER BY h.history_id DESC
            LIMIT 1
        """
        )
        target_cutoff_date = db.execute(
            cutoff_query, {"doc_id": document_id, "ver": version.strip()}
        ).scalar()

    params: Dict[str, Any] = {"doc_id": document_id}
    cutoff_filter = ""
    if target_cutoff_date:
        cutoff_filter = "AND COALESCE(h.updated_at, h.history_created_at, h.created_at) <= :cutoff_date"
        params["cutoff_date"] = target_cutoff_date

    # 3. Fetch history records deduplicated by revision ordered by history_id ASC
    hist_query = text(
        f"""
        SELECT
            h.*,
            f.folder_name,
            sf.sub_folder_name,
            COALESCE(h.updated_by, h.created_by) AS deposited_by_id,
            TRIM(CONCAT_WS(' ', u.first_name, u.last_name)) AS deposited_by_name
        FROM (
            SELECT DISTINCT ON (COALESCE(revision, 'Rev ' || LPAD(revision_number::text, 2, '0'))) *
            FROM dms_documents_history
            WHERE document_id = :doc_id
            {cutoff_filter}
            ORDER BY COALESCE(revision, 'Rev ' || LPAD(revision_number::text, 2, '0')), history_id DESC
        ) h
        LEFT JOIN dms_folders f ON f.folder_id = h.folder_id
        LEFT JOIN dms_sub_folders sf ON sf.sub_folder_id = h.sub_folder_id
        LEFT JOIN users u ON u.id = COALESCE(h.updated_by, h.created_by)
        ORDER BY h.history_id ASC
    """
    )
    hist_rows = db.execute(hist_query, params).mappings().all()

    revisions_list: List[Dict[str, Any]] = []

    for idx, row in enumerate(hist_rows, start=1):
        h = dict(row)
        rev_num = h.get("revision_number") or idx
        rev_label = h.get("revision") or f"Rev {rev_num:02d}"

        # Clean file type & name
        f_type = h.get("file_type") or ""
        f_name = h.get("file_name") or ""
        f_path = h.get("file_path") or ""
        f_size = h.get("file_size") or ""
        if not f_type and f_name:
            ext = os.path.splitext(f_name)[1].replace(".", "").upper()
            f_type = ext if ext else "PDF"

        ts = h.get("history_created_at") or h.get("updated_at") or h.get("created_at")
        dep_at = format_datetime_ist_display(ts)
        dep_by_id = h.get("deposited_by_id")
        dep_by_name = h.get("deposited_by_name") or "System"

        rev_desc = h.get("revision_note") or h.get("description")
        if not rev_desc and idx == 1:
            rev_desc = (
                "Initial Baseline Deposit - Original contract & drawing specifications"
            )

        revision_item = {
            "history_id": h["history_id"],
            "revision": rev_label,
            "revision_number": rev_num,
            "is_current_active": False,
            "is_oldest_baseline": (idx == 1),
            "file_name": f_name or doc_dict.get("current_file_name"),
            "file_path": f_path or doc_dict.get("current_file_path"),
            "file_size": f_size or doc_dict.get("current_file_size") or "—",
            "file_type": f_type.upper() if f_type else "PDF",
            "deposited_at": dep_at,
            "deposited_by_id": dep_by_id,
            "deposited_by_name": dep_by_name,
            "description": rev_desc
            or "Active controlled release with authorized compliance approval",
            "download_url": f"/dms-document/download-revision/{h['history_id']}",
        }
        revisions_list.append(revision_item)

    if not revisions_list:
        # Fallback synthesized baseline if history was empty
        ts = doc_dict.get("updated_at") or doc_dict.get("created_at")
        f_name = doc_dict.get("current_file_name") or ""
        f_type = doc_dict.get("current_file_type") or (
            os.path.splitext(f_name)[1].replace(".", "").upper() if f_name else "PDF"
        )
        f_path = doc_dict.get("current_file_path") or ""
        f_size = doc_dict.get("current_file_size") or "—"
        rev_label = doc_dict.get("current_revision") or "Rev 01"

        revisions_list.append(
            {
                "history_id": 0,
                "revision": rev_label,
                "revision_number": 1,
                "is_current_active": True,
                "is_oldest_baseline": True,
                "file_name": f_name,
                "file_path": f_path,
                "file_size": f_size,
                "file_type": f_type,
                "deposited_at": format_datetime_ist_display(ts),
                "deposited_by_id": doc_dict.get("created_by"),
                "deposited_by_name": "System",
                "description": "Initial Baseline Deposit - Original contract & drawing specifications",
                "download_url": f"/dms-document/download/{document_id}",
            }
        )

    # Chronologically last entry is current active release
    revisions_list[-1]["is_current_active"] = True

    # Oldest baseline is first entry
    oldest_item = revisions_list[0]
    oldest_baseline = {
        "history_id": oldest_item["history_id"],
        "revision": oldest_item["revision"],
        "revision_number": oldest_item["revision_number"],
        "registered_date": oldest_item["deposited_at"],
        "registered_by_id": oldest_item["deposited_by_id"],
        "registered_by_name": oldest_item["deposited_by_name"],
        "file_name": oldest_item["file_name"],
        "file_size": oldest_item["file_size"],
        "file_type": oldest_item["file_type"],
        "description": oldest_item["description"],
        "download_url": oldest_item["download_url"],
    }

    # Order newest first for UI list
    revisions_ordered = list(reversed(revisions_list))
    active_rev = revisions_ordered[0]["revision"]

    doc_header = {
        "document_id": doc_dict["document_id"],
        "document_number": clean_document_number(doc_dict.get("document_number")),
        "document_title": doc_dict.get("document_title"),
        "document_subject": doc_dict.get("document_subject"),
        "department": doc_dict.get("department"),
        "location": doc_dict.get("location"),
        "station_id": doc_dict.get("station_id"),
        "target_folder": doc_dict.get("target_folder"),
        "folder_id": doc_dict.get("folder_id"),
        "folder_name": doc_dict.get("folder_name"),
        "sub_folder_id": doc_dict.get("sub_folder_id"),
        "sub_folder_name": doc_dict.get("sub_folder_name"),
        "volume": doc_dict.get("volume"),
        "security_classification": doc_dict.get("security_classification"),
        "status": doc_dict.get("status"),
        "current_revision": active_rev,
        "current_file_name": doc_dict.get("current_file_name"),
        "current_file_size": doc_dict.get("current_file_size"),
        "current_file_type": doc_dict.get("current_file_type"),
        "current_download_url": f"/dms-document/download/{document_id}",
    }

    return {
        "document_id": document_id,
        "document": doc_header,
        "revisions": revisions_ordered,
        "oldest_baseline": oldest_baseline,
        "action_urls": {
            "open_oldest_version_url": oldest_item["download_url"],
            "open_current_version_url": f"/dms-document/download/{document_id}",
        },
    }


def get_dms_revision_file(
    db: Session, history_id: int, user_id: Optional[int] = None
) -> dict:
    """Fetch revision history file metadata and verify access permissions."""
    row = (
        db.execute(
            text(
                """
            SELECT h.history_id, h.document_id, h.file_path, h.file_name, h.file_type,
                   d.confidential_document, d.security_classification, d.created_by, d.custodian_id,
                   d.individual_engineer, d.custody_list
            FROM dms_documents_history h
            LEFT JOIN dms_documents d ON d.document_id = h.document_id
            WHERE h.history_id = :hid
        """
            ),
            {"hid": history_id},
        )
        .mappings()
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Revision history record not found")

    row_dict = dict(row)
    if not _check_confidential_access(db, user_id, row_dict):
        raise HTTPException(
            status_code=403, detail="Permission denied to access this document revision"
        )

    if not check_document_file_access(db, user_id, row_dict):
        raise HTTPException(
            status_code=403,
            detail="Access required: You do not have permission to open or download this revision. Please request access.",
        )

    file_path = row.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="No file attached to this revision")

    norm_path = os.path.abspath(file_path)
    upload_dir = get_dms_upload_dir()

    if os.path.commonpath([norm_path, upload_dir]) != upload_dir or not os.path.exists(
        norm_path
    ):
        raise HTTPException(
            status_code=404, detail="Revision file not found on storage"
        )

    return {
        "file_path": norm_path,
        "file_name": row.get("file_name") or os.path.basename(norm_path),
        "media_type": row.get("file_type") or "application/octet-stream",
    }
