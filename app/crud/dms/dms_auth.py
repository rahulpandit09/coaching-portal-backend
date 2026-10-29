import json
import logging
from typing import Optional, Tuple, Set
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import text, bindparam

from app.dependencies.dms_auth import get_current_user_id
from app.models.user import User

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Custom exception raised when a DMS resource is not found or already deleted."""
    pass


def is_user_dms_admin(db: Session, user_id: Optional[int]) -> bool:
    """
    Returns True if user has an Admin role (role_id = 4, 31, or 'admin' in role_name).
    """
    if not user_id:
        return False

    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        role_name = (user.role.name or "").lower() if user.role else ""
        if user.role_id in (4, 31) or "admin" in role_name:
            return True

        return False
    except Exception as e:
        logger.error(f"Error checking DMS admin status for user_id {user_id}: {e}", exc_info=True)
        return False


def verify_dms_admin(db: Session, user_id: Optional[int], action: str = "perform this action") -> bool:
    """
    Verifies that the given user_id has an Admin role.
    Raises HTTPException(400) if user_id is missing, or HTTPException(403) if not an Admin.
    """
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail=f"Admin user ID is required to {action}."
        )

    if not is_user_dms_admin(db, user_id):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: Only Admin users can {action}."
        )
    return True


def get_user_dms_folder_access(
    db: Session,
    user_id: Optional[int],
    ignore_admin: bool = False,
) -> Tuple[bool, Optional[Set[int]], Optional[Set[int]]]:
    """
    Determines folder and subfolder access for a given user.
    Returns:
        (is_unrestricted: bool, allowed_folder_ids: Optional[Set[int]], allowed_subfolder_ids: Optional[Set[int]])

    - If user_id is None -> raises 401 Unauthorized
    - If user is Admin (and not ignore_admin) -> (True, None, None) (Admin sees all folders and subfolders)
    - If user is Publisher -> returns allowed folder IDs and subfolder IDs assigned in dms_publishers.
    - If user has no assignments and is not admin -> (False, set(), set()) (empty)
    """
    if not user_id:
        return False, set(), set()

    if not ignore_admin and is_user_dms_admin(db, user_id):
        return True, None, None

    # Fetch publisher assignments for this user
    pub_query = text("""
        SELECT assigned_folders, assigned_subfolders
        FROM dms_publishers
        WHERE publisher_user_id = :user_id
          AND (is_deleted = FALSE OR is_deleted IS NULL)
          AND (status = 'ACTIVE' OR status IS NULL)
    """)
    try:
        rows = db.execute(pub_query, {"user_id": user_id}).mappings().all()
    except Exception as e:
        logger.warning(f"Could not query dms_publishers (table may not exist yet): {e}")
        return False, set(), set()

    if not rows:
        return False, set(), set()

    allowed_folder_ids: Set[int] = set()
    explicit_subfolder_ids: Set[int] = set()

    for r in rows:
        # Extract folder IDs
        raw_folders = r.get("assigned_folders") or []
        if isinstance(raw_folders, str):
            try:
                raw_folders = json.loads(raw_folders)
            except Exception:
                raw_folders = []
        if isinstance(raw_folders, list):
            for item in raw_folders:
                if isinstance(item, (int, str)) and str(item).isdigit():
                    allowed_folder_ids.add(int(item))
                elif isinstance(item, dict):
                    fid = item.get("folder_id") or item.get("id")
                    if fid and str(fid).isdigit():
                        allowed_folder_ids.add(int(fid))
                elif isinstance(item, str) and item.strip():
                    name_clean = item.strip().lower()
                    # Resolve dynamically against dms_folders
                    f_rows = db.execute(
                        text("SELECT folder_id FROM dms_folders WHERE LOWER(TRIM(folder_name)) = :name AND (is_deleted = FALSE OR is_deleted IS NULL)"),
                        {"name": name_clean}
                    ).fetchall()
                    for f_row in f_rows:
                        allowed_folder_ids.add(f_row[0])

        # Extract subfolder IDs
        raw_subfolders = r.get("assigned_subfolders") or []
        if isinstance(raw_subfolders, str):
            try:
                raw_subfolders = json.loads(raw_subfolders)
            except Exception:
                raw_subfolders = []
        if isinstance(raw_subfolders, list):
            for item in raw_subfolders:
                if isinstance(item, (int, str)) and str(item).isdigit():
                    explicit_subfolder_ids.add(int(item))
                elif isinstance(item, dict):
                    sfid = item.get("sub_folder_id") or item.get("id")
                    if sfid and str(sfid).isdigit():
                        explicit_subfolder_ids.add(int(sfid))
                    # Also collect any nested sub_sub_folders
                    for sub_sub in (item.get("sub_sub_folders") or []):
                        if isinstance(sub_sub, dict):
                            ssid = sub_sub.get("sub_sub_folder_id") or sub_sub.get("sub_folder_id") or sub_sub.get("id")
                            if ssid and str(ssid).isdigit():
                                explicit_subfolder_ids.add(int(ssid))
                        elif isinstance(sub_sub, (int, str)) and str(sub_sub).isdigit():
                            explicit_subfolder_ids.add(int(sub_sub))
                elif isinstance(item, str) and item.strip():
                    sf_name_clean = item.strip().lower()
                    sf_rows = db.execute(
                        text("SELECT sub_folder_id FROM dms_sub_folders WHERE LOWER(TRIM(sub_folder_name)) = :name AND (is_deleted = FALSE OR is_deleted IS NULL)"),
                        {"name": sf_name_clean}
                    ).fetchall()
                    for sf_row in sf_rows:
                        explicit_subfolder_ids.add(sf_row[0])

    # Also resolve parent folder IDs for any explicit subfolders so the folders are visible
    sf_parents = []
    if explicit_subfolder_ids:
        sf_parents = db.execute(
            text("""
                SELECT sub_folder_id, folder_id 
                FROM dms_sub_folders 
                WHERE sub_folder_id IN :sf_ids 
                  AND (is_deleted = FALSE OR is_deleted IS NULL)
            """).bindparams(bindparam("sf_ids", expanding=True)),
            {"sf_ids": list(explicit_subfolder_ids)}
        ).mappings().all()

        for sf in sf_parents:
            if sf.get("folder_id"):
                allowed_folder_ids.add(int(sf["folder_id"]))

    allowed_subfolder_ids: Set[int] = set(explicit_subfolder_ids)

    # Automatically grant access to child sub-folders under any granted subfolders (arbitrary depth)
    if explicit_subfolder_ids:
        child_sf_rows = db.execute(
            text("""
                WITH RECURSIVE subfolder_tree AS (
                    SELECT sub_folder_id
                    FROM dms_sub_folders
                    WHERE parent_sub_folder_id IN :sf_ids
                      AND (is_deleted = FALSE OR is_deleted IS NULL)
                    UNION ALL
                    SELECT sf.sub_folder_id
                    FROM dms_sub_folders sf
                    INNER JOIN subfolder_tree st ON sf.parent_sub_folder_id = st.sub_folder_id
                    WHERE (sf.is_deleted = FALSE OR sf.is_deleted IS NULL)
                )
                SELECT DISTINCT sub_folder_id FROM subfolder_tree
            """).bindparams(bindparam("sf_ids", expanding=True)),
            {"sf_ids": list(explicit_subfolder_ids)}
        ).mappings().all()
        for csf in child_sf_rows:
            allowed_subfolder_ids.add(int(csf["sub_folder_id"]))

    # For any folder in allowed_folder_ids that has NO specific subfolder in explicit_subfolder_ids,
    # grant access to all its subfolders
    folders_with_explicit_sf = set()
    for sf in sf_parents:
        if sf.get("folder_id"):
            folders_with_explicit_sf.add(int(sf["folder_id"]))

    fully_granted_folders = allowed_folder_ids - folders_with_explicit_sf
    if fully_granted_folders:
        full_sf_rows = db.execute(
            text("""
                SELECT sub_folder_id 
                FROM dms_sub_folders 
                WHERE folder_id IN :f_ids 
                  AND (is_deleted = FALSE OR is_deleted IS NULL)
            """).bindparams(bindparam("f_ids", expanding=True)),
            {"f_ids": list(fully_granted_folders)}
        ).mappings().all()
        for fsf in full_sf_rows:
            allowed_subfolder_ids.add(int(fsf["sub_folder_id"]))

    return False, allowed_folder_ids, allowed_subfolder_ids


def is_user_folder_publisher(
    db: Session,
    user_id: Optional[int],
    folder_id: Optional[int],
    sub_folder_id: Optional[int] = None,
    allowed_folders: Optional[Set[int]] = None,
    allowed_subfolders: Optional[Set[int]] = None,
    is_admin: Optional[bool] = None,
    is_unrestricted: Optional[bool] = None,
) -> bool:
    """
    Returns True if the user has publisher privileges for this folder:
      1. User is an Admin -> True
      2. User has unrestricted folder access -> True
      3. User is an active Publisher assigned to folder_id (and sub_folder_id if specified) -> True
    Supports passing cached allowed_folders/allowed_subfolders to avoid N+1 queries during bulk listings.
    """
    if not user_id:
        return False

    # When checking confidential documents, caller passes is_admin=False and is_unrestricted=False.
    # In that case, admins MUST NOT get automatic bypass — only their real publisher assignments count.
    strictly_enforce = (is_admin is False or is_unrestricted is False)

    if not strictly_enforce:
        if is_admin is True or is_unrestricted is True:
            return True
        if is_admin is None and is_user_dms_admin(db, user_id):
            return True
        if allowed_folders is None:
            unrestricted, allowed_folders, allowed_subfolders = get_user_dms_folder_access(db, user_id)
            if unrestricted:
                return True
    else:
        # If allowed_folders is None (or caller passed None/admin context), load actual assignments:
        if allowed_folders is None:
            _, allowed_folders, allowed_subfolders = get_user_dms_folder_access(
                db, user_id, ignore_admin=True
            )

    if not folder_id:
        return False

    if allowed_folders and folder_id in allowed_folders:
        # Document is at folder root (no subfolder): publisher for this folder ✓
        if not sub_folder_id:
            return True
        # Document is inside a subfolder.
        # allowed_subfolders=None means unrestricted, handled above when not strictly_enforce.
        # allowed_subfolders=set() means the publisher was assigned no subfolders → deny access.
        # allowed_subfolders={...} means check explicit assignment.
        if allowed_subfolders and sub_folder_id in allowed_subfolders:
            return True

    return False



def is_user_dms_publisher(db: Session, user_id: Optional[int]) -> bool:
    """Check if user is registered as an active publisher in dms_publishers."""
    if not user_id:
        return False
    query = text("""
        SELECT 1 FROM dms_publishers
        WHERE publisher_user_id = :uid
          AND (is_deleted = FALSE OR is_deleted IS NULL)
          AND (status = 'ACTIVE' OR status IS NULL)
        LIMIT 1
    """)
    return db.execute(query, {"uid": user_id}).first() is not None


def verify_dms_can_upload(db: Session, user_id: Optional[int]) -> bool:
    """Verifies that the user is an Admin or an active Publisher before allowing uploads."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    if is_user_dms_admin(db, user_id) or is_user_dms_publisher(db, user_id):
        return True
    raise HTTPException(
        status_code=403,
        detail="Permission denied: Only Administrators and authorized Publishers can upload documents."
    )


