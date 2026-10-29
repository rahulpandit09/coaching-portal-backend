import json
import logging
from typing import Optional
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.sql import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB

logger = logging.getLogger(__name__)

from app.schemas.dms.dms_publisher_schema import (
    DmsPublisherCreate,
    DmsPublisherUpdate
)
from app.crud.dms.dms_auth import NotFoundError


# -------------------------------------------------
# CREATE (MASTER + HISTORY)
# -------------------------------------------------
def create_dms_publisher(
    db: Session,
    data: DmsPublisherCreate,
    background_tasks: Optional[BackgroundTasks] = None,
):
    payload = data.model_dump()

    insert_master = text("""
        INSERT INTO dms_publishers (
            publisher_user_id,
            publisher_name,
            publisher_email,
            publisher_dept,
            publisher_station_location,
            publisher_station_id,
            status,
            assigned_folders,
            assigned_subfolders,
            is_deleted,
            created_by
        )
        VALUES (
            :publisher_user_id,
            :publisher_name,
            :publisher_email,
            :publisher_dept,
            :publisher_station_location,
            :publisher_station_id,
            :status,
            :assigned_folders,
            :assigned_subfolders,
            FALSE,
            :created_by
        )
        RETURNING publisher_id
    """).bindparams(
        bindparam("assigned_folders", type_=JSONB),
        bindparam("assigned_subfolders", type_=JSONB)
    )

    insert_history = text("""
        INSERT INTO dms_publishers_history (
            publisher_id,
            publisher_user_id,
            publisher_name,
            publisher_email,
            publisher_dept,
            publisher_station_location,
            publisher_station_id,
            status,
            assigned_folders,
            assigned_subfolders,
            is_deleted,
            created_by
        )
        SELECT
            publisher_id,
            publisher_user_id,
            publisher_name,
            publisher_email,
            publisher_dept,
            publisher_station_location,
            publisher_station_id,
            status,
            assigned_folders,
            assigned_subfolders,
            is_deleted,
            created_by
        FROM dms_publishers
        WHERE publisher_id = :publisher_id
    """)

    try:
        publisher_id = db.execute(insert_master, payload).scalar()
        db.execute(insert_history, {"publisher_id": publisher_id})
        db.commit()

        # Trigger notification to the appointed publisher user
        try:
            from app.crud.dms.dms_notification_crud import notify_publisher_assigned
            notify_publisher_assigned(
                db=db,
                publisher_user_id=payload.get("publisher_user_id"),
                assigned_folders=payload.get("assigned_folders"),
                actor_id=payload.get("created_by"),
                background_tasks=background_tasks,
            )
        except Exception as ne:
            logger.debug("[dms_publisher] Notification create error: %s", ne)

        return publisher_id
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to create DMS publisher: {str(e)}")


