import logging
from datetime import datetime
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import text, bindparam

from app.schemas.dms.dms_sub_folder_schema import DmsSubFolderCreate, DmsSubFolderUpdate
from app.crud.dms.dms_auth import get_user_dms_folder_access, NotFoundError
from app.utils.time_utils import to_iso_ist, IST

logger = logging.getLogger(__name__)


class SubFolderNotFoundException(NotFoundError, HTTPException):
    def __init__(self, detail: str = "Sub folder not found"):
        super().__init__(status_code=404, detail=detail)


def _format_sub_folder_row(row):
    """Format row datetime fields to ISO IST strings."""
    if not row:
        return None
    r = dict(row)
    if r.get("created_at"):
        r["created_at"] = to_iso_ist(r["created_at"])
    if r.get("updated_at"):
        r["updated_at"] = to_iso_ist(r["updated_at"])
    return r


SUB_FOLDER_BASE_SELECT = """
    SELECT
        sf.sub_folder_id,
        sf.folder_id,
        f.folder_name,
        sf.parent_sub_folder_id,
        psf.sub_folder_name AS parent_sub_folder_name,
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
    LEFT JOIN dms_folders f ON f.folder_id = sf.folder_id
    LEFT JOIN dms_sub_folders psf ON psf.sub_folder_id = sf.parent_sub_folder_id
    LEFT JOIN users uc ON uc.id = sf.created_by
    LEFT JOIN users uu ON uu.id = sf.updated_by
"""


def _enrich_sub_folders_with_children(db: Session, sub_folders: list, depth: int = 0) -> list:
    """Recursively enrich each sub-folder with all nested descendant sub-folders (unlimited depth)."""
    if not sub_folders or depth > 50:  # guard against infinite loops
        return sub_folders
    sf_ids = [sf["sub_folder_id"] for sf in sub_folders if sf and sf.get("sub_folder_id")]
    if not sf_ids:
        for sf in sub_folders:
            if sf:
                sf["sub_sub_folders"] = []
                sf["children"] = []
        return sub_folders

    child_query = text(
        f"""
        {SUB_FOLDER_BASE_SELECT}
        WHERE sf.parent_sub_folder_id IN :sf_ids AND sf.is_deleted = FALSE
        ORDER BY sf.sub_folder_id ASC
    """
    ).bindparams(bindparam("sf_ids", expanding=True))

    child_rows = db.execute(child_query, {"sf_ids": sf_ids}).mappings().all()
    children_by_parent = {}
    child_list = []
    for cr in child_rows:
        formatted = _format_sub_folder_row(cr)
        # Compatibility aliases for frontend
        formatted["sub_sub_folder_id"] = formatted["sub_folder_id"]
        formatted["sub_sub_folder_name"] = formatted["sub_folder_name"]
        formatted["sub_sub_folders"] = []
        formatted["children"] = []
        pid = formatted.get("parent_sub_folder_id")
        children_by_parent.setdefault(pid, []).append(formatted)
        child_list.append(formatted)

    # Recursively enrich children at next depth level
    if child_list:
        child_list = _enrich_sub_folders_with_children(db, child_list, depth=depth + 1)
        # Re-build parent map after recursive enrichment
        children_by_parent = {}
        for cf in child_list:
            pid = cf.get("parent_sub_folder_id")
            children_by_parent.setdefault(pid, []).append(cf)

    for sf in sub_folders:
        if sf:
            kids = children_by_parent.get(sf.get("sub_folder_id"), [])
            sf["sub_sub_folders"] = kids
            sf["children"] = kids

    return sub_folders


def _get_all_descendant_sf_ids(db: Session, sub_folder_id: int) -> list:
    """Return all descendant sub_folder_ids for a given sub_folder_id (recursive BFS)."""
    visited = []
    queue = [sub_folder_id]
    seen = {sub_folder_id}
    while queue:
        current_batch = queue[:]
        queue = []
        rows = db.execute(
            text(
                "SELECT sub_folder_id FROM dms_sub_folders WHERE parent_sub_folder_id IN :pids AND is_deleted = FALSE"
            ).bindparams(bindparam("pids", expanding=True)),
            {"pids": current_batch},
        ).fetchall()
        for r in rows:
            cid = r[0]
            if cid not in seen:
                seen.add(cid)
                visited.append(cid)
                queue.append(cid)
    return visited


