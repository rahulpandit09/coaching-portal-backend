# app/crud/dms/dms_notification_crud.py
"""
DMS Notification Service
========================
Unified notification service for Document Management System (DMS).
Follows strict Petronet standards matching capex_csr_notification.py and audit_notification_crud.py:
  * Zero email/Gmail triggers (In-App DB + WebSocket only).
  * Strict redirect_url = None (no deep links in payload).
  * 1-minute deduplication window to prevent duplicate notifications.
  * Direct parameterized SQL persistence + asynchronous WebSocket push via BackgroundTasks.
  * Standardized module title prefix: 'DMS - <Event Name>'.
  * Standard UTC datetime handling and silent/structured logging.
  * Fail-safe isolation (notification errors NEVER roll back the caller's transaction).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any, List, Optional, Set, Tuple, Union

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from app.core.Websocket import manager

logger = logging.getLogger(__name__)

DMS_MODULE_NAME = "dms"


# =========================================================================
# SECTION 1 — USER RESOLUTION HELPERS
# =========================================================================

def _resolve_user_info(
    db: Session, user_identifier: Optional[Union[int, str]]
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Safely resolves (username, email, display_name) from either user_id (int) or username (str).
    Uses raw SQL query to guarantee zero ORM relationship/mapper conflicts.
    """
    if not user_identifier:
        return None, None, None

    try:
        row = None
        if isinstance(user_identifier, int) or (
            isinstance(user_identifier, str) and str(user_identifier).isdigit()
        ):
            uid = int(user_identifier)
            row = db.execute(
                text("""
                    SELECT username, email, first_name, last_name
                    FROM users
                    WHERE user_id = :uid AND (is_deleted = FALSE OR is_deleted IS NULL)
                """),
                {"uid": uid}
            ).mappings().first()
        elif isinstance(user_identifier, str):
            row = db.execute(
                text("""
                    SELECT username, email, first_name, last_name
                    FROM users
                    WHERE username = :uname AND (is_deleted = FALSE OR is_deleted IS NULL)
                """),
                {"uname": user_identifier}
            ).mappings().first()

        if row:
            first = row.get("first_name") or ""
            last = row.get("last_name") or ""
            full_name = f"{first} {last}".strip() or row.get("username")
            return row.get("username"), row.get("email"), full_name
    except Exception as err:
        logger.debug("[dms_notification] _resolve_user_info failed for %s: %s", user_identifier, err)

    return None, None, None


def _get_display_name(db: Session, user_identifier: Optional[Union[int, str]]) -> str:
    """Returns human-friendly display name, username, or fallback 'System'."""
    _, _, full_name = _resolve_user_info(db, user_identifier)
    if full_name:
        return full_name
    if user_identifier:
        return str(user_identifier)
    return "System"


# =========================================================================
# SECTION 2 — CORE DISPATCH ENGINE
# =========================================================================