# -------------------------------------------------
# UPDATE (MASTER + HISTORY)
# -------------------------------------------------
def update_dms_publisher(
    db: Session,
    publisher_id: int,
    data: DmsPublisherUpdate,
    background_tasks: Optional[BackgroundTasks] = None,
):
    payload = data.model_dump(exclude_unset=True)

    # Never allow updating creation audit fields on PUT calls
    payload.pop("created_at", None)
    payload.pop("created_by", None)

    if not payload:
        return 0

    payload["publisher_id"] = publisher_id

    # Build dynamic SET clause from supplied fields
    set_clauses = []
    field_map = {
        "publisher_user_id": "publisher_user_id",
        "publisher_name": "publisher_name",
        "publisher_email": "publisher_email",
        "publisher_dept": "publisher_dept",
        "publisher_station_location": "publisher_station_location",
        "publisher_station_id": "publisher_station_id",
        "status": "status",
        "assigned_folders": "assigned_folders",
        "assigned_subfolders": "assigned_subfolders",
        "updated_by": "updated_by",
    }

    bind_params = []
    for key, col in field_map.items():
        if key in payload:
            set_clauses.append(f"{col} = :{key}")
            if key in ("assigned_folders", "assigned_subfolders"):
                bind_params.append(bindparam(key, type_=JSONB))

    if not set_clauses:
        return 0

    set_clauses.append("updated_at = NOW()")

    update_sql = f"""
        UPDATE dms_publishers
        SET {', '.join(set_clauses)}
        WHERE publisher_id = :publisher_id AND is_deleted = FALSE
    """

    update_query = text(update_sql)
    for bp in bind_params:
        update_query = update_query.bindparams(bp)

    history_query = text("""
        INSERT INTO dms_publishers_history (
            publisher_id,
            publisher_user_id,
            publisher_name,
            publisher_email,
            publisher_dept,
            publisher_station_location,
            publisher_station_id,
            status,
            assigned_folders,
            assigned_subfolders,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        )
        SELECT
            publisher_id,
            publisher_user_id,
            publisher_name,
            publisher_email,
            publisher_dept,
            publisher_station_location,
            publisher_station_id,
            status,
            assigned_folders,
            assigned_subfolders,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM dms_publishers
        WHERE publisher_id = :publisher_id
    """)

    try:
        result = db.execute(update_query, payload)
        if result.rowcount > 0:
            db.execute(history_query, {"publisher_id": publisher_id})
        db.commit()

        # Trigger notification if assigned_folders or assigned_subfolders were updated
        if "assigned_folders" in payload or "assigned_subfolders" in payload:
            try:
                from app.crud.dms.dms_notification_crud import notify_publisher_assigned
                pub_uid = payload.get("publisher_user_id")
                if not pub_uid:
                    pub_row = db.execute(
                        text("SELECT publisher_user_id FROM dms_publishers WHERE publisher_id = :pid"),
                        {"pid": publisher_id}
                    ).mappings().first()
                    pub_uid = pub_row["publisher_user_id"] if pub_row else None
                if pub_uid:
                    notify_publisher_assigned(
                        db=db,
                        publisher_user_id=pub_uid,
                        assigned_folders=payload.get("assigned_folders"),
                        actor_id=payload.get("updated_by"),
                        background_tasks=background_tasks,
                    )
            except Exception as ne:
                logger.debug("[dms_publisher] Notification update error: %s", ne)

        return result.rowcount
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to update DMS publisher: {str(e)}")