def get_dms_sub_folder_move_preview(
    db: Session,
    sub_folder_id: int,
    destination_folder_id: int,
    parent_sub_folder_id: Optional[int] = None,
) -> dict:
    """
    Validate and get preview details for moving a sub-folder to any destination in the hierarchy.
    - destination_folder_id: Primary (root) folder target.
    - parent_sub_folder_id: Optional destination parent sub-folder. None = move to root of primary folder.
    """
    if parent_sub_folder_id is not None and parent_sub_folder_id <= 0:
        parent_sub_folder_id = None

    # 1. Fetch source sub-folder
    sf_query = text(
        """
        SELECT
            sf.sub_folder_id,
            sf.sub_folder_name,
            sf.folder_id,
            sf.parent_sub_folder_id AS source_parent_sub_folder_id,
            psf.sub_folder_name AS source_parent_sub_folder_name,
            f.folder_name AS source_folder_name
        FROM dms_sub_folders sf
        LEFT JOIN dms_folders f ON f.folder_id = sf.folder_id
        LEFT JOIN dms_sub_folders psf ON psf.sub_folder_id = sf.parent_sub_folder_id
        WHERE sf.sub_folder_id = :sub_folder_id AND sf.is_deleted = FALSE
    """
    )
    sf = db.execute(sf_query, {"sub_folder_id": sub_folder_id}).mappings().first()
    if not sf:
        raise SubFolderNotFoundException("Sub folder not found or has been deleted")

    # 2. Prevent moving a subfolder into itself
    if sub_folder_id == parent_sub_folder_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot move a sub-folder into itself.",
        )

    # 3. Fetch destination primary folder
    dest_query = text(
        """
        SELECT folder_id, folder_name
        FROM dms_folders
        WHERE folder_id = :destination_folder_id AND is_deleted = FALSE
    """
    )
    dest = (
        db.execute(dest_query, {"destination_folder_id": destination_folder_id})
        .mappings()
        .first()
    )
    if not dest:
        raise HTTPException(
            status_code=400,
            detail="Invalid destination folder: Folder does not exist or has been deleted",
        )

    # 4. Validate destination parent subfolder if provided
    dest_parent_sf_name = None
    if parent_sub_folder_id is not None:
        dest_parent_sf = db.execute(
            text(
                """
                SELECT sub_folder_id, sub_folder_name, folder_id
                FROM dms_sub_folders
                WHERE sub_folder_id = :psf_id AND is_deleted = FALSE
                """
            ),
            {"psf_id": parent_sub_folder_id},
        ).mappings().first()
        if not dest_parent_sf:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid parent_sub_folder_id {parent_sub_folder_id}: Destination parent sub-folder does not exist or has been deleted.",
            )
        if dest_parent_sf["folder_id"] != destination_folder_id:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid parent_sub_folder_id {parent_sub_folder_id}: Destination parent sub-folder belongs to folder {dest_parent_sf['folder_id']}, not the specified destination folder {destination_folder_id}.",
            )
        dest_parent_sf_name = dest_parent_sf["sub_folder_name"]

        # 5. Prevent moving into any of its own descendants (cycle check)
        descendant_ids = _get_all_descendant_sf_ids(db, sub_folder_id)
        if parent_sub_folder_id in descendant_ids:
            raise HTTPException(
                status_code=400,
                detail="Cannot move a sub-folder into one of its own descendants. This would create a circular hierarchy.",
            )

    # 6. Check if destination is same as current location (no-op guard)
    same_folder = sf["folder_id"] == destination_folder_id
    same_parent = sf["source_parent_sub_folder_id"] == parent_sub_folder_id
    if same_folder and same_parent:
        raise HTTPException(
            status_code=400,
            detail=f"Sub-folder '{sf['sub_folder_name']}' is already at the specified destination.",
        )

    # 7. Check for name collision in destination parent scope
    if parent_sub_folder_id is not None:
        name_check = db.execute(
            text(
                """
            SELECT sub_folder_id FROM dms_sub_folders
            WHERE parent_sub_folder_id = :parent_sub_folder_id
              AND LOWER(TRIM(sub_folder_name)) = LOWER(TRIM(:sub_folder_name))
              AND is_deleted = FALSE
              AND sub_folder_id != :sub_folder_id
        """
            ),
            {
                "parent_sub_folder_id": parent_sub_folder_id,
                "sub_folder_name": sf["sub_folder_name"],
                "sub_folder_id": sub_folder_id,
            },
        ).first()
    else:
        name_check = db.execute(
            text(
                """
            SELECT sub_folder_id FROM dms_sub_folders
            WHERE folder_id = :destination_folder_id
              AND parent_sub_folder_id IS NULL
              AND LOWER(TRIM(sub_folder_name)) = LOWER(TRIM(:sub_folder_name))
              AND is_deleted = FALSE
              AND sub_folder_id != :sub_folder_id
        """
            ),
            {
                "destination_folder_id": destination_folder_id,
                "sub_folder_name": sf["sub_folder_name"],
                "sub_folder_id": sub_folder_id,
            },
        ).first()
    if name_check:
        dest_label = f"sub-folder '{dest_parent_sf_name}'" if dest_parent_sf_name else f"folder '{dest['folder_name']}'"
        raise HTTPException(
            status_code=400,
            detail=f"A sub-folder named '{sf['sub_folder_name']}' already exists in destination {dest_label}.",
        )

    # 8. Count affected direct documents
    affected_doc_count = (
        db.execute(
            text(
                "SELECT COUNT(1) FROM dms_documents WHERE sub_folder_id = :sub_folder_id AND is_deleted = FALSE"
            ),
            {"sub_folder_id": sub_folder_id},
        ).scalar()
        or 0
    )

    # 9. Count all descendant sub-folders
    descendant_ids = _get_all_descendant_sf_ids(db, sub_folder_id)
    affected_descendants = len(descendant_ids)

    return {
        "sub_folder_id": sf["sub_folder_id"],
        "sub_folder_name": sf["sub_folder_name"],
        "source_folder_id": sf["folder_id"],
        "source_folder_name": sf["source_folder_name"] or "",
        "source_parent_sub_folder_id": sf["source_parent_sub_folder_id"],
        "source_parent_sub_folder_name": sf["source_parent_sub_folder_name"],
        "destination_folder_id": dest["folder_id"],
        "destination_folder_name": dest["folder_name"] or "",
        "destination_parent_sub_folder_id": parent_sub_folder_id,
        "destination_parent_sub_folder_name": dest_parent_sf_name,
        "affected_documents_count": affected_doc_count,
        "affected_descendants_count": affected_descendants,
    }


