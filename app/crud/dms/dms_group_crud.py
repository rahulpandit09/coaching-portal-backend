import json
from sqlalchemy.orm import Session
from sqlalchemy.sql import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB


from app.schemas.dms.dms_group_schema import (
    DmsGroupCreate,
    DmsGroupUpdate
)
from app.crud.dms.dms_auth import NotFoundError


# -------------------------------------------------
# CREATE (MASTER + HISTORY)
# -------------------------------------------------
def create_dms_group(db: Session, data: DmsGroupCreate):
    payload = data.model_dump()

    insert_master = text("""
        INSERT INTO dms_groups (
            group_name,
            discipline_dept,
            description,
            member_engineers,
            member_count,
            is_deleted,
            created_by
        )
        VALUES (
            :group_name,
            :discipline_dept,
            :description,
            :member_engineers,
            :member_count,
            FALSE,
            :created_by
        )
        RETURNING group_id
    """).bindparams(
        bindparam("member_engineers", type_=JSONB)
    )

    insert_history = text("""
        INSERT INTO dms_groups_history (
            group_id,
            group_name,
            discipline_dept,
            description,
            member_engineers,
            member_count,
            is_deleted,
            created_by,
            created_at
        )
        SELECT
            group_id,
            group_name,
            discipline_dept,
            description,
            member_engineers,
            member_count,
            is_deleted,
            created_by,
            created_at
        FROM dms_groups
        WHERE group_id = :group_id
    """)

    try:
        group_id = db.execute(insert_master, payload).scalar()
        db.execute(insert_history, {"group_id": group_id})
        db.commit()
        return group_id
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to create DMS group: {str(e)}")


# -------------------------------------------------
# UPDATE (MASTER + HISTORY)
# -------------------------------------------------
def update_dms_group(db: Session, group_id: int, data: DmsGroupUpdate):
    payload = data.model_dump(exclude_unset=True)

    # Never allow updating creation audit fields on PUT calls
    payload.pop("created_at", None)
    payload.pop("created_by", None)

    if not payload:
        return 0

    payload["group_id"] = group_id

    # Build dynamic SET clause from supplied fields
    set_clauses = []
    field_map = {
        "group_name": "group_name",
        "discipline_dept": "discipline_dept",
        "description": "description",
        "member_engineers": "member_engineers",
        "member_count": "member_count",
        "updated_by": "updated_by",
    }

    bind_params = []
    for key, col in field_map.items():
        if key in payload:
            set_clauses.append(f"{col} = :{key}")
            if key == "member_engineers":
                bind_params.append(bindparam(key, type_=JSONB))

    if not set_clauses:
        return 0

    set_clauses.append("updated_at = NOW()")

    update_sql = f"""
        UPDATE dms_groups
        SET {', '.join(set_clauses)}
        WHERE group_id = :group_id AND is_deleted = FALSE
    """

    update_query = text(update_sql)
    for bp in bind_params:
        update_query = update_query.bindparams(bp)

    history_query = text("""
        INSERT INTO dms_groups_history (
            group_id,
            group_name,
            discipline_dept,
            description,
            member_engineers,
            member_count,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        )
        SELECT
            group_id,
            group_name,
            discipline_dept,
            description,
            member_engineers,
            member_count,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM dms_groups
        WHERE group_id = :group_id
    """)

    try:
        result = db.execute(update_query, payload)
        if result.rowcount > 0:
            db.execute(history_query, {"group_id": group_id})
        db.commit()
        return result.rowcount
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to update DMS group: {str(e)}")


# -------------------------------------------------
# GET BY ID
# -------------------------------------------------
def get_dms_group(db: Session, group_id: int):
    query = text("""
        SELECT
            g.group_id,
            g.group_name,
            g.discipline_dept,
            g.description,
            g.member_engineers,
            g.member_count,
            g.is_deleted,
            g.created_at,
            g.created_by,
            TRIM(CONCAT_WS(' ', uc.first_name, uc.last_name)) AS created_by_name,
            g.updated_at,
            g.updated_by,
            TRIM(CONCAT_WS(' ', uu.first_name, uu.last_name)) AS updated_by_name
        FROM dms_groups g
        LEFT JOIN users uc ON uc.id = g.created_by
        LEFT JOIN users uu ON uu.id = g.updated_by
        WHERE g.group_id = :group_id AND g.is_deleted = FALSE
    """)

    result = db.execute(query, {"group_id": group_id}).mappings().first()
    return result


# -------------------------------------------------
# GET ALL (non-deleted)
# -------------------------------------------------
def get_all_dms_groups(db: Session):
    query = text("""
        SELECT
            g.group_id,
            g.group_name,
            g.discipline_dept,
            g.description,
            g.member_engineers,
            g.member_count,
            g.is_deleted,
            g.created_at,
            g.created_by,
            TRIM(CONCAT_WS(' ', uc.first_name, uc.last_name)) AS created_by_name,
            g.updated_at,
            g.updated_by,
            TRIM(CONCAT_WS(' ', uu.first_name, uu.last_name)) AS updated_by_name
        FROM dms_groups g
        LEFT JOIN users uc ON uc.id = g.created_by
        LEFT JOIN users uu ON uu.id = g.updated_by
        WHERE g.is_deleted = FALSE
        ORDER BY g.group_id DESC
    """)

    result = db.execute(query).mappings().all()
    return result