# -------------------------------------------------
# ENRICH ASSIGNED FOLDERS & SUBFOLDERS (ID + NAME + HIERARCHY)
# -------------------------------------------------
def _enrich_publishers_with_folders(db: Session, publishers: list) -> list:
    if not publishers:
        return publishers

    result_list = [dict(p) for p in publishers]

    # Pre-fetch all active folders from dms_folders
    f_rows = db.execute(text("""
        SELECT folder_id, folder_name, folder_icon
        FROM dms_folders
        WHERE is_deleted = FALSE
    """)).mappings().all()

    folder_by_id = {}
    folder_by_name = {}
    for f in f_rows:
        f_dict = {
            "folder_id": f["folder_id"],
            "folder_name": f["folder_name"],
            "folder_icon": f.get("folder_icon")
        }
        folder_by_id[f["folder_id"]] = f_dict
        name_key = str(f["folder_name"] or "").strip().lower()
        if name_key:
            folder_by_name[name_key] = f_dict

    # Pre-fetch all active subfolders from dms_sub_folders
    sf_rows = db.execute(text("""
        SELECT sub_folder_id, folder_id, parent_sub_folder_id, sub_folder_name, sub_folder_code
        FROM dms_sub_folders
        WHERE is_deleted = FALSE
    """)).mappings().all()

    subfolder_by_id = {}
    subfolders_by_name = {}
    children_by_parent_sf = {}
    for sf in sf_rows:
        sf_dict = {
            "sub_folder_id": sf["sub_folder_id"],
            "folder_id": sf["folder_id"],
            "parent_sub_folder_id": sf.get("parent_sub_folder_id"),
            "sub_folder_name": sf["sub_folder_name"],
            "sub_folder_code": sf.get("sub_folder_code")
        }
        subfolder_by_id[sf["sub_folder_id"]] = sf_dict
        sf_name_key = str(sf["sub_folder_name"] or "").strip().lower()
        if sf_name_key:
            subfolders_by_name.setdefault(sf_name_key, []).append(sf_dict)
        if sf.get("parent_sub_folder_id"):
            children_by_parent_sf.setdefault(sf["parent_sub_folder_id"], []).append(sf_dict)

    # Recursive collector for all descendants of a subfolder
    def _collect_descendants(sf_id: int, target_set: set):
        for child in children_by_parent_sf.get(sf_id, []):
            cid = child["sub_folder_id"]
            if cid not in target_set:
                target_set.add(cid)
                _collect_descendants(cid, target_set)

    # Robust ID extractor handling integers, digit strings, and objects
    def _extract_ids_and_names(raw_data, id_key, name_key):
        extracted_ids = set()
        extracted_names = set()
        if not raw_data:
            return extracted_ids, extracted_names
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except Exception:
                raw_data = [raw_data]
        if not isinstance(raw_data, list):
            raw_data = [raw_data]

        for item in raw_data:
            if isinstance(item, (int, str)) and str(item).isdigit():
                extracted_ids.add(int(item))
            elif isinstance(item, str) and item.strip():
                extracted_names.add(item.strip().lower())
            elif isinstance(item, dict):
                v_id = item.get(id_key) or item.get("id")
                if v_id and str(v_id).isdigit():
                    extracted_ids.add(int(v_id))
                v_name = item.get(name_key) or item.get("name")
                if v_name and isinstance(v_name, str) and v_name.strip():
                    extracted_names.add(v_name.strip().lower())

        return extracted_ids, extracted_names

    for p in result_list:
        raw_folders = p.get("assigned_folders") or []
        raw_subfolders = p.get("assigned_subfolders") or []

        # 1. Resolve folder IDs
        folder_ids, folder_names = _extract_ids_and_names(
            raw_folders, "folder_id", "folder_name"
        )
        for fname in folder_names:
            if fname in folder_by_name:
                folder_ids.add(folder_by_name[fname]["folder_id"])

        # Extract embedded subfolders ONLY from dictionary objects within raw_folders (never from plain integer folder IDs)
        embedded_sf_ids = set()
        embedded_sf_names = set()
        raw_folders_list = raw_folders if isinstance(raw_folders, list) else [raw_folders] if raw_folders else []
        for item in raw_folders_list:
            if isinstance(item, dict):
                for child_prop in ("subfolders", "children", "sub_sub_folders"):
                    if child_prop in item and isinstance(item[child_prop], list):
                        c_ids, c_names = _extract_ids_and_names(
                            item[child_prop], "sub_folder_id", "sub_folder_name"
                        )
                        embedded_sf_ids.update(c_ids)
                        embedded_sf_names.update(c_names)

        # 2. Resolve subfolder IDs
        subfolder_ids, subfolder_names = _extract_ids_and_names(
            raw_subfolders, "sub_folder_id", "sub_folder_name"
        )
        subfolder_ids.update(embedded_sf_ids)
        subfolder_names.update(embedded_sf_names)

        for sname in subfolder_names:
            if ":::" in sname:
                sname = sname.split(":::", 1)[1].strip()
            if sname in subfolders_by_name:
                for matched in subfolders_by_name[sname]:
                    subfolder_ids.add(matched["sub_folder_id"])

        # 3. Only keep valid, existing IDs
        assigned_fids = {fid for fid in folder_ids if fid in folder_by_id}
        explicit_sfids = {sfid for sfid in subfolder_ids if sfid in subfolder_by_id}

        # Capture the explicitly saved folder IDs BEFORE auto-adding parents
        # This preserves what the user actually saved in the DB
        explicit_fids = set(assigned_fids)

        # 4. Auto-include all nested children/descendants of assigned subfolders
        all_relevant_sfids = set(explicit_sfids)
        for sf_id in explicit_sfids:
            _collect_descendants(sf_id, all_relevant_sfids)

        # Ensure parent folders of all assigned subfolders are present in the TREE only
        # (assigned_fids is used for tree rendering; explicit_fids is used for IDs)
        for sf_id in all_relevant_sfids:
            fid = subfolder_by_id[sf_id]["folder_id"]
            if fid and fid in folder_by_id:
                assigned_fids.add(fid)

        # 5. Build sub-folder node map with children & sub_sub_folders aliases
        sf_node_map = {}
        for sf_id in all_relevant_sfids:
            raw_sf = subfolder_by_id[sf_id]
            parent_id = raw_sf.get("parent_sub_folder_id")
            parent_name = (
                subfolder_by_id.get(parent_id, {}).get("sub_folder_name")
                if parent_id
                else None
            )
            kids = []
            sf_node = {
                "sub_folder_id": raw_sf["sub_folder_id"],
                "sub_folder_name": raw_sf["sub_folder_name"],
                "sub_folder_code": raw_sf.get("sub_folder_code"),
                "folder_id": raw_sf["folder_id"],
                "parent_sub_folder_id": parent_id,
                "parent_sub_folder_name": parent_name,
                "sub_sub_folder_id": raw_sf["sub_folder_id"],       # alias
                "sub_sub_folder_name": raw_sf["sub_folder_name"],   # alias
                "children": kids,
                "sub_sub_folders": kids                              # alias
            }
            sf_node_map[sf_id] = sf_node

        # 6. Build folder nodes — only use explicit_fids (what user saved)
        #    auto-added parent folders (assigned_fids) are excluded from the tree
        folders_tree = []
        folder_node_map = {}
        for fid in explicit_fids:
            f_info = folder_by_id[fid]
            subs = []
            f_node = {
                "folder_id": f_info["folder_id"],
                "folder_name": f_info["folder_name"],
                "folder_icon": f_info.get("folder_icon"),
                "subfolders": subs,
                "sub_folders": subs  # alias
            }
            folders_tree.append(f_node)
            folder_node_map[fid] = f_node

        # 7. Assemble the nested tree (arbitrary depth, zero duplicates)
        # Sort sf_node_map by sub_folder_id so order is deterministic
        for sf_id in sorted(sf_node_map.keys()):
            node = sf_node_map[sf_id]
            parent_sf_id = node.get("parent_sub_folder_id")
            fid = node.get("folder_id")

            if parent_sf_id and parent_sf_id in sf_node_map:
                # Nested child: attach to parent sub-folder
                sf_node_map[parent_sf_id]["children"].append(node)
            elif fid and fid in folder_node_map:
                # Top-level sub-folder: attach to folder
                folder_node_map[fid]["subfolders"].append(node)

        # 8. Build enriched flat assigned_subfolders list
        flat_subfolders = []
        for sf_id in sorted(sf_node_map.keys()):
            node = sf_node_map[sf_id]
            fid = node.get("folder_id")
            flat_subfolders.append({
                "sub_folder_id": node["sub_folder_id"],
                "sub_folder_name": node["sub_folder_name"],
                "folder_id": fid,
                "folder_name": folder_by_id.get(fid, {}).get("folder_name") if fid else None,
                "parent_sub_folder_id": node["parent_sub_folder_id"],
                "parent_sub_folder_name": node["parent_sub_folder_name"]
            })

        p["assigned_folders"] = folders_tree
        p["assigned_subfolders"] = flat_subfolders
        p["assigned_hierarchy"] = folders_tree
        p["assigned_folder_ids"] = sorted(list(explicit_fids))
        p["assigned_subfolder_ids"] = sorted(list(explicit_sfids))
        p["raw_assigned_folders"] = raw_folders
        p["raw_assigned_subfolders"] = raw_subfolders

    return result_list