# ==============================================================================
# MAIN CRUD OPERATIONS
# ==============================================================================


# -------------------------------------------------
# 1. CREATE SUB-FOLDER
# -------------------------------------------------
def create_dms_sub_folder(db: Session, data: DmsSubFolderCreate):
    """Create sub-folder in master table and log snapshot in history."""
    payload = data.model_dump()

    parent_sub_folder_id = payload.get("parent_sub_folder_id")
    if parent_sub_folder_id is not None and parent_sub_folder_id <= 0:
        parent_sub_folder_id = None
        payload["parent_sub_folder_id"] = None

    folder_id = payload.get("folder_id")
    if folder_id is not None and folder_id <= 0:
        folder_id = None
        payload["folder_id"] = None

    # If parent_sub_folder_id is provided, validate parent sub-folder and inherit/verify folder_id
    if parent_sub_folder_id:
        parent_sf = db.execute(
            text(
                """
                SELECT sub_folder_id, folder_id, sub_folder_name 
                FROM dms_sub_folders 
                WHERE sub_folder_id = :psf_id AND is_deleted = FALSE
                """
            ),
            {"psf_id": parent_sub_folder_id},
        ).mappings().first()
        if not parent_sf:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid parent_sub_folder_id {parent_sub_folder_id}: Parent sub-folder does not exist or has been deleted.",
            )
        if not folder_id:
            folder_id = parent_sf["folder_id"]
            payload["folder_id"] = folder_id
        elif folder_id != parent_sf["folder_id"]:
            raise HTTPException(
                status_code=400,
                detail=f"Mismatched folder_id: Parent sub-folder belongs to folder {parent_sf['folder_id']}, but received folder {folder_id}.",
            )

    if not folder_id:
        raise HTTPException(
            status_code=400,
            detail="folder_id or parent_sub_folder_id must be provided to create a sub-folder.",
        )

    # Validate that parent folder exists and is active
    folder = db.execute(
        text(
            "SELECT folder_id FROM dms_folders WHERE folder_id = :folder_id AND is_deleted = FALSE"
        ),
        {"folder_id": folder_id},
    ).first()
    if not folder:
        raise HTTPException(
            status_code=400,
            detail="Invalid folder_id: Parent folder does not exist or has been deleted.",
        )

    # Validate unique sub_folder_name (case-insensitive & trimmed) in its parent scope
    sub_folder_name = payload.get("sub_folder_name")
    if sub_folder_name and str(sub_folder_name).strip():
        clean_sf_name = str(sub_folder_name).strip()
        if parent_sub_folder_id:
            existing = db.execute(
                text("""
                    SELECT sub_folder_id FROM dms_sub_folders
                    WHERE parent_sub_folder_id = :parent_sub_folder_id
                      AND LOWER(TRIM(sub_folder_name)) = LOWER(TRIM(:sub_folder_name))
                      AND is_deleted = FALSE
                    LIMIT 1
                """),
                {"parent_sub_folder_id": parent_sub_folder_id, "sub_folder_name": clean_sf_name}
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sub-folder name '{clean_sf_name}' already exists in this parent sub-folder"
                )
        else:
            existing = db.execute(
                text("""
                    SELECT sub_folder_id FROM dms_sub_folders
                    WHERE folder_id = :folder_id
                      AND parent_sub_folder_id IS NULL
                      AND LOWER(TRIM(sub_folder_name)) = LOWER(TRIM(:sub_folder_name))
                      AND is_deleted = FALSE
                    LIMIT 1
                """),
                {"folder_id": folder_id, "sub_folder_name": clean_sf_name}
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sub-folder name '{clean_sf_name}' already exists in this folder"
                )
        payload["sub_folder_name"] = clean_sf_name

    payload["parent_sub_folder_id"] = parent_sub_folder_id

    insert_master = text(
        """
        INSERT INTO dms_sub_folders (
            folder_id,
            parent_sub_folder_id,
            sub_folder_code,
            sub_folder_name,
            sub_folder_description,
            status,
            is_deleted,
            created_by
        )
        VALUES (
            :folder_id,
            :parent_sub_folder_id,
            :sub_folder_code,
            :sub_folder_name,
            :sub_folder_description,
            :status,
            FALSE,
            :created_by
        )
        RETURNING sub_folder_id
    """
    )

    insert_history = text(
        """
        INSERT INTO dms_sub_folders_history (
            sub_folder_id,
            folder_id,
            parent_sub_folder_id,
            sub_folder_code,
            sub_folder_name,
            sub_folder_description,
            status,
            is_deleted,
            created_by,
            created_at
        )
        SELECT
            sub_folder_id,
            folder_id,
            parent_sub_folder_id,
            sub_folder_code,
            sub_folder_name,
            sub_folder_description,
            status,
            is_deleted,
            created_by,
            created_at
        FROM dms_sub_folders
        WHERE sub_folder_id = :sub_folder_id
    """
    )

    try:
        sub_folder_id = db.execute(insert_master, payload).scalar()
        db.execute(insert_history, {"sub_folder_id": sub_folder_id})
        db.commit()
        return sub_folder_id
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create DMS sub folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create DMS sub folder")


