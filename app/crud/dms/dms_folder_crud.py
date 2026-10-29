import logging
from datetime import datetime
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import text, bindparam

from app.schemas.dms.dms_folder_schema import (
    DmsFolderCreate,
    DmsFolderUpdate
)
from app.crud.dms.dms_auth import get_user_dms_folder_access, NotFoundError
from app.utils.time_utils import to_iso_ist, IST

logger = logging.getLogger(__name__)


class FolderNotFoundException(NotFoundError, HTTPException):
    def __init__(self, detail: str = "Folder not found"):
        super().__init__(status_code=404, detail=detail)


def _format_folder_row(row):
    """Format row datetime fields to ISO IST strings."""
    if not row:
        return None
    r = dict(row)
    if r.get("created_at"):
        r["created_at"] = to_iso_ist(r["created_at"])
    if r.get("updated_at"):
        r["updated_at"] = to_iso_ist(r["updated_at"])
    return r


FOLDER_BASE_SELECT = """
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
"""


# ==============================================================================
# MAIN CRUD OPERATIONS
# ==============================================================================

# -------------------------------------------------
# 1. CREATE FOLDER
# -------------------------------------------------
def create_dms_folder(db: Session, data: DmsFolderCreate):
    """Create a new folder in master table and log initial snapshot in history."""
    payload = data.model_dump()

    # Validate unique folder_name (case-insensitive & trimmed) among active folders
    folder_name = payload.get("folder_name")
    if folder_name and str(folder_name).strip():
        clean_name = str(folder_name).strip()
        existing = db.execute(
            text("""
                SELECT folder_id FROM dms_folders
                WHERE LOWER(TRIM(folder_name)) = LOWER(TRIM(:folder_name))
                  AND is_deleted = FALSE
                LIMIT 1
            """),
            {"folder_name": clean_name}
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Folder name '{clean_name}' already exists"
            )
        payload["folder_name"] = clean_name

    insert_master = text("""
        INSERT INTO dms_folders (
            folder_name,
            folder_description,
            folder_icon,
            is_deleted,
            created_by
        )
        VALUES (
            :folder_name,
            :folder_description,
            :folder_icon,
            FALSE,
            :created_by
        )
        RETURNING folder_id
    """)

    insert_history = text("""
        INSERT INTO dms_folders_history (
            folder_id,
            folder_name,
            folder_description,
            folder_icon,
            is_deleted,
            created_by,
            created_at
        )
        SELECT
            folder_id,
            folder_name,
            folder_description,
            folder_icon,
            is_deleted,
            created_by,
            created_at
        FROM dms_folders
        WHERE folder_id = :folder_id
    """)

    try:
        folder_id = db.execute(insert_master, payload).scalar()
        db.execute(insert_history, {"folder_id": folder_id})
        db.commit()
        return folder_id
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create DMS folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create DMS folder")


# -------------------------------------------------
# 2. UPDATE FOLDER
# -------------------------------------------------
def update_dms_folder(db: Session, folder_id: int, data: DmsFolderUpdate):
    """Update folder attributes and record snapshot in history."""
    check_query = text("""
        SELECT folder_id FROM dms_folders
        WHERE folder_id = :folder_id AND is_deleted = FALSE
    """)
    folder = db.execute(check_query, {"folder_id": folder_id}).first()
    if not folder:
        raise FolderNotFoundException("Folder not found")

    payload = data.model_dump(exclude_unset=True)

    # Never allow updating creation audit fields on PUT calls
    payload.pop("created_at", None)
    payload.pop("created_by", None)

    if not payload:
        return 0

    # Validate unique folder_name if updated
    if "folder_name" in payload and payload["folder_name"]:
        clean_name = str(payload["folder_name"]).strip()
        existing = db.execute(
            text("""
                SELECT folder_id FROM dms_folders
                WHERE LOWER(TRIM(folder_name)) = LOWER(TRIM(:folder_name))
                  AND folder_id != :folder_id
                  AND is_deleted = FALSE
                LIMIT 1
            """),
            {"folder_name": clean_name, "folder_id": folder_id}
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Folder name '{clean_name}' already exists"
            )
        payload["folder_name"] = clean_name

    payload["folder_id"] = folder_id

    # Dynamic SET clauses
    set_clauses = []
    field_map = {
        "folder_name": "folder_name",
        "folder_description": "folder_description",
        "folder_icon": "folder_icon",
        "updated_by": "updated_by",
    }

    for key, col in field_map.items():
        if key in payload:
            set_clauses.append(f"{col} = :{key}")

    if not set_clauses:
        return 0

    set_clauses.append("updated_at = NOW()")

    update_sql = f"""
        UPDATE dms_folders
        SET {', '.join(set_clauses)}
        WHERE folder_id = :folder_id AND is_deleted = FALSE
    """

    history_query = text("""
        INSERT INTO dms_folders_history (
            folder_id,
            folder_name,
            folder_description,
            folder_icon,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        )
        SELECT
            folder_id,
            folder_name,
            folder_description,
            folder_icon,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM dms_folders
        WHERE folder_id = :folder_id
    """)

    try:
        result = db.execute(text(update_sql), payload)
        if result.rowcount == 0:
            raise FolderNotFoundException("Folder not found")
        db.execute(history_query, {"folder_id": folder_id})
        db.commit()
        return result.rowcount
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update DMS folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update DMS folder")