# -------------------------------------------------
# GET BY ID
# -------------------------------------------------
def get_dms_publisher(db: Session, publisher_id: int):
    query = text("""
        SELECT
            p.publisher_id,
            p.publisher_user_id,
            p.publisher_name,
            p.publisher_email,
            p.publisher_dept,
            p.publisher_station_location,
            p.publisher_station_id,
            p.status,
            p.assigned_folders,
            p.assigned_subfolders,
            p.is_deleted,
            p.created_at,
            p.created_by,
            TRIM(CONCAT_WS(' ', uc.first_name, uc.last_name)) AS created_by_name,
            p.updated_at,
            p.updated_by,
            TRIM(CONCAT_WS(' ', uu.first_name, uu.last_name)) AS updated_by_name
        FROM dms_publishers p
        LEFT JOIN users uc ON uc.id = p.created_by
        LEFT JOIN users uu ON uu.id = p.updated_by
        WHERE p.publisher_id = :publisher_id AND p.is_deleted = FALSE
    """)

    result = db.execute(query, {"publisher_id": publisher_id}).mappings().first()
    if not result:
        return None
    return _enrich_publishers_with_folders(db, [dict(result)])[0]


# -------------------------------------------------
# GET ALL (non-deleted)
# -------------------------------------------------
def get_all_dms_publishers(db: Session):
    query = text("""
        SELECT
            p.publisher_id,
            p.publisher_user_id,
            p.publisher_name,
            p.publisher_email,
            p.publisher_dept,
            p.publisher_station_location,
            p.publisher_station_id,
            p.status,
            p.assigned_folders,
            p.assigned_subfolders,
            p.is_deleted,
            p.created_at,
            p.created_by,
            TRIM(CONCAT_WS(' ', uc.first_name, uc.last_name)) AS created_by_name,
            p.updated_at,
            p.updated_by,
            TRIM(CONCAT_WS(' ', uu.first_name, uu.last_name)) AS updated_by_name
        FROM dms_publishers p
        LEFT JOIN users uc ON uc.id = p.created_by
        LEFT JOIN users uu ON uu.id = p.updated_by
        WHERE p.is_deleted = FALSE
        ORDER BY p.publisher_id DESC
    """)

    result = db.execute(query).mappings().all()
    return _enrich_publishers_with_folders(db, result)