# -------------------------------------------------
# 2. UPDATE SUB-FOLDER
# -------------------------------------------------
def update_dms_sub_folder(db: Session, sub_folder_id: int, data: DmsSubFolderUpdate):
    """Update sub-folder attributes and record snapshot in history."""
    check_query = text(
        """
        SELECT sub_folder_id, folder_id, parent_sub_folder_id, sub_folder_code, sub_folder_name
        FROM dms_sub_folders
        WHERE sub_folder_id = :sub_folder_id AND is_deleted = FALSE
    """
    )
    current_sf = (
        db.execute(check_query, {"sub_folder_id": sub_folder_id}).mappings().first()
    )
    if not current_sf:
        raise SubFolderNotFoundException("Sub folder not found")

    payload = data.model_dump(exclude_unset=True)

    # Never allow updating creation audit fields on PUT calls
    payload.pop("created_at", None)
    payload.pop("created_by", None)

    if not payload:
        return 0

    # Validate parent_sub_folder_id if updated
    if "parent_sub_folder_id" in payload:
        if payload["parent_sub_folder_id"] is not None and payload["parent_sub_folder_id"] <= 0:
            payload["parent_sub_folder_id"] = None
        new_parent_id = payload["parent_sub_folder_id"]
        if new_parent_id is not None:
            if new_parent_id == sub_folder_id:
                raise HTTPException(
                    status_code=400,
                    detail="A sub-folder cannot be its own parent.",
                )
            parent_sf = db.execute(
                text(
                    "SELECT sub_folder_id, folder_id FROM dms_sub_folders WHERE sub_folder_id = :psf_id AND is_deleted = FALSE"
                ),
                {"psf_id": new_parent_id},
            ).mappings().first()
            if not parent_sf:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid parent_sub_folder_id {new_parent_id}: Parent sub-folder does not exist or has been deleted.",
                )
            # Cycle prevention: walk up the ancestor chain
            curr_pid = new_parent_id
            while curr_pid:
                if curr_pid == sub_folder_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Circular reference: cannot set parent to a descendant sub-folder.",
                    )
                ancestor = db.execute(
                    text("SELECT parent_sub_folder_id FROM dms_sub_folders WHERE sub_folder_id = :pid AND is_deleted = FALSE"),
                    {"pid": curr_pid}
                ).first()
                curr_pid = ancestor[0] if ancestor else None

            # Inherit folder_id from new parent if folder_id wasn't explicitly changed
            if "folder_id" not in payload:
                payload["folder_id"] = parent_sf["folder_id"]

    # Validate parent folder if folder_id is updated
    if "folder_id" in payload and payload["folder_id"] is not None:
        folder = db.execute(
            text(
                "SELECT folder_id FROM dms_folders WHERE folder_id = :folder_id AND is_deleted = FALSE"
            ),
            {"folder_id": payload["folder_id"]},
        ).first()
        if not folder:
            raise HTTPException(
                status_code=400,
                detail="Invalid folder_id: Parent folder does not exist or has been deleted.",
            )

    # Validate unique sub_folder_name in parent scope
    target_folder_id = payload.get("folder_id") if "folder_id" in payload and payload["folder_id"] is not None else current_sf["folder_id"]
    target_parent_sf_id = payload.get("parent_sub_folder_id") if "parent_sub_folder_id" in payload else current_sf.get("parent_sub_folder_id")

    sf_name_to_check = payload.get("sub_folder_name")
    if sf_name_to_check is not None:
        clean_sf_name = str(sf_name_to_check).strip()
    elif "folder_id" in payload or "parent_sub_folder_id" in payload:
        clean_sf_name = str(current_sf.get("sub_folder_name") or "").strip()
    else:
        clean_sf_name = None

    if clean_sf_name:
        if target_parent_sf_id:
            existing = db.execute(
                text("""
                    SELECT sub_folder_id FROM dms_sub_folders
                    WHERE parent_sub_folder_id = :parent_sub_folder_id
                      AND LOWER(TRIM(sub_folder_name)) = LOWER(TRIM(:sub_folder_name))
                      AND sub_folder_id != :sub_folder_id
                      AND is_deleted = FALSE
                    LIMIT 1
                """),
                {
                    "parent_sub_folder_id": target_parent_sf_id,
                    "sub_folder_name": clean_sf_name,
                    "sub_folder_id": sub_folder_id,
                }
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sub-folder name '{clean_sf_name}' already exists in this parent sub-folder"
                )
        else:
            existing = db.execute(
                text("""
                    SELECT sub_folder_id FROM dms_sub_folders
                    WHERE folder_id = :folder_id
                      AND parent_sub_folder_id IS NULL
                      AND LOWER(TRIM(sub_folder_name)) = LOWER(TRIM(:sub_folder_name))
                      AND sub_folder_id != :sub_folder_id
                      AND is_deleted = FALSE
                    LIMIT 1
                """),
                {
                    "folder_id": target_folder_id,
                    "sub_folder_name": clean_sf_name,
                    "sub_folder_id": sub_folder_id,
                }
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sub-folder name '{clean_sf_name}' already exists in this folder"
                )
        if "sub_folder_name" in payload:
            payload["sub_folder_name"] = clean_sf_name

    payload["sub_folder_id"] = sub_folder_id

    # Dynamic SET clauses
    set_clauses = []
    field_map = {
        "folder_id": "folder_id",
        "parent_sub_folder_id": "parent_sub_folder_id",
        "sub_folder_code": "sub_folder_code",
        "sub_folder_name": "sub_folder_name",
        "sub_folder_description": "sub_folder_description",
        "status": "status",
        "updated_by": "updated_by",
    }

    for key, col in field_map.items():
        if key in payload:
            set_clauses.append(f"{col} = :{key}")

    if not set_clauses:
        return 0

    set_clauses.append("updated_at = NOW()")

    update_sql = f"""
        UPDATE dms_sub_folders
        SET {', '.join(set_clauses)}
        WHERE sub_folder_id = :sub_folder_id AND is_deleted = FALSE
    """

    history_query = text(
        """
        INSERT INTO dms_sub_folders_history (
            sub_folder_id,
            folder_id,
            parent_sub_folder_id,
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
            parent_sub_folder_id,
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
        WHERE sub_folder_id = :sub_folder_id
    """
    )

    try:
        result = db.execute(text(update_sql), payload)
        if result.rowcount == 0:
            raise SubFolderNotFoundException("Sub folder not found")
        db.execute(history_query, {"sub_folder_id": sub_folder_id})
        db.commit()
        return result.rowcount
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update DMS sub folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update DMS sub folder")