# -------------------------------------------------
# SOFT DELETE (+ HISTORY)
# -------------------------------------------------
def soft_delete_dms_group(db: Session, group_id: int, deleted_by: int = None):
    update_query = text("""
        UPDATE dms_groups
        SET
            is_deleted = TRUE,
            updated_by = :deleted_by,
            updated_at = NOW()
        WHERE group_id = :group_id AND is_deleted = FALSE
    """)

    history_query = text("""
        INSERT INTO dms_groups_history (
            group_id,
            group_name,
            discipline_dept,
            description,
            member_engineers,
            member_count,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        )
        SELECT
            group_id,
            group_name,
            discipline_dept,
            description,
            member_engineers,
            member_count,
            is_deleted,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM dms_groups
        WHERE group_id = :group_id
    """)

    try:
        result = db.execute(update_query, {
            "group_id": group_id,
            "deleted_by": deleted_by
        })
        if result.rowcount == 0:
            raise NotFoundError("Group not found or already deleted")
        db.execute(history_query, {"group_id": group_id})
        db.commit()
        return result.rowcount
    except NotFoundError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to delete DMS group: {str(e)}")


# -------------------------------------------------
# DROPDOWN: USERS WITH ENGINEER ROLE (submenu_id = 30)
# -------------------------------------------------
def get_engineer_dropdown_users(db: Session):
    query = text("""
        SELECT DISTINCT
            u.id                                            AS user_id,
            TRIM(CONCAT_WS(' ', u.first_name, u.last_name)) AS user_name,
            u.first_name,
            u.last_name,
            COALESCE(u.email, '')                           AS email,
            ''                                              AS employee_code,
            ''                                              AS designation,
            ''                                              AS station_name,
            NULL::integer                                   AS station_id,
            COALESCE(r.id, u.role_id)                       AS role_id,
            COALESCE(r.name, '')                            AS role_name
        FROM users u
        LEFT JOIN role r ON r.id = u.role_id
        LEFT JOIN role_submenu rsm ON rsm.role_id = r.id
        WHERE (rsm.submenu_id = 30 OR r.id IN (1, 4, 31) OR LOWER(r.name) LIKE '%engineer%' OR LOWER(r.name) LIKE '%admin%')
        ORDER BY user_name ASC
    """)
    result = db.execute(query).mappings().all()
    return result


# -------------------------------------------------
# DASHBOARD COUNTS (ENGINEER GROUPS & DIRECTORY - 4 CARDS)
# -------------------------------------------------
def get_dms_group_dashboard_counts(db: Session) -> dict:
    """
    Computes dashboard metrics for Engineer Groups:
    - TOTAL GROUPS: Configured engineer clusters
    - ASSIGNED ENGINEERS: Unique engineers in groups
    - TOTAL DIRECTORY: Engineers in system directory
    - PUBLISHER READY: Instant Delegation (+ Available on document creation)
    """
    # 1. Total Groups and Member Engineers
    group_query = text("""
        SELECT
            group_id,
            member_engineers,
            member_count
        FROM dms_groups
        WHERE is_deleted = FALSE OR is_deleted IS NULL
    """)
    groups = [dict(r) for r in db.execute(group_query).mappings().all()]
    total_groups_count = len(groups)

    # 2. Extract Unique Assigned Engineers across all active groups
    unique_engineer_ids = set()
    for g in groups:
        raw = g.get("member_engineers")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                raw = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, (int, str)) and str(item).isdigit():
                    unique_engineer_ids.add(int(item))
                elif isinstance(item, dict):
                    uid = item.get("user_id") or item.get("id")
                    if uid and str(uid).isdigit():
                        unique_engineer_ids.add(int(uid))

    assigned_engineers_count = len(unique_engineer_ids)

    # 3. Total Engineers in System Directory
    dir_users = get_engineer_dropdown_users(db)
    total_directory_count = len(dir_users)

    # 4. Publisher Ready
    publisher_ready_title = "Instant Delegation"
    publisher_ready_subtitle = "Available on document creation"

    # 4 Dashboard Cards matching UI exactly
    cards = [
        {
            "title": "TOTAL GROUPS",
            "value": str(total_groups_count),
            "subtitle": "Configured engineer clusters"
        },
        {
            "title": "ASSIGNED ENGINEERS",
            "value": str(assigned_engineers_count),
            "subtitle": "Unique engineers in groups"
        },
        {
            "title": "TOTAL DIRECTORY",
            "value": str(total_directory_count),
            "subtitle": "Engineers in system directory"
        },
        {
            "title": "PUBLISHER READY",
            "value": publisher_ready_title,
            "subtitle": publisher_ready_subtitle
        }
    ]

    return {
        "total_groups": total_groups_count,
        "assigned_engineers": assigned_engineers_count,
        "total_directory": total_directory_count,
        "publisher_ready": publisher_ready_title,
        "publisher_ready_subtitle": publisher_ready_subtitle,
        "cards": cards
    }