# -------------------------------------------------
# GET ALL BY USER
# -------------------------------------------------
def get_dms_publishers_by_user(db: Session, user_id: int):
    query = text("""
        SELECT
            p.publisher_id,
            p.publisher_user_id,
            p.publisher_name,
            p.publisher_email,
            p.publisher_dept,
            p.publisher_station_location,
            p.publisher_station_id,
            p.status,
            p.assigned_folders,
            p.assigned_subfolders,
            p.is_deleted,
            p.created_at,
            p.created_by,
            TRIM(CONCAT_WS(' ', uc.first_name, uc.last_name)) AS created_by_name,
            p.updated_at,
            p.updated_by,
            TRIM(CONCAT_WS(' ', uu.first_name, uu.last_name)) AS updated_by_name
        FROM dms_publishers p
        LEFT JOIN users uc ON uc.id = p.created_by
        LEFT JOIN users uu ON uu.id = p.updated_by
        WHERE p.publisher_user_id = :user_id AND p.is_deleted = FALSE
        ORDER BY p.publisher_id DESC
    """)

    result = db.execute(query, {"user_id": user_id}).mappings().all()
    return _enrich_publishers_with_folders(db, result)




# -------------------------------------------------
# SOFT DELETE (+ HISTORY)
# -------------------------------------------------
def soft_delete_dms_publisher(db: Session, publisher_id: int, deleted_by: int = None):
    update_query = text("""
        UPDATE dms_publishers
        SET
            is_deleted = TRUE,
            status = 'DELETED',
            updated_by = :deleted_by,
            updated_at = NOW()
        WHERE publisher_id = :publisher_id AND is_deleted = FALSE
    """)

    history_query = text("""
        INSERT INTO dms_publishers_history (
            publisher_id,
            publisher_user_id,
            publisher_name,
            publisher_email,
            publisher_dept,
            publisher_station_location,
            publisher_station_id,
            status,
            assigned_folders,
            assigned_subfolders,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        )
        SELECT
            publisher_id,
            publisher_user_id,
            publisher_name,
            publisher_email,
            publisher_dept,
            publisher_station_location,
            publisher_station_id,
            status,
            assigned_folders,
            assigned_subfolders,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM dms_publishers
        WHERE publisher_id = :publisher_id
    """)

    try:
        result = db.execute(update_query, {
            "publisher_id": publisher_id,
            "deleted_by": deleted_by
        })
        if result.rowcount == 0:
            raise NotFoundError("Publisher not found or already deleted")
        db.execute(history_query, {"publisher_id": publisher_id})
        db.commit()
        return result.rowcount
    except NotFoundError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to delete DMS publisher: {str(e)}")