# -------------------------------------------------
# 3. GET SUB-FOLDER BY ID
# -------------------------------------------------
def get_dms_sub_folder(db: Session, sub_folder_id: int, user_id: Optional[int] = None):
    """Retrieve sub-folder details with creator/updater names, child sub-folders, and access validation."""
    # if user_id:
    #     is_unrestricted, allowed_folders, allowed_subfolders = get_user_dms_folder_access(db, user_id)
    #     if not is_unrestricted and allowed_subfolders is not None and sub_folder_id not in allowed_subfolders:
    #         return None

    query = text(
        f"""
        {SUB_FOLDER_BASE_SELECT}
        WHERE sf.sub_folder_id = :sub_folder_id AND sf.is_deleted = FALSE
    """
    )

    result = db.execute(query, {"sub_folder_id": sub_folder_id}).mappings().first()
    if not result:
        return None
    row_dict = _format_sub_folder_row(result)
    enriched = _enrich_sub_folders_with_children(db, [row_dict])
    return enriched[0] if enriched else row_dict


# -------------------------------------------------
# 4. GET ALL SUB-FOLDERS
# -------------------------------------------------
def get_all_dms_sub_folders(db: Session, user_id: Optional[int] = None):
    """Retrieve all non-deleted sub-folders with user access filtering and children enrichment."""
    where_clauses = ["sf.is_deleted = FALSE"]
    params = {}
    # if user_id:
    #     is_unrestricted, allowed_folders, allowed_subfolders = get_user_dms_folder_access(db, user_id)
    #     if not is_unrestricted:
    #         if not allowed_subfolders:
    #             return []
    #         where_clauses.append("sf.sub_folder_id IN :allowed_sf_ids")
    #         params["allowed_sf_ids"] = list(allowed_subfolders)

    where_sql = " AND ".join(where_clauses)
    query = text(
        f"""
        {SUB_FOLDER_BASE_SELECT}
        WHERE {where_sql}
        ORDER BY sf.sub_folder_id DESC
    """
    )
    if "allowed_sf_ids" in params:
        query = query.bindparams(bindparam("allowed_sf_ids", expanding=True))

    result = db.execute(query, params).mappings().all()
    formatted_list = [_format_sub_folder_row(r) for r in result]
    return _enrich_sub_folders_with_children(db, formatted_list)


