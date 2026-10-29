import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dms.dms_ocr_schema import (
    DmsOcrProcessRequest,
    DmsOcrResponse,
    DmsOcrDetails,
)
from app.crud.dms.dms_ocr_crud import process_document_ocr, get_document_ocr
from app.crud.dms.dms_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dms-ocr", tags=["DMS OCR"])


# -------------------------------------------------
# 1. PROCESS DOCUMENT OCR & SUMMARY
# -------------------------------------------------
@router.post(
    "/process/{document_id}",
    response_model=DmsOcrResponse,
    summary="Trigger OCR extraction and AI summary generation for a document"
)
def process_ocr(
    document_id: int,
    payload: Optional[DmsOcrProcessRequest] = None,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Triggers OCR text extraction from the document's physical file (PDF, DOCX, TXT, etc.)
    and invokes the configured LLM (Gemini, OpenAI, Groq, Ollama) to generate a structured summary.
    Saves results to `dms_document_ocr` and logs an entry in `dms_document_ocr_history`.
    """
    uid = current_user_id
    force = payload.force_reprocess if payload else False
    custom_prompt = payload.custom_summary_prompt if payload else None

    try:
        result = process_document_ocr(
            db=db,
            document_id=document_id,
            user_id=uid,
            force_reprocess=force,
            custom_summary_prompt=custom_prompt
        )
        msg = "Document OCR and summary already up to date (cached)" if result.get("is_cached") else "Document OCR and AI summary processed successfully"
        return DmsOcrResponse(
            status="success",
            message=msg,
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed processing OCR for document %s: %s", document_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process OCR for document ID {document_id}: {str(e)}"
        )


# -------------------------------------------------
# 2. GET DOCUMENT OCR STATUS & SUMMARY
# -------------------------------------------------
@router.get(
    "/get/{document_id}",
    response_model=DmsOcrResponse,
    summary="Get OCR extraction status, extracted text, and AI summary for a document"
)
def get_ocr(
    document_id: int,
    include_full_text: bool = Query(True, description="Whether to include full extracted text"),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Retrieves the OCR status, extracted text, AI summary, page count, and metadata
    for the specified document ID. Enforces document viewing permissions.
    """
    uid = current_user_id
    try:
        result = get_document_ocr(
            db=db,
            document_id=document_id,
            user_id=uid,
            include_full_text=include_full_text
        )
        return DmsOcrResponse(
            status="success",
            message="OCR details retrieved successfully",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed fetching OCR for document %s: %s", document_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve OCR details for document ID {document_id}: {str(e)}"
        )