# -------------------------------------------------
# STATUS CHANGE (ACTIVE / INACTIVE + HISTORY)
# -------------------------------------------------
def update_dms_publisher_status(db: Session, publisher_id: int, status: str, updated_by: Optional[int] = None):
    update_query = text("""
        UPDATE dms_publishers
        SET
            status = :status,
            updated_by = :updated_by,
            updated_at = NOW()
        WHERE publisher_id = :publisher_id AND is_deleted = FALSE
    """)

    history_query = text("""
        INSERT INTO dms_publishers_history (
            publisher_id,
            publisher_user_id,
            publisher_name,
            publisher_email,
            publisher_dept,
            publisher_station_location,
            publisher_station_id,
            status,
            assigned_folders,
            assigned_subfolders,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        )
        SELECT
            publisher_id,
            publisher_user_id,
            publisher_name,
            publisher_email,
            publisher_dept,
            publisher_station_location,
            publisher_station_id,
            status,
            assigned_folders,
            assigned_subfolders,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM dms_publishers
        WHERE publisher_id = :publisher_id
    """)

    try:
        result = db.execute(update_query, {
            "publisher_id": publisher_id,
            "status": status,
            "updated_by": updated_by
        })
        if result.rowcount == 0:
            raise NotFoundError("Publisher not found or already deleted")
        db.execute(history_query, {"publisher_id": publisher_id})
        db.commit()
        return {
            "publisher_id": publisher_id,
            "status": status
        }
    except NotFoundError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to update DMS publisher status: {str(e)}")


# -------------------------------------------------
# DROPDOWN: ALL ACTIVE EMPLOYEES FROM USERS TABLE
# -------------------------------------------------
def get_publisher_dropdown_users(db: Session):
    query = text("""
        SELECT DISTINCT
            u.id                                            AS user_id,
            COALESCE(NULLIF(TRIM(CONCAT_WS(' ', u.first_name, u.last_name)), ''), u.username, '') AS user_name,
            u.first_name,
            u.last_name,
            COALESCE(u.email, '')                           AS email,
            ''                                              AS employee_code,
            ''                                              AS designation,
            ''                                              AS publisher_station_location,
            NULL::integer                                   AS publisher_station_id,
            COALESCE(r.id, u.role_id)                       AS role_id,
            COALESCE(r.name, '')                            AS role_name
        FROM users u
        LEFT JOIN role r ON r.id = u.role_id
        ORDER BY user_name ASC
    """)
    result = db.execute(query).mappings().all()
    return result