# -------------------------------------------------
# 5. GET SUB-FOLDERS BY FOLDER ID
# -------------------------------------------------
def get_dms_sub_folders_by_folder(
    db: Session,
    folder_id: int,
    parent_sub_folder_id: Optional[int] = None,
    user_id: Optional[int] = None,
    flat: bool = False,
):
    """Retrieve sub-folders for a specific parent folder with hierarchical or flat filtering."""
    where_clauses = ["sf.folder_id = :folder_id", "sf.is_deleted = FALSE"]
    params = {"folder_id": folder_id}

    if parent_sub_folder_id is not None:
        where_clauses.append("sf.parent_sub_folder_id = :parent_sub_folder_id")
        params["parent_sub_folder_id"] = parent_sub_folder_id
    elif not flat:
        # Default hierarchical view: return top-level subfolders (Level 2), with their sub_sub_folders attached
        where_clauses.append("sf.parent_sub_folder_id IS NULL")

    # if user_id:
    #     is_unrestricted, allowed_folders, allowed_subfolders = get_user_dms_folder_access(db, user_id)
    #     if not is_unrestricted:
    #         if allowed_folders is not None and folder_id not in allowed_folders:
    #             return []
    #         if allowed_subfolders is not None:
    #             if not allowed_subfolders:
    #                 return []
    #             where_clauses.append("sf.sub_folder_id IN :allowed_sf_ids")
    #             params["allowed_sf_ids"] = list(allowed_subfolders)

    where_sql = " AND ".join(where_clauses)
    query = text(
        f"""
        {SUB_FOLDER_BASE_SELECT}
        WHERE {where_sql}
        ORDER BY sf.sub_folder_id ASC
    """
    )
    if "allowed_sf_ids" in params:
        query = query.bindparams(bindparam("allowed_sf_ids", expanding=True))

    result = db.execute(query, params).mappings().all()
    formatted_list = [_format_sub_folder_row(r) for r in result]
    return _enrich_sub_folders_with_children(db, formatted_list)