def send_dms_notification(
    db: Session,
    to_user: Union[int, str],
    from_user: Optional[Union[int, str]],
    title: str,
    description: str,
    module_status: str,
    notif_type: str = "Document",
    reference_id: Optional[Union[int, str]] = None,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Optional[dict]:
    """
    Core Dispatch Engine for DMS:
      1. Resolves recipient username for WebSocket routing.
      2. Enforces 1-minute deduplication window.
      3. Synchronous PostgreSQL persistence with redirect_url = None.
      4. Asynchronous WebSocket push (BackgroundTasks or asyncio task fallback).
      5. Zero email/SMTP calls.
      6. Isolated try/except so notification failure never aborts the caller transaction.
    """
    if not to_user:
        return None

    to_username, _, _ = _resolve_user_info(db, to_user)
    ws_recipient_key = to_username or str(to_user)
    from_display = _get_display_name(db, from_user)

    # 1. Deduplication guard (1-minute window)
    one_minute_ago = datetime.now() - timedelta(minutes=1)
    ref_str = str(reference_id) if reference_id is not None else None

    try:
        dup = db.execute(
            text("""
                SELECT id FROM notifications
                WHERE module_name = :mod_name
                  AND to_user = :to_user
                  AND module_status = :mod_status
                  AND ((:ref_id IS NULL AND reference_id IS NULL) OR reference_id = :ref_id)
                  AND date >= :one_min_ago
                LIMIT 1
            """),
            {
                "mod_name": DMS_MODULE_NAME,
                "to_user": ws_recipient_key,
                "mod_status": str(module_status),
                "ref_id": ref_str,
                "one_min_ago": one_minute_ago,
            }
        ).scalar()
        if dup:
            logger.debug(
                "[dms_notification] Suppressing duplicate notification for '%s' (ref: %s, status: %s)",
                ws_recipient_key, ref_str, module_status
            )
            return {"id": dup, "status": "duplicate_suppressed"}
    except Exception as exc:
        logger.debug("[dms_notification] Deduplication check failed: %s", exc)

    # 2. Database Persistence via Parameterized SQL (Bulletproof & Fast)
    notif_id = None
    notif_date = datetime.now()
    try:
        row = db.execute(
            text("""
                INSERT INTO notifications (
                    module_name,
                    module_status,
                    type,
                    title,
                    description,
                    from_user,
                    to_user,
                    reference_id,
                    date,
                    is_read,
                    redirect_url
                )
                VALUES (
                    :module_name,
                    :module_status,
                    :type,
                    :title,
                    :description,
                    :from_user,
                    :to_user,
                    :reference_id,
                    NOW(),
                    FALSE,
                    NULL
                )
                RETURNING id, date
            """),
            {
                "module_name": DMS_MODULE_NAME,
                "module_status": str(module_status),
                "type": str(notif_type),
                "title": str(title),
                "description": str(description),
                "from_user": from_display,
                "to_user": ws_recipient_key,
                "reference_id": ref_str,
            }
        ).mappings().first()
        db.commit()
        if row:
            notif_id = row["id"]
            notif_date = row.get("date") or notif_date
    except Exception as exc:
        db.rollback()
        logger.error("[dms_notification] DB persistence failed for recipient '%s': %s", ws_recipient_key, exc)
        return None

    # 3. Real-time WebSocket Push (NO EMAIL)
    ws_payload = {
        "id": notif_id,
        "module_name": DMS_MODULE_NAME,
        "module_status": str(module_status),
        "type": str(notif_type),
        "title": str(title),
        "description": str(description),
        "from_user": from_display,
        "to_user": ws_recipient_key,
        "reference_id": ref_str,
        "date": str(notif_date),
        "redirect_url": None,
    }

    if background_tasks is not None:
        background_tasks.add_task(manager.send_personal_message, ws_recipient_key, ws_payload)
    else:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(manager.send_personal_message(ws_recipient_key, ws_payload))
        except RuntimeError:
            pass  # No running event loop in thread; DB record is safely persisted

    logger.debug("[dms_notification] Dispatched notification to '%s' (status: %s, ref: %s)", ws_recipient_key, module_status, ref_str)
    return {"id": notif_id, "to_user": ws_recipient_key, "title": title}


# =========================================================================
# SECTION 3 — ENTITY RESOLUTION HELPERS
# =========================================================================

def _get_document_meta(db: Session, document_id: int) -> dict:
    """Fetches core document metadata for notification formatting."""
    try:
        row = db.execute(
            text("""
                SELECT
                    d.document_id,
                    d.document_title,
                    d.document_number,
                    d.folder_id,
                    d.sub_folder_id,
                    d.custodian_id,
                    d.created_by,
                    d.close_date,
                    f.folder_name
                FROM dms_documents d
                LEFT JOIN dms_folders f ON f.folder_id = d.folder_id
                WHERE d.document_id = :doc_id
            """),
            {"doc_id": document_id}
        ).mappings().first()
        return dict(row) if row else {}
    except Exception as exc:
        logger.debug("[dms_notification] _get_document_meta failed: %s", exc)
        return {}


def _get_folder_publishers(db: Session, folder_id: Optional[int], sub_folder_id: Optional[int] = None) -> List[int]:
    """
    Returns user_ids of active publishers assigned to the given folder or subfolder.
    """
    publisher_user_ids: Set[int] = set()
    try:
        rows = db.execute(
            text("""
                SELECT publisher_user_id, assigned_folders, assigned_subfolders
                FROM dms_publishers
                WHERE is_deleted = FALSE
                  AND (status IS NULL OR UPPER(status) = 'ACTIVE')
            """)
        ).mappings().all()

        for r in rows:
            uid = r.get("publisher_user_id")
            if not uid:
                continue

            # Check primary folder assignment
            assigned_f = r.get("assigned_folders") or []
            if folder_id:
                if folder_id in assigned_f or str(folder_id) in [str(x) for x in assigned_f]:
                    publisher_user_ids.add(uid)
                    continue

            # Check subfolder assignment
            assigned_sf = r.get("assigned_subfolders") or []
            if sub_folder_id:
                if sub_folder_id in assigned_sf or str(sub_folder_id) in [str(x) for x in assigned_sf]:
                    publisher_user_ids.add(uid)
    except Exception as exc:
        logger.debug("[dms_notification] _get_folder_publishers failed: %s", exc)

    return list(publisher_user_ids)


def _get_document_approved_users(db: Session, document_id: int) -> List[int]:
    """
    Returns user_ids of all users holding an active approved access request for this document.
    """
    try:
        rows = db.execute(
            text("""
                SELECT DISTINCT requester_id
                FROM dms_access_requests
                WHERE document_id = :doc_id
                  AND UPPER(status) = 'APPROVED'
                  AND is_deleted = FALSE
                  AND (access_end_date IS NULL OR access_end_date >= CURRENT_DATE)
            """),
            {"doc_id": document_id}
        ).scalars().all()
        return [uid for uid in rows if uid]
    except Exception as exc:
        logger.debug("[dms_notification] _get_document_approved_users failed: %s", exc)
        return []


# =========================================================================
# SECTION 4 — SPECIALIZED DMS NOTIFICATION DISPATCHERS
# =========================================================================

# -------------------------------------------------------------------------
# 4.1 ACCESS REQUESTS
# -------------------------------------------------------------------------

def notify_access_request_submitted(
    db: Session,
    request_id: int,
    requester_id: int,
    document_id: int,
    reason: Optional[str] = None,
    background_tasks: Optional[BackgroundTasks] = None,
):
    """
    Called after an access request is submitted.
    Notifies Document Custodian and active Folder Publishers.
    """
    doc = _get_document_meta(db, document_id)
    doc_title = doc.get("document_title") or f"Document #{document_id}"
    doc_number = doc.get("document_number") or ""
    custodian_id = doc.get("custodian_id")
    folder_id = doc.get("folder_id")
    sub_folder_id = doc.get("sub_folder_id")

    requester_name = _get_display_name(db, requester_id)
    desc_suffix = f" Reason: {reason}" if reason else ""
    title = "DMS - Access Request Submitted"
    doc_label = f"'{doc_title}' ({doc_number})" if doc_number else f"'{doc_title}'"
    description = f"{requester_name} requested access to {doc_label}.{desc_suffix}"

    recipients: Set[int] = set()
    if custodian_id and custodian_id != requester_id:
        recipients.add(custodian_id)

    publishers = _get_folder_publishers(db, folder_id, sub_folder_id)
    for pub_uid in publishers:
        if pub_uid != requester_id:
            recipients.add(pub_uid)

    for uid in recipients:
        send_dms_notification(
            db=db,
            to_user=uid,
            from_user=requester_id,
            title=title,
            description=description,
            module_status="PENDING",
            notif_type="Access Request",
            reference_id=request_id,
            background_tasks=background_tasks,
        )


def notify_access_request_action(
    db: Session,
    request_id: int,
    action: str,
    action_by: Optional[int],
    remarks: Optional[str] = None,
    access_end_date: Optional[Any] = None,
    background_tasks: Optional[BackgroundTasks] = None,
):
    """
    Called after an access request is approved or rejected.
    Notifies the requesting user.
    """
    try:
        req = db.execute(
            text("""
                SELECT requester_id, document_id
                FROM dms_access_requests
                WHERE request_id = :req_id
            """),
            {"req_id": request_id}
        ).mappings().first()
        if not req:
            return

        requester_id = req.get("requester_id")
        document_id = req.get("document_id")
        if not requester_id:
            return

        doc = _get_document_meta(db, document_id) if document_id else {}
        doc_title = doc.get("document_title") or (f"Document #{document_id}" if document_id else "the document")
        actor_name = _get_display_name(db, action_by)
        is_approved = str(action).upper().strip() in ("APPROVE", "APPROVED")

        if is_approved:
            title = "DMS - Access Request Approved"
            valid_until = f" Valid until {access_end_date}." if access_end_date else " Valid with ongoing access."
            description = f"Your access request for '{doc_title}' has been approved by {actor_name}.{valid_until}"
            status_val = "APPROVED"
        else:
            title = "DMS - Access Request Rejected"
            rem_str = f" Remarks: {remarks}" if remarks else ""
            description = f"Your access request for '{doc_title}' was rejected by {actor_name}.{rem_str}"
            status_val = "REJECTED"

        send_dms_notification(
            db=db,
            to_user=requester_id,
            from_user=action_by,
            title=title,
            description=description,
            module_status=status_val,
            notif_type="Access Request",
            reference_id=request_id,
            background_tasks=background_tasks,
        )
    except Exception as exc:
        logger.debug("[dms_notification] notify_access_request_action failed: %s", exc)


def notify_access_request_expired(
    db: Session,
    request_id: int,
    requester_id: int,
    document_id: int,
    valid_to: Optional[Any] = None,
    background_tasks: Optional[BackgroundTasks] = None,
):
    """
    Called when an access request passes its valid_to date.
    Notifies the requester.
    """
    doc = _get_document_meta(db, document_id)
    doc_title = doc.get("document_title") or f"Document #{document_id}"
    doc_number = doc.get("document_number") or ""
    doc_label = f"'{doc_title}' ({doc_number})" if doc_number else f"'{doc_title}'"

    title = "DMS - Access Request Expired"
    ended_str = f" as the validity period ended on {valid_to}" if valid_to else ""
    description = f"Your temporary access to document {doc_label} has expired{ended_str}."

    send_dms_notification(
        db=db,
        to_user=requester_id,
        from_user="System",
        title=title,
        description=description,
        module_status="EXPIRED",
        notif_type="Access Request",
        reference_id=request_id,
        background_tasks=background_tasks,
    )


# -------------------------------------------------------------------------
# 4.2 DOCUMENT LIFECYCLE
# -------------------------------------------------------------------------

def notify_document_created(
    db: Session,
    document_id: int,
    creator_id: Optional[int],
    background_tasks: Optional[BackgroundTasks] = None,
):
    """
    Called after a new document is published in DMS.
    Notifies Custodian (if different from creator) and Folder Publishers.
    """
    doc = _get_document_meta(db, document_id)
    doc_title = doc.get("document_title") or f"Document #{document_id}"
    folder_name = doc.get("folder_name") or "Primary Folder"
    custodian_id = doc.get("custodian_id")
    folder_id = doc.get("folder_id")
    sub_folder_id = doc.get("sub_folder_id")

    creator_name = _get_display_name(db, creator_id)
    title = "DMS - New Document Published"
    description = f"{creator_name} published a new document '{doc_title}' in folder '{folder_name}'."

    recipients: Set[int] = set()
    if custodian_id and custodian_id != creator_id:
        recipients.add(custodian_id)

    publishers = _get_folder_publishers(db, folder_id, sub_folder_id)
    for pub_uid in publishers:
        if pub_uid != creator_id:
            recipients.add(pub_uid)

    for uid in recipients:
        send_dms_notification(
            db=db,
            to_user=uid,
            from_user=creator_id,
            title=title,
            description=description,
            module_status="ACTIVE",
            notif_type="Document",
            reference_id=document_id,
            background_tasks=background_tasks,
        )


def notify_document_revision(
    db: Session,
    document_id: int,
    revision_number: Union[int, str],
    actor_id: Optional[int],
    background_tasks: Optional[BackgroundTasks] = None,
):
    """
    Called after a new revision of an existing document is uploaded.
    Notifies:
      1. All users with active approved access to this document.
      2. Document Custodian.
      3. Active Folder Publishers.
    """
    doc = _get_document_meta(db, document_id)
    doc_title = doc.get("document_title") or f"Document #{document_id}"
    custodian_id = doc.get("custodian_id")
    folder_id = doc.get("folder_id")
    sub_folder_id = doc.get("sub_folder_id")

    actor_name = _get_display_name(db, actor_id)
    title = "DMS - Document Revised"
    description = f"A new revision (Rev {revision_number}) for '{doc_title}' was uploaded by {actor_name}."

    recipients: Set[int] = set()
    if custodian_id and custodian_id != actor_id:
        recipients.add(custodian_id)

    publishers = _get_folder_publishers(db, folder_id, sub_folder_id)
    for pub_uid in publishers:
        if pub_uid != actor_id:
            recipients.add(pub_uid)

    approved_users = _get_document_approved_users(db, document_id)
    for app_uid in approved_users:
        if app_uid != actor_id:
            recipients.add(app_uid)

    for uid in recipients:
        send_dms_notification(
            db=db,
            to_user=uid,
            from_user=actor_id,
            title=title,
            description=description,
            module_status="REVISED",
            notif_type="Document",
            reference_id=document_id,
            background_tasks=background_tasks,
        )


def notify_document_status_change(
    db: Session,
    document_id: int,
    new_status: str,
    actor_id: Optional[int],
    background_tasks: Optional[BackgroundTasks] = None,
):
    """
    Called when a document's status transitions to ARCHIVED or from ARCHIVED to ACTIVE.
    Notifies the document creator and custodian.
    """
    doc = _get_document_meta(db, document_id)
    doc_title = doc.get("document_title") or f"Document #{document_id}"
    doc_number = doc.get("document_number") or ""
    doc_label = f"'{doc_title}' ({doc_number})" if doc_number else f"'{doc_title}'"
    creator_id = doc.get("created_by")
    custodian_id = doc.get("custodian_id")

    actor_name = _get_display_name(db, actor_id)
    status_upper = str(new_status).upper().strip()

    if status_upper == "ARCHIVED":
        title = "DMS - Document Archived"
        description = f"Document {doc_label} has been archived by {actor_name}."
    elif status_upper == "ACTIVE":
        title = "DMS - Document Restored"
        description = f"Archived document {doc_label} has been restored to Active by {actor_name}."
    else:
        return

    recipients: Set[int] = set()
    if creator_id and creator_id != actor_id:
        recipients.add(creator_id)
    if custodian_id and custodian_id != actor_id:
        recipients.add(custodian_id)

    for uid in recipients:
        send_dms_notification(
            db=db,
            to_user=uid,
            from_user=actor_id,
            title=title,
            description=description,
            module_status=status_upper,
            notif_type="Document",
            reference_id=document_id,
            background_tasks=background_tasks,
        )


# -------------------------------------------------------------------------
# 4.3 PUBLISHER ASSIGNMENT
# -------------------------------------------------------------------------

def notify_publisher_assigned(
    db: Session,
    publisher_user_id: int,
    assigned_folders: Optional[List[Any]],
    actor_id: Optional[int],
    background_tasks: Optional[BackgroundTasks] = None,
):
    """
    Called after a user is appointed or updated as a Folder Publisher.
    Notifies the appointed user.
    """
    if not publisher_user_id or publisher_user_id == actor_id:
        return

    actor_name = _get_display_name(db, actor_id)
    folders_count = len(assigned_folders) if assigned_folders else 0
    folders_summary = f"{folders_count} folder(s)" if folders_count else "DMS folders"

    title = "DMS - Publisher Access Granted"
    description = f"You have been granted folder publisher permissions for {folders_summary} by {actor_name}."

    send_dms_notification(
        db=db,
        to_user=publisher_user_id,
        from_user=actor_id,
        title=title,
        description=description,
        module_status="ASSIGNED",
        notif_type="Publisher",
        reference_id=publisher_user_id,
        background_tasks=background_tasks,
    )


def notify_document_expired(
    db: Session,
    document_id: int,
    background_tasks: Optional[BackgroundTasks] = None,
):
    """
    Called when a document's validity period (close_date) expires.
    Notifies the Document Custodian and Document Creator.
    """
    doc = _get_document_meta(db, document_id)
    doc_title = doc.get("document_title") or f"Document #{document_id}"
    doc_number = doc.get("document_number") or ""
    doc_label = f"'{doc_title}' ({doc_number})" if doc_number else f"'{doc_title}'"
    custodian_id = doc.get("custodian_id")
    creator_id = doc.get("created_by")

    close_date = doc.get("close_date")
    ended_str = f"ended on {close_date}" if close_date else "ended"
    title = "DMS - Document Validity Expired"
    description = f"Document {doc_label} has expired as its validity {ended_str}. Please review for renewal or archiving."

    recipients: Set[int] = set()
    if custodian_id:
        recipients.add(custodian_id)
    if creator_id:
        recipients.add(creator_id)

    for uid in recipients:
        send_dms_notification(
            db=db,
            to_user=uid,
            from_user="System",
            title=title,
            description=description,
            module_status="EXPIRED",
            notif_type="Document",
            reference_id=document_id,
            background_tasks=background_tasks,
        )

