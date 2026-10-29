import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from app.models.dms.dms_chat_thread import DmsChatThread
from app.models.dms.dms_chat_thread_history import DmsChatThreadHistory
from app.models.dms.dms_chat_message import DmsChatMessage
from app.models.dms.dms_chat_message_history import DmsChatMessageHistory
from app.models.dms.dms_document_ocr import DmsDocumentOcr
from app.crud.dms.dms_auth import is_user_dms_admin, get_user_dms_folder_access
from app.crud.dms.dms_ocr_crud import verify_user_document_access, process_document_ocr
from app.utils.time_utils import to_iso_ist, IST
from app.services.dms.document_ocr_service import chunk_text
from app.services.dms.llm_provider_service import generate_grounded_answer, generate_document_summary

logger = logging.getLogger(__name__)


# -------------------------------------------------
# HISTORY AUDIT LOGGING HELPERS
# -------------------------------------------------
def log_thread_history(db: Session, thread: DmsChatThread) -> None:
    """Inserts a historical snapshot of thread into dms_chat_threads_history."""
    try:
        hist = DmsChatThreadHistory(
            thread_id=thread.thread_id,
            user_id=thread.user_id,
            thread_title=thread.thread_title,
            document_id=thread.document_id,
            is_deleted=thread.is_deleted,
            created_at=thread.created_at,
            created_by=thread.created_by,
            updated_at=thread.updated_at,
            updated_by=thread.updated_by
        )
        db.add(hist)
        db.flush()
    except Exception as e:
        logger.warning("Failed to log thread history for thread_id %s: %s", thread.thread_id, e)


def log_message_history(db: Session, msg: DmsChatMessage) -> None:
    """Inserts a historical snapshot of message into dms_chat_messages_history."""
    try:
        hist = DmsChatMessageHistory(
            message_id=msg.message_id,
            thread_id=msg.thread_id,
            sender=msg.sender,
            content=msg.content,
            document_references=msg.document_references,
            model_used=msg.model_used,
            tokens_used=msg.tokens_used,
            is_deleted=msg.is_deleted,
            created_at=msg.created_at,
            created_by=msg.created_by,
            updated_at=msg.updated_at,
            updated_by=msg.updated_by
        )
        db.add(hist)
        db.flush()
    except Exception as e:
        logger.warning("Failed to log message history for message_id %s: %s", msg.message_id, e)


# -------------------------------------------------
# THREAD OPERATIONS
# -------------------------------------------------
def create_chat_thread(
    db: Session,
    user_id: int,
    thread_title: Optional[str] = "New Chat",
    document_id: Optional[int] = None
) -> Dict[str, Any]:
    """Creates a new DMS chat thread with optional document attachment."""
    doc_title = None
    doc_number = None

    if document_id:
        doc = verify_user_document_access(db, user_id, document_id)
        doc_title = doc.get("document_title")
        doc_number = doc.get("document_number")
        if not thread_title or thread_title == "New Chat":
            thread_title = f"Chat: {doc_title[:30]}" if doc_title else f"Chat: Doc #{document_id}"

    title = thread_title.strip() if thread_title and thread_title.strip() else "New Chat"

    thread = DmsChatThread(
        user_id=user_id,
        thread_title=title,
        document_id=document_id,
        created_by=user_id
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)

    log_thread_history(db, thread)
    db.commit()

    return {
        "thread_id": thread.thread_id,
        "user_id": thread.user_id,
        "thread_title": thread.thread_title,
        "document_id": thread.document_id,
        "document_title": doc_title,
        "document_number": doc_number,
        "message_count": 0,
        "last_message": None,
        "created_at": to_iso_ist(thread.created_at),
        "updated_at": to_iso_ist(thread.updated_at)
    }