# -------------------------------------------------
# 6. MOVE SUB-FOLDER (+ CASCADE DOCUMENTS & HISTORY)
# -------------------------------------------------
def move_dms_sub_folder(
    db: Session,
    sub_folder_id: int,
    destination_folder_id: int,
    parent_sub_folder_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> dict:
    """
    Move a sub-folder to any destination in the hierarchy.
    - destination_folder_id: The primary folder ID of the destination.
    - parent_sub_folder_id: Optional; the destination parent sub-folder at any nesting depth.
      None = move to root of primary folder.
    Cascades folder_id and sub_folder_id updates to ALL descendant sub-folders and their documents.
    """
    if parent_sub_folder_id is not None and parent_sub_folder_id <= 0:
        parent_sub_folder_id = None
    preview = get_dms_sub_folder_move_preview(
        db, sub_folder_id, destination_folder_id, parent_sub_folder_id=parent_sub_folder_id
    )

    try:
        # 1. Collect all descendant sub-folder IDs before moving
        descendant_ids = _get_all_descendant_sf_ids(db, sub_folder_id)
        all_sf_ids = [sub_folder_id] + descendant_ids  # root + all descendants

        # 2. Update the moved sub-folder's folder_id and parent_sub_folder_id
        db.execute(
            text(
                """
            UPDATE dms_sub_folders
            SET
                folder_id = :destination_folder_id,
                parent_sub_folder_id = :parent_sub_folder_id,
                updated_by = :user_id,
                updated_at = NOW()
            WHERE sub_folder_id = :sub_folder_id AND is_deleted = FALSE
        """
            ),
            {
                "destination_folder_id": destination_folder_id,
                "parent_sub_folder_id": parent_sub_folder_id,
                "user_id": user_id,
                "sub_folder_id": sub_folder_id,
            },
        )

        # 3. Cascade folder_id update to all descendant sub-folders
        if descendant_ids:
            db.execute(
                text(
                    """
                UPDATE dms_sub_folders
                SET
                    folder_id = :destination_folder_id,
                    updated_by = :user_id,
                    updated_at = NOW()
                WHERE sub_folder_id IN :desc_ids AND is_deleted = FALSE
            """
                ).bindparams(bindparam("desc_ids", expanding=True)),
                {
                    "destination_folder_id": destination_folder_id,
                    "user_id": user_id,
                    "desc_ids": descendant_ids,
                },
            )

        # 4. Insert history snapshot for the moved sub-folder and all descendants
        db.execute(
            text(
                """
            INSERT INTO dms_sub_folders_history (
                sub_folder_id,
                folder_id,
                parent_sub_folder_id,
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
                parent_sub_folder_id,
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
            WHERE sub_folder_id IN :all_sf_ids
        """
            ).bindparams(bindparam("all_sf_ids", expanding=True)),
            {"all_sf_ids": all_sf_ids},
        )

        # 5. Cascade folder_id update to ALL documents under moved sub-folder AND its descendants
        db.execute(
            text(
                """
            INSERT INTO dms_documents_history (
                document_id, document_number, document_title, document_subject,
                target_folder, folder_id, sub_folder_id, sub_sub_folder_id,
                department, location, station_id, category, document_type,
                custodian_id, custodian_name, open_date, close_date, volume,
                security_classification, retention_class, confidential_document,
                status, revision, revision_number, revision_note,
                physical_rack, physical_shelf, physical_box,
                custody_list, individual_engineer, file_path, file_name,
                file_size, file_type, description, tags, is_deleted,
                created_by, created_at, updated_by, updated_at
            )
            SELECT
                document_id, document_number, document_title, document_subject,
                target_folder, folder_id, sub_folder_id, sub_sub_folder_id,
                department, location, station_id, category, document_type,
                custodian_id, custodian_name, open_date, close_date, volume,
                security_classification, retention_class, confidential_document,
                status, revision, revision_number, revision_note,
                physical_rack, physical_shelf, physical_box,
                custody_list, individual_engineer, file_path, file_name,
                file_size, file_type, description, tags, is_deleted,
                created_by, created_at, updated_by, updated_at
            FROM dms_documents
            WHERE sub_folder_id IN :all_sf_ids AND is_deleted = FALSE
        """
            ).bindparams(bindparam("all_sf_ids", expanding=True)),
            {"all_sf_ids": all_sf_ids},
        )

        db.execute(
            text(
                """
            UPDATE dms_documents
            SET
                folder_id = :destination_folder_id,
                target_folder = :destination_folder_name,
                updated_by = :user_id,
                updated_at = NOW()
            WHERE sub_folder_id IN :all_sf_ids AND is_deleted = FALSE
        """
            ).bindparams(bindparam("all_sf_ids", expanding=True)),
            {
                "destination_folder_id": destination_folder_id,
                "destination_folder_name": preview["destination_folder_name"],
                "user_id": user_id,
                "all_sf_ids": all_sf_ids,
            },
        )

        db.commit()
        return preview
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to move DMS sub folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to move DMS sub folder")


# -------------------------------------------------
# 7. SOFT DELETE SUB-FOLDER
# -------------------------------------------------
def soft_delete_dms_sub_folder(
    db: Session, sub_folder_id: int, deleted_by: int = None, cascade: bool = False
):
    """Soft delete sub-folder and optionally cascade soft-delete to contained documents."""
    check_query = text(
        """
        SELECT sub_folder_id FROM dms_sub_folders
        WHERE sub_folder_id = :sub_folder_id AND is_deleted = FALSE
    """
    )
    sf = db.execute(check_query, {"sub_folder_id": sub_folder_id}).first()
    if not sf:
        raise SubFolderNotFoundException("Sub folder not found or already deleted")

    # Cascade or block deletion when documents exist
    doc_count = (
        db.execute(
            text(
                "SELECT COUNT(1) FROM dms_documents WHERE sub_folder_id = :sub_folder_id AND is_deleted = FALSE"
            ),
            {"sub_folder_id": sub_folder_id},
        ).scalar()
        or 0
    )

    if doc_count > 0:
        if not cascade:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete sub-folder: {doc_count} active document(s) exist. Please delete documents first or specify cascade.",
            )
        # Cascade soft-delete child documents
        db.execute(
            text(
                """
            UPDATE dms_documents
            SET
                is_deleted = TRUE,
                status = 'DELETED',
                updated_by = :deleted_by,
                updated_at = NOW()
            WHERE sub_folder_id = :sub_folder_id AND is_deleted = FALSE
        """
            ),
            {"sub_folder_id": sub_folder_id, "deleted_by": deleted_by},
        )

        db.execute(
            text(
                """
            INSERT INTO dms_documents_history (
                document_id, document_number, document_title, document_subject,
                target_folder, folder_id, sub_folder_id, sub_sub_folder_id,
                department, location, station_id, category, document_type,
                custodian_id, custodian_name, open_date, close_date, volume,
                security_classification, retention_class, confidential_document,
                status, revision, revision_number, revision_note,
                physical_rack, physical_shelf, physical_box,
                custody_list, individual_engineer, file_path, file_name,
                file_size, file_type, description, tags, is_deleted,
                created_by, created_at, updated_by, updated_at
            )
            SELECT
                document_id, document_number, document_title, document_subject,
                target_folder, folder_id, sub_folder_id, sub_sub_folder_id,
                department, location, station_id, category, document_type,
                custodian_id, custodian_name, open_date, close_date, volume,
                security_classification, retention_class, confidential_document,
                status, revision, revision_number, revision_note,
                physical_rack, physical_shelf, physical_box,
                custody_list, individual_engineer, file_path, file_name,
                file_size, file_type, description, tags, is_deleted,
                created_by, created_at, updated_by, updated_at
            FROM dms_documents
            WHERE sub_folder_id = :sub_folder_id
        """
            ),
            {"sub_folder_id": sub_folder_id},
        )

    update_query = text(
        """
        UPDATE dms_sub_folders
        SET
            is_deleted = TRUE,
            status = 'DELETED',
            updated_by = :deleted_by,
            updated_at = NOW()
        WHERE (sub_folder_id = :sub_folder_id OR (:cascade = TRUE AND parent_sub_folder_id = :sub_folder_id)) 
          AND is_deleted = FALSE
    """
    )

    history_query = text(
        """
        INSERT INTO dms_sub_folders_history (
            sub_folder_id,
            folder_id,
            parent_sub_folder_id,
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
            parent_sub_folder_id,
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
        WHERE sub_folder_id = :sub_folder_id OR (:cascade = TRUE AND parent_sub_folder_id = :sub_folder_id)
    """
    )

    try:
        result = db.execute(
            update_query, {"sub_folder_id": sub_folder_id, "deleted_by": deleted_by, "cascade": cascade}
        )
        if result.rowcount == 0:
            raise SubFolderNotFoundException("Sub folder not found or already deleted")
        db.execute(history_query, {"sub_folder_id": sub_folder_id, "cascade": cascade})
        db.commit()
        return result.rowcount
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete DMS sub folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete DMS sub folder")