def verify_dms_folder_publish_access(
    db: Session,
    user_id: Optional[int],
    folder_id: Optional[int],
    sub_folder_id: Optional[int] = None
) -> bool:
    """Verifies that the user can create or publish documents into a specific folder/subfolder."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    if is_user_dms_admin(db, user_id):
        return True

    is_unrestricted, allowed_folders, allowed_subfolders = get_user_dms_folder_access(db, user_id)
    if is_unrestricted:
        return True

    if allowed_folders is None or not allowed_folders:
        raise HTTPException(
            status_code=403,
            detail="Permission denied: You do not have Publisher privileges to create documents."
        )

    if folder_id and folder_id != 0 and folder_id not in allowed_folders:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: You are not assigned as a publisher for folder ID {folder_id}."
        )

    if sub_folder_id and sub_folder_id != 0 and allowed_subfolders and sub_folder_id not in allowed_subfolders:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: You are not assigned as a publisher for sub-folder ID {sub_folder_id}."
        )

    return True


def verify_dms_document_manage_access(
    db: Session,
    user_id: Optional[int],
    document_id: int,
    action: str = "modify"
) -> dict:
    """
    Verifies that the user has permission to modify, update status, or delete a document.
    Allowed for:
      - Admin
      - Original Creator / Publisher of the document
      - Custodian of the document
      - Publisher assigned to the folder where the document is located
    Raises 404 if document doesn't exist, 403 if unauthorized.
    Returns the document row dict.
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    doc = db.execute(
        text("""
            SELECT document_id, document_number, document_title, folder_id, sub_folder_id,
                   created_by, custodian_id, status, confidential_document, security_classification
            FROM dms_documents
            WHERE document_id = :doc_id AND is_deleted = FALSE
        """),
        {"doc_id": document_id}
    ).mappings().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if is_user_dms_admin(db, user_id):
        return dict(doc)

    # Original Creator or Custodian can manage their document
    if (doc.get("created_by") is not None and doc.get("created_by") == user_id) or \
       (doc.get("custodian_id") is not None and doc.get("custodian_id") == user_id):
        return dict(doc)

    # Must be an authorized publisher with access to this document's folder
    folder_id = doc.get("folder_id")
    sub_folder_id = doc.get("sub_folder_id")
    if is_user_folder_publisher(db, user_id, folder_id, sub_folder_id):
        return dict(doc)

    raise HTTPException(
        status_code=403,
        detail=f"Permission denied: Only Administrators and assigned folder Publishers can {action} this document."
    )