def get_user_chat_threads(
    db: Session,
    user_id: int,
    document_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Lists all active chat threads belonging to user, ordered by most recently active."""
    query = text("""
        SELECT 
            t.thread_id,
            t.user_id,
            t.thread_title,
            t.document_id,
            t.created_at,
            t.updated_at,
            d.document_title,
            d.document_number,
            COUNT(m.message_id) AS message_count,
            (
                SELECT m_last.content 
                FROM dms_chat_messages m_last 
                WHERE m_last.thread_id = t.thread_id 
                  AND (m_last.is_deleted = FALSE OR m_last.is_deleted IS NULL)
                ORDER BY m_last.message_id DESC 
                LIMIT 1
            ) AS last_message
        FROM dms_chat_threads t
        LEFT JOIN dms_documents d ON d.document_id = t.document_id
        LEFT JOIN dms_chat_messages m ON m.thread_id = t.thread_id AND (m.is_deleted = FALSE OR m.is_deleted IS NULL)
        WHERE t.user_id = :uid 
          AND (t.is_deleted = FALSE OR t.is_deleted IS NULL)
          AND (:doc_id IS NULL OR t.document_id = :doc_id)
        GROUP BY t.thread_id, t.user_id, t.thread_title, t.document_id, t.created_at, t.updated_at, d.document_title, d.document_number
        ORDER BY COALESCE(t.updated_at, t.created_at) DESC
    """)

    rows = db.execute(query, {"uid": user_id, "doc_id": document_id}).mappings().all()

    threads = []
    for r in rows:
        threads.append({
            "thread_id": r["thread_id"],
            "user_id": r["user_id"],
            "thread_title": r["thread_title"],
            "document_id": r["document_id"],
            "document_title": r["document_title"],
            "document_number": r["document_number"],
            "message_count": int(r["message_count"] or 0),
            "last_message": r["last_message"],
            "created_at": to_iso_ist(r["created_at"]),
            "updated_at": to_iso_ist(r["updated_at"])
        })
    return threads


def delete_chat_thread(db: Session, thread_id: int, user_id: int) -> bool:
    """Soft deletes chat thread and its messages."""
    thread = db.query(DmsChatThread).filter(
        DmsChatThread.thread_id == thread_id,
        DmsChatThread.is_deleted == False
    ).first()

    if not thread:
        raise HTTPException(status_code=404, detail="Chat thread not found.")

    if thread.user_id != user_id and not is_user_dms_admin(db, user_id):
        raise HTTPException(status_code=403, detail="Permission denied: You do not own this chat thread.")

    thread.is_deleted = True
    thread.updated_by = user_id
    thread.updated_at = func.now()

    # Soft delete related messages
    db.query(DmsChatMessage).filter(
        DmsChatMessage.thread_id == thread_id,
        DmsChatMessage.is_deleted == False
    ).update({"is_deleted": True, "updated_by": user_id, "updated_at": func.now()}, synchronize_session=False)

    db.commit()
    db.refresh(thread)

    log_thread_history(db, thread)
    db.commit()
    return True


def get_thread_messages(db: Session, thread_id: int, user_id: int) -> List[Dict[str, Any]]:
    """Loads all chat messages for a thread."""
    thread = db.query(DmsChatThread).filter(
        DmsChatThread.thread_id == thread_id,
        DmsChatThread.is_deleted == False
    ).first()

    if not thread:
        raise HTTPException(status_code=404, detail="Chat thread not found.")

    if thread.user_id != user_id and not is_user_dms_admin(db, user_id):
        raise HTTPException(status_code=403, detail="Permission denied: You do not have access to this chat thread.")

    messages = db.query(DmsChatMessage).filter(
        DmsChatMessage.thread_id == thread_id,
        DmsChatMessage.is_deleted == False
    ).order_by(DmsChatMessage.message_id.asc()).all()

    results = []
    for m in messages:
        results.append({
            "message_id": m.message_id,
            "thread_id": m.thread_id,
            "sender": m.sender,
            "content": m.content,
            "document_references": m.document_references,
            "model_used": m.model_used,
            "tokens_used": m.tokens_used,
            "created_at": to_iso_ist(m.created_at)
        })
    return results


# -------------------------------------------------
# CONTEXT RETRIEVAL FOR GROUNDED CHAT
# -------------------------------------------------
def get_authorized_document_context(
    db: Session,
    user_id: int,
    question: str,
    target_doc_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    sub_folder_id: Optional[int] = None,
    sub_sub_folder_id: Optional[int] = None,
    max_chunks: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieves authorized document chunks relevant to the user query.
    Enforces strict access control:
      - If target_doc_id is provided, validates access and returns its text chunks.
      - If folder_id/sub_folder_id/sub_sub_folder_id or general query, filters only documents the user is allowed to access.
    Access levels (checked in priority order):
      1. Admin → all documents
      2. Author (created_by) → their own uploaded documents
      3. Custodian → documents they are custodian of
      4. Publisher with folder/subfolder assignment → documents in assigned folders/subfolders/sub-sub-folders
      5. Individual engineer / custody_list inclusion → specific documents granted
      6. Approved access requests → specific documents with approved request
    """
    candidate_doc_ids: List[int] = []

    if target_doc_id:
        # Access check for specific document — raises 403/404 if not allowed
        verify_user_document_access(db, user_id, target_doc_id)
        candidate_doc_ids = [target_doc_id]
    else:
        is_admin = is_user_dms_admin(db, user_id)

        if is_admin:
            # Admin sees all documents
            doc_query = text("""
                SELECT document_id FROM dms_documents
                WHERE (is_deleted = FALSE OR is_deleted IS NULL)
                  AND (:fid IS NULL OR folder_id = :fid)
                  AND (:sfid IS NULL OR sub_folder_id = :sfid OR sub_sub_folder_id = :sfid)
                  AND (:ssfid IS NULL OR sub_sub_folder_id = :ssfid)
                LIMIT 50
            """)
            rows = db.execute(doc_query, {
                "fid": folder_id,
                "sfid": sub_folder_id,
                "ssfid": sub_sub_folder_id
            }).mappings().all()
            candidate_doc_ids = [r["document_id"] for r in rows]
        else:
            # Non-admin: resolve folder + subfolder access
            is_unrestricted, allowed_folders, allowed_subfolders = get_user_dms_folder_access(db, user_id)

            # Build folder and subfolder filter lists
            folder_list: List[int] = []
            subfolder_list: List[int] = []

            if is_unrestricted:
                # Publisher/engineer with unrestricted folder access — fetch all docs like admin
                doc_query = text("""
                    SELECT document_id FROM dms_documents
                    WHERE (is_deleted = FALSE OR is_deleted IS NULL)
                      AND (:fid IS NULL OR folder_id = :fid)
                      AND (:sfid IS NULL OR sub_folder_id = :sfid OR sub_sub_folder_id = :sfid)
                      AND (:ssfid IS NULL OR sub_sub_folder_id = :ssfid)
                    LIMIT 50
                """)
                rows = db.execute(doc_query, {
                    "fid": folder_id,
                    "sfid": sub_folder_id,
                    "ssfid": sub_sub_folder_id
                }).mappings().all()
                candidate_doc_ids = [r["document_id"] for r in rows]
            else:
                folder_list = list(allowed_folders or set())
                subfolder_list = list(allowed_subfolders or set())

                # Build access condition:
                # user is author OR custodian OR document is in an allowed folder OR allowed subfolder/sub-sub-folder
                doc_query = text("""
                    SELECT document_id FROM dms_documents
                    WHERE (is_deleted = FALSE OR is_deleted IS NULL)
                      AND (
                        created_by = :uid
                        OR custodian_id = :uid
                        OR (folder_id = ANY(:f_list))
                        OR (sub_folder_id IS NOT NULL AND sub_folder_id = ANY(:sf_list))
                        OR (sub_sub_folder_id IS NOT NULL AND sub_sub_folder_id = ANY(:sf_list))
                      )
                      AND (:fid IS NULL OR folder_id = :fid)
                      AND (:sfid IS NULL OR sub_folder_id = :sfid OR sub_sub_folder_id = :sfid)
                      AND (:ssfid IS NULL OR sub_sub_folder_id = :ssfid)
                    LIMIT 50
                """)
                rows = db.execute(doc_query, {
                    "uid": user_id,
                    "f_list": folder_list if folder_list else [-1],
                    "sf_list": subfolder_list if subfolder_list else [-1],
                    "fid": folder_id,
                    "sfid": sub_folder_id,
                    "ssfid": sub_sub_folder_id
                }).mappings().all()
                candidate_doc_ids = [r["document_id"] for r in rows]

                # Also include documents granted via individual_engineer / custody_list / approved requests
                extra_doc_query = text("""
                    SELECT d.document_id FROM dms_documents d
                    WHERE (d.is_deleted = FALSE OR d.is_deleted IS NULL)
                      AND d.document_id NOT IN :excluded_ids
                      AND (
                        EXISTS (
                            SELECT 1 FROM dms_access_requests ar
                            WHERE ar.requester_id = :uid AND ar.document_id = d.document_id
                              AND UPPER(ar.status) = 'APPROVED'
                              AND (ar.valid_to IS NULL OR ar.valid_to >= CURRENT_DATE)
                              AND (ar.valid_from IS NULL OR ar.valid_from <= CURRENT_DATE)
                              AND (ar.is_deleted = FALSE OR ar.is_deleted IS NULL)
                        )
                      )
                    LIMIT 20
                """)
                if candidate_doc_ids:
                    extra_rows = db.execute(extra_doc_query, {
                        "uid": user_id,
                        "excluded_ids": tuple(candidate_doc_ids)
                    }).mappings().all()
                else:
                    extra_rows = []

                for r in extra_rows:
                    candidate_doc_ids.append(r["document_id"])

    if not candidate_doc_ids:
        return []

    # Fetch OCR extracted texts for candidate documents
    ocr_rows = db.query(
        DmsDocumentOcr.document_id,
        DmsDocumentOcr.extracted_text,
        DmsDocumentOcr.ocr_status
    ).filter(
        DmsDocumentOcr.document_id.in_(candidate_doc_ids),
        DmsDocumentOcr.is_deleted == False
    ).all()

    # Map existing OCR
    ocr_map = {row.document_id: row for row in ocr_rows}

    # If target_doc_id was specified and not yet OCR'd or had a binary placeholder, auto-process it on demand
    target_needs_reprocess = (
        target_doc_id
        and (
            target_doc_id not in ocr_map
            or ocr_map[target_doc_id].ocr_status != "COMPLETED"
            or not ocr_map[target_doc_id].extracted_text
            or (ocr_map[target_doc_id].extracted_text or "").startswith("[Binary file")
            or (ocr_map[target_doc_id].extracted_text or "").startswith("[Unsupported file")
        )
    )
    if target_needs_reprocess:
        try:
            logger.info("Auto-processing OCR for document %s during chat...", target_doc_id)
            process_document_ocr(db, target_doc_id, user_id, force_reprocess=True)
            refreshed = db.query(DmsDocumentOcr).filter(
                DmsDocumentOcr.document_id == target_doc_id,
                DmsDocumentOcr.is_deleted == False
            ).first()
            if refreshed:
                ocr_map[target_doc_id] = refreshed
        except Exception as e:
            logger.warning("Could not auto-process OCR for document %s: %s", target_doc_id, e)

    # Fetch document titles & numbers
    doc_info_query = text("""
        SELECT document_id, document_title, document_number
        FROM dms_documents
        WHERE document_id = ANY(:d_ids)
    """)
    doc_info_rows = db.execute(doc_info_query, {"d_ids": candidate_doc_ids}).mappings().all()
    doc_info_map = {r["document_id"]: r for r in doc_info_rows}

    # Simple keyword scoring for chunk retrieval
    query_terms = [w.lower() for w in question.split() if len(w) > 3]

    all_scored_chunks: List[Dict[str, Any]] = []

    for doc_id, ocr_entry in ocr_map.items():
        text_content = ocr_entry.extracted_text
        if not text_content or ocr_entry.ocr_status != "COMPLETED":
            continue

        # Ignore raw binary data if present
        if "IHDR" in text_content or "PNG\n" in text_content or "IDAT" in text_content:
            continue

        doc_meta = doc_info_map.get(doc_id, {})
        chunks = chunk_text(text_content, chunk_size=800, overlap=100)

        for c in chunks:
            c_text = c.get("text", "")
            if not c_text or "IHDR" in c_text or "PNG\n" in c_text or "IDAT" in c_text:
                continue

            # Score chunk by keyword relevance
            score = 0
            c_lower = c_text.lower()
            for term in query_terms:
                if term in c_lower:
                    score += 1

            all_scored_chunks.append({
                "score": score,
                "document_id": doc_id,
                "document_title": doc_meta.get("document_title") or f"Document #{doc_id}",
                "document_number": doc_meta.get("document_number") or "",
                "page_number": c.get("page_number", 1),
                "text": c_text
            })

    # Sort chunks by relevance score descending, return top chunks
    all_scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return all_scored_chunks[:max_chunks]




# -------------------------------------------------
# SEND CHAT MESSAGE
# -------------------------------------------------
def send_chat_message(
    db: Session,
    user_id: int,
    thread_id: int,
    question: str,
    document_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    sub_folder_id: Optional[int] = None,
    sub_sub_folder_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Submits a user query to Navi, retrieves authorized document context,
    invokes LLM, saves user & assistant messages, and returns assistant reply with citations.
    """
    # 1. Verify thread access
    thread = db.query(DmsChatThread).filter(
        DmsChatThread.thread_id == thread_id,
        DmsChatThread.is_deleted == False
    ).first()

    if not thread:
        raise HTTPException(status_code=404, detail="Chat thread not found.")

    if thread.user_id != user_id and not is_user_dms_admin(db, user_id):
        raise HTTPException(status_code=403, detail="Permission denied: You do not own this chat thread.")

    active_doc_id = document_id or thread.document_id

    # Detect simple greetings / conversational messages that don't need document retrieval
    _GREETING_PHRASES = {
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
        "greetings", "howdy", "thanks", "thank you", "ok", "okay", "bye",
        "goodbye", "good night", "welcome", "namaste", "hii", "hiii",
        "who are you", "what can you do", "help", "help me",
    }
    _is_greeting = question.strip().lower().rstrip("!?., ") in _GREETING_PHRASES

    # 2. Save User Message
    user_msg = DmsChatMessage(
        thread_id=thread_id,
        sender="user",
        content=question.strip(),
        created_by=user_id
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    log_message_history(db, user_msg)
    db.commit()

    # 3. Retrieve authorized context chunks (skip for simple greetings to avoid wasteful queries)
    if _is_greeting:
        context_chunks = []
    else:
        context_chunks = get_authorized_document_context(
            db=db,
            user_id=user_id,
            question=question,
            target_doc_id=active_doc_id,
            folder_id=folder_id,
            sub_folder_id=sub_folder_id,
            sub_sub_folder_id=sub_sub_folder_id,
            max_chunks=5
        )

    # 4. Fetch recent conversation history
    recent_msgs = db.query(DmsChatMessage).filter(
        DmsChatMessage.thread_id == thread_id,
        DmsChatMessage.is_deleted == False
    ).order_by(DmsChatMessage.message_id.desc()).limit(6).all()

    conv_history = [
        {"sender": m.sender, "content": m.content}
        for m in reversed(recent_msgs)
    ]

    # 5. Generate Grounded AI Answer
    llm_result = generate_grounded_answer(
        question=question,
        context_chunks=context_chunks,
        conversation_history=conv_history
    )

    answer_text = llm_result.get("answer", "")
    citations = llm_result.get("citations", [])
    model_name = llm_result.get("model", "navi-ai")
    tokens_used = llm_result.get("tokens_used", 0)

    # 6. Save Navi Assistant Message
    assistant_msg = DmsChatMessage(
        thread_id=thread_id,
        sender="navi",
        content=answer_text,
        document_references=citations,
        model_used=model_name,
        tokens_used=tokens_used,
        created_by=user_id
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    log_message_history(db, assistant_msg)
    db.commit()

    # 7. Update Thread Title if still "New Chat"
    if thread.thread_title in ["New Chat", ""]:
        words = question.strip().split()
        short_title = " ".join(words[:6])
        if len(short_title) > 50:
            short_title = short_title[:50] + "..."
        thread.thread_title = short_title

    thread.updated_at = func.now()
    thread.updated_by = user_id
    db.commit()
    db.refresh(thread)
    log_thread_history(db, thread)
    db.commit()

    return {
        "message_id": assistant_msg.message_id,
        "thread_id": assistant_msg.thread_id,
        "sender": assistant_msg.sender,
        "content": assistant_msg.content,
        "document_references": assistant_msg.document_references,
        "model_used": assistant_msg.model_used,
        "tokens_used": assistant_msg.tokens_used,
        "created_at": to_iso_ist(assistant_msg.created_at)
    }


# -------------------------------------------------
# SUMMARIZE DOCUMENT
# -------------------------------------------------
def summarize_document(
    db: Session,
    user_id: int,
    document_id: int,
    thread_id: Optional[int] = None,
    summary_type: str = "detailed",
    custom_instructions: Optional[str] = None
) -> Dict[str, Any]:
    """Generates an instant 1-click summary for a document and optionally appends to a chat thread."""
    doc = verify_user_document_access(db, user_id, document_id)
    doc_title = doc.get("document_title") or doc.get("document_number") or f"Document #{document_id}"

    # Check or generate OCR
    ocr_row = db.query(DmsDocumentOcr).filter(
        DmsDocumentOcr.document_id == document_id,
        DmsDocumentOcr.is_deleted == False
    ).first()

    # Check if existing OCR has genuine extracted text and a valid summary
    has_valid_text = (
        ocr_row
        and ocr_row.ocr_status == "COMPLETED"
        and bool(ocr_row.extracted_text)
        and not (ocr_row.extracted_text or "").startswith("[Binary file")
        and not (ocr_row.extracted_text or "").startswith("[Unsupported file")
    )

    has_valid_summary = (
        has_valid_text
        and bool(ocr_row.document_summary)
        and "Navi System Notification" not in (ocr_row.document_summary or "")
        and "has no readable text content to summarize" not in (ocr_row.document_summary or "")
    )

    if not has_valid_text:
        # Run OCR extraction with force_reprocess=True so newly supported formats (Excel, PPT, etc.) re-extract
        ocr_result = process_document_ocr(db, document_id, user_id, force_reprocess=True)
        extracted_text = ocr_result.get("extracted_text")
        page_count = ocr_result.get("page_count", 1)
        summary = ocr_result.get("document_summary")
    else:
        extracted_text = ocr_row.extracted_text
        page_count = ocr_row.page_count

        # If custom type or instructions given, or no valid summary exists, generate summary
        if summary_type != "detailed" or custom_instructions or not has_valid_summary:
            summary = generate_document_summary(
                document_text=extracted_text,
                document_title=doc_title,
                summary_type=summary_type,
                custom_instructions=custom_instructions
            )
            # If summary generated successfully, persist it
            if summary and "Navi System Notification" not in summary:
                ocr_row.document_summary = summary
                db.commit()
        else:
            summary = ocr_row.document_summary

    # If thread_id is provided, record interaction into chat thread
    if thread_id:
        thread = db.query(DmsChatThread).filter(
            DmsChatThread.thread_id == thread_id,
            DmsChatThread.is_deleted == False
        ).first()
        if thread and (thread.user_id == user_id or is_user_dms_admin(db, user_id)):
            # User query message
            user_msg = DmsChatMessage(
                thread_id=thread_id,
                sender="user",
                content=f"Please provide a {summary_type} summary of '{doc_title}'.",
                created_by=user_id
            )
            db.add(user_msg)
            db.commit()
            log_message_history(db, user_msg)

            # Navi response message
            navi_msg = DmsChatMessage(
                thread_id=thread_id,
                sender="navi",
                content=summary,
                document_references=[{
                    "document_id": document_id,
                    "document_title": doc_title,
                    "document_number": doc.get("document_number"),
                    "page_count": page_count,
                    "summary_type": summary_type
                }],
                model_used="navi-summarizer",
                created_by=user_id
            )
            db.add(navi_msg)
            thread.updated_at = func.now()
            thread.updated_by = user_id
            db.commit()
            log_message_history(db, navi_msg)
            log_thread_history(db, thread)
            db.commit()

    return {
        "document_id": document_id,
        "document_title": doc_title,
        "document_number": doc.get("document_number"),
        "page_count": page_count,
        "summary_type": summary_type,
        "summary": summary,
        "thread_id": thread_id,
        "created_at": to_iso_ist(datetime.now(IST))
    }