# -------------------------------------------------
# 8. UPDATE SUB-FOLDER STATUS
# -------------------------------------------------
def update_dms_sub_folder_status(
    db: Session,
    sub_folder_id: int,
    status: str,
    updated_by: Optional[int] = None,
):
    """Update active/inactive status of sub-folder and log snapshot to history."""
    update_query = text(
        """
        UPDATE dms_sub_folders
        SET
            status = :status,
            updated_by = :updated_by,
            updated_at = NOW()
        WHERE sub_folder_id = :sub_folder_id AND is_deleted = FALSE
    """
    )

    history_query = text(
        """
        INSERT INTO dms_sub_folders_history (
            sub_folder_id,
            folder_id,
            parent_sub_folder_id,
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
            parent_sub_folder_id,
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
        WHERE sub_folder_id = :sub_folder_id
    """
    )

    try:
        result = db.execute(
            update_query,
            {
                "sub_folder_id": sub_folder_id,
                "status": status,
                "updated_by": updated_by,
            },
        )
        if result.rowcount == 0:
            raise SubFolderNotFoundException("Sub folder not found or already deleted")
        db.execute(history_query, {"sub_folder_id": sub_folder_id})
        db.commit()
        return result.rowcount
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update DMS sub folder status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update DMS sub folder status")