# -------------------------------------------------
# DASHBOARD COUNTS (PUBLISHER DIRECTORY & GOVERNANCE)
# -------------------------------------------------
def get_dms_publisher_dashboard_counts(db: Session, publishers: list = None) -> dict:
    """
    Computes dashboard metrics for Publisher Directory & Folder Governance:
    - TOTAL PUBLISHERS: Authorized content controllers (Active)
    - PRIMARY FOLDERS: All folders actively governed in DMS
    - MULTI-PUBLISHER FOLDERS: Folders governed collaboratively by 2+ publishers
    - ADMIN AUTHORITY: Governance role summary (+ Non-Confidential Archive)
    """
    # 1. Non-deleted publishers
    if publishers is None:
        pub_query = text("""
            SELECT
                publisher_id,
                publisher_user_id,
                publisher_name,
                publisher_email,
                status,
                assigned_folders,
                assigned_subfolders
            FROM dms_publishers
            WHERE is_deleted = FALSE OR is_deleted IS NULL
        """)
        pub_list = [dict(r) for r in db.execute(pub_query).mappings().all()]
    else:
        pub_list = [dict(p) for p in publishers]

    total_publishers_all = len(pub_list)

    active_publishers = [
        p for p in pub_list
        if (p.get("status") is None or str(p.get("status")).strip().upper() == "ACTIVE")
    ]
    active_publishers_count = len(active_publishers)
    inactive_publishers_count = total_publishers_all - active_publishers_count

    # 2. Primary folders in DMS
    folder_query = text("""
        SELECT
            folder_id,
            folder_name,
            folder_icon
        FROM dms_folders
        WHERE is_deleted = FALSE OR is_deleted IS NULL
        ORDER BY folder_id ASC
    """)
    folders = [dict(r) for r in db.execute(folder_query).mappings().all()]
    primary_folders_count = len(folders)
    all_folder_ids = {f["folder_id"] for f in folders}

    # 3. Subfolders for parent folder resolution
    sf_query = text("""
        SELECT
            sub_folder_id,
            folder_id,
            sub_folder_name
        FROM dms_sub_folders
        WHERE is_deleted = FALSE OR is_deleted IS NULL
    """)
    subfolders = [dict(r) for r in db.execute(sf_query).mappings().all()]
    subfolder_to_folder = {
        sf["sub_folder_id"]: sf["folder_id"]
        for sf in subfolders
        if sf.get("folder_id") is not None
    }

    # Helper function to parse JSON lists/dicts of IDs
    def _extract_ids_set(raw_data, id_key):
        extracted = set()
        if not raw_data:
            return extracted
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except Exception:
                return extracted
        if isinstance(raw_data, list):
            for item in raw_data:
                if isinstance(item, (int, str)) and str(item).isdigit():
                    extracted.add(int(item))
                elif isinstance(item, dict):
                    v = item.get(id_key) or item.get("id")
                    if v and str(v).isdigit():
                        extracted.add(int(v))
        return extracted

    # Count publishers assigned per folder to determine multi-publisher folders
    folder_pub_count = {fid: 0 for fid in all_folder_ids}
    for p in active_publishers:
        direct_fids = _extract_ids_set(p.get("assigned_folders"), "folder_id")
        assigned_sfids = _extract_ids_set(p.get("assigned_subfolders"), "sub_folder_id")
        parent_fids = {
            subfolder_to_folder[sfid]
            for sfid in assigned_sfids
            if sfid in subfolder_to_folder
        }
        assigned_folders_for_pub = (direct_fids | parent_fids) & all_folder_ids
        for fid in assigned_folders_for_pub:
            folder_pub_count[fid] += 1

    multi_publisher_count = sum(1 for cnt in folder_pub_count.values() if cnt >= 2)

    admin_authority_title = "Governance Only"
    admin_authority_subtitle = "+ Non-Confidential Archive"

    # 4 Dashboard cards matching the UI screenshot exactly
    cards = [
        {
            "title": "TOTAL PUBLISHERS",
            "value": str(active_publishers_count),
            "subtitle": "Authorized content controllers"
        },
        {
            "title": "PRIMARY FOLDERS",
            "value": str(primary_folders_count),
            "subtitle": "All folders actively governed"
        },
        {
            "title": "MULTI-PUBLISHER FOLDERS",
            "value": f"{multi_publisher_count} Folders",
            "subtitle": "Collaborative delegation"
        },
        {
            "title": "ADMIN AUTHORITY",
            "value": admin_authority_title,
            "subtitle": admin_authority_subtitle
        }
    ]

    return {
        "total_publishers": active_publishers_count,
        "primary_folders": primary_folders_count,
        "multi_publisher_folders": f"{multi_publisher_count} Folders",
        "admin_authority": admin_authority_title,
        "admin_authority_subtitle": admin_authority_subtitle,
        "cards": cards
    }