# -------------------------------------------------
# 3. GET FOLDER BY ID
# -------------------------------------------------
def get_dms_folder(db: Session, folder_id: int, user_id: Optional[int] = None):
    """Retrieve folder details with creator/updater names and access validation."""
    # if user_id:
    #     is_unrestricted, allowed_folders, _ = get_user_dms_folder_access(db, user_id)
    #     if not is_unrestricted and (allowed_folders is None or folder_id not in allowed_folders):
    #         return None

    query = text(f"""
        {FOLDER_BASE_SELECT}
        WHERE f.folder_id = :folder_id AND f.is_deleted = FALSE
    """)

    result = db.execute(query, {"folder_id": folder_id}).mappings().first()
    if not result:
        return None
    return _format_folder_row(result)


# -------------------------------------------------
# 4. GET ALL FOLDERS
# -------------------------------------------------
def get_all_dms_folders(db: Session, user_id: Optional[int] = None):
    """Retrieve all non-deleted folders with user folder access filtering."""
    where_clauses = ["f.is_deleted = FALSE"]
    params = {}
    # if user_id:
    #     is_unrestricted, allowed_folders, _ = get_user_dms_folder_access(db, user_id)
    #     if not is_unrestricted:
    #         if not allowed_folders:
    #             return []
    #         where_clauses.append("f.folder_id IN :allowed_folders")
    #         params["allowed_folders"] = list(allowed_folders)

    where_sql = " AND ".join(where_clauses)
    query = text(f"""
        {FOLDER_BASE_SELECT}
        WHERE {where_sql}
        ORDER BY f.folder_id DESC
    """)
    if "allowed_folders" in params:
        query = query.bindparams(bindparam("allowed_folders", expanding=True))

    result = db.execute(query, params).mappings().all()
    return [_format_folder_row(r) for r in result]


# -------------------------------------------------
# 5. SOFT DELETE FOLDER
# -------------------------------------------------
def soft_delete_dms_folder(db: Session, folder_id: int, deleted_by: int = None, cascade: bool = False):
    """Soft delete folder and optionally cascade soft-delete to contained sub-folders."""
    check_query = text("""
        SELECT folder_id FROM dms_folders
        WHERE folder_id = :folder_id AND is_deleted = FALSE
    """)
    folder = db.execute(check_query, {"folder_id": folder_id}).first()
    if not folder:
        raise FolderNotFoundException("Folder not found or already deleted")

    # Cascade or block deletion when sub-folders exist
    subfolder_count = db.execute(
        text("SELECT COUNT(1) FROM dms_sub_folders WHERE folder_id = :folder_id AND is_deleted = FALSE"),
        {"folder_id": folder_id}
    ).scalar() or 0

    if subfolder_count > 0:
        if not cascade:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete folder: {subfolder_count} active sub-folder(s) exist. Please delete sub-folders first or specify cascade."
            )
        # Cascade soft deletion of sub-folders
        db.execute(text("""
            UPDATE dms_sub_folders
            SET
                is_deleted = TRUE,
                status = 'DELETED',
                updated_by = :deleted_by,
                updated_at = NOW()
            WHERE folder_id = :folder_id AND is_deleted = FALSE
        """), {"folder_id": folder_id, "deleted_by": deleted_by})

        db.execute(text("""
            INSERT INTO dms_sub_folders_history (
                sub_folder_id,
                folder_id,
                sub_folder_code,
                sub_folder_name,
                sub_folder_description,
                status,
                is_deleted,
                created_by,
                created_at,
                updated_by,
                updated_at
            )
            SELECT
                sub_folder_id,
                folder_id,
                sub_folder_code,
                sub_folder_name,
                sub_folder_description,
                status,
                is_deleted,
                created_by,
                created_at,
                updated_by,
                updated_at
            FROM dms_sub_folders
            WHERE folder_id = :folder_id
        """), {"folder_id": folder_id})

    update_query = text("""
        UPDATE dms_folders
        SET
            is_deleted = TRUE,
            updated_by = :deleted_by,
            updated_at = NOW()
        WHERE folder_id = :folder_id AND is_deleted = FALSE
    """)

    history_query = text("""
        INSERT INTO dms_folders_history (
            folder_id,
            folder_name,
            folder_description,
            folder_icon,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        )
        SELECT
            folder_id,
            folder_name,
            folder_description,
            folder_icon,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM dms_folders
        WHERE folder_id = :folder_id
    """)

    try:
        result = db.execute(update_query, {
            "folder_id": folder_id,
            "deleted_by": deleted_by
        })
        if result.rowcount == 0:
            raise FolderNotFoundException("Folder not found or already deleted")
        db.execute(history_query, {"folder_id": folder_id})
        db.commit()
        return result.rowcount
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete DMS folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete DMS folder")
