import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dms.dms_chat_schema import (
    DmsChatThreadCreate,
    DmsChatThreadResponse,
    DmsChatMessageResponse,
    DmsChatSendRequest,
    DmsChatSummarizeRequest,
    DmsChatSummarizeResponse,
    DmsChatEnvelope
)
from app.crud.dms.dms_chat_crud import (
    create_chat_thread,
    get_user_chat_threads,
    delete_chat_thread,
    get_thread_messages,
    send_chat_message,
    summarize_document
)
from app.crud.dms.dms_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dms-chat", tags=["DMS Navi Chatbot"])


# -------------------------------------------------
# 3. CREATE CHAT THREAD
# -------------------------------------------------
@router.post(
    "/thread/create",
    response_model=DmsChatEnvelope,
    summary="Create a new chat thread for Navi"
)
def create_thread(
    payload: Optional[DmsChatThreadCreate] = None,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Creates a new conversation thread for the logged-in user (+ button in Navi UI).
    Optionally associates the thread with a specific document.
    """
    uid = current_user_id
    title = payload.thread_title if payload else "New Chat"
    doc_id = payload.document_id if payload else None

    try:
        thread = create_chat_thread(
            db=db,
            user_id=uid,
            thread_title=title,
            document_id=doc_id
        )
        return DmsChatEnvelope(
            status="success",
            message="Chat thread created successfully",
            data=thread
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create chat thread for user %s: %s", uid, e)
        raise HTTPException(status_code=500, detail=f"Failed to create chat thread: {str(e)}")


# -------------------------------------------------
# 4. GET ALL THREADS FOR USER
# -------------------------------------------------
@router.get(
    "/threads",
    response_model=DmsChatEnvelope,
    summary="List all chat threads for logged-in user"
)
def list_threads(
    document_id: Optional[int] = Query(None, description="Optional filter threads attached to a specific document"),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns all active chat threads belonging to the logged-in user,
    ordered by most recently updated. Includes message counts and last message snippets.
    """
    uid = current_user_id
    try:
        threads = get_user_chat_threads(db=db, user_id=uid, document_id=document_id)
        return DmsChatEnvelope(
            status="success",
            message="Chat threads retrieved successfully",
            data=threads
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to list chat threads for user %s: %s", uid, e)
        raise HTTPException(status_code=500, detail=f"Failed to list chat threads: {str(e)}")


# -------------------------------------------------
# 5. DELETE A CHAT THREAD
# -------------------------------------------------
@router.delete(
    "/thread/{thread_id}",
    response_model=DmsChatEnvelope,
    summary="Delete a chat thread"
)
def delete_thread(
    thread_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Soft-deletes the chat thread and its associated message history.
    """
    uid = current_user_id
    try:
        delete_chat_thread(db=db, thread_id=thread_id, user_id=uid)
        return DmsChatEnvelope(
            status="success",
            message="Chat thread deleted successfully",
            data={"thread_id": thread_id, "is_deleted": True}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete chat thread %s: %s", thread_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to delete chat thread: {str(e)}")


# -------------------------------------------------
# 6. GET THREAD MESSAGE HISTORY
# -------------------------------------------------
@router.get(
    "/thread/{thread_id}/messages",
    response_model=DmsChatEnvelope,
    summary="Load full chat history of a thread"
)
def get_messages(
    thread_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Retrieves all messages in the conversation thread in chronological order.
    Includes document reference citations and model information.
    """
    uid = current_user_id
    try:
        messages = get_thread_messages(db=db, thread_id=thread_id, user_id=uid)
        return DmsChatEnvelope(
            status="success",
            message="Messages loaded successfully",
            data=messages
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to load messages for thread %s: %s", thread_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to load thread messages: {str(e)}")


# -------------------------------------------------
# 7. SEND QUESTION TO NAVI (GROUNDED CHAT)
# -------------------------------------------------
@router.post(
    "/send",
    response_model=DmsChatEnvelope,
    summary="Send question to Navi -> returns answer + document references"
)
def send_message(
    payload: DmsChatSendRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Core grounded chat endpoint.
    Retrieves authorized document extracts matching user permissions,
    invokes configured LLM with conversational context, and returns Navi's grounded answer
    along with clickable document citations.
    """
    uid = current_user_id
    try:
        result = send_chat_message(
            db=db,
            user_id=uid,
            thread_id=payload.thread_id,
            question=payload.question,
            document_id=payload.document_id,
            folder_id=payload.folder_id,
            sub_folder_id=payload.sub_folder_id,
            sub_sub_folder_id=payload.sub_sub_folder_id
        )
        return DmsChatEnvelope(
            status="success",
            message="Response generated successfully",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed generating chat response in thread %s: %s", payload.thread_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")


# -------------------------------------------------
# 8. ONE-CLICK DOCUMENT SUMMARY
# -------------------------------------------------
@router.post(
    "/summarize/{document_id}",
    response_model=DmsChatEnvelope,
    summary="One-click AI summary of any single document"
)
def summarize_doc(
    document_id: int,
    payload: Optional[DmsChatSummarizeRequest] = None,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Generates an instant structured AI summary of the document.
    Optionally records the summary into a chat thread for continued questioning.
    """
    uid = current_user_id
    thread_id = payload.thread_id if payload else None
    summary_type = (payload.summary_type if payload and payload.summary_type else "detailed").lower()
    custom_instructions = payload.custom_instructions if payload else None

    try:
        result = summarize_document(
            db=db,
            user_id=uid,
            document_id=document_id,
            thread_id=thread_id,
            summary_type=summary_type,
            custom_instructions=custom_instructions
        )
        return DmsChatEnvelope(
            status="success",
            message="Document summary generated successfully",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed generating summary for document %s: %s", document_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to generate document summary: {str(e)}")
