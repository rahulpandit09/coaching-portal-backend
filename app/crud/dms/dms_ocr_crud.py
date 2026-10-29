import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.dms.dms_document_ocr import DmsDocumentOcr
from app.models.dms.dms_document_ocr_history import DmsDocumentOcrHistory
from app.crud.dms.dms_auth import is_user_dms_admin, get_user_dms_folder_access
from app.services.dms.document_ocr_service import extract_document_content
from app.services.dms.llm_provider_service import generate_document_summary
from app.utils.time_utils import to_iso_ist, IST

logger = logging.getLogger(__name__)


def verify_user_document_access(db: Session, user_id: Optional[int], document_id: int) -> Dict[str, Any]:
    """
    Verifies that the user has authorization to view or process the given document.
    Adheres strictly to DMS role permissions, publisher assignments, and custodianship.
    Raises HTTPException 404 (not found) or 403 (forbidden).
    Returns document dictionary on success.
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    doc_query = text("""
        SELECT document_id, document_number, document_title, folder_id, sub_folder_id,
               file_path, file_name, file_type, file_size, created_by, custodian_id,
               custody_list, individual_engineer, status, confidential_document
        FROM dms_documents
        WHERE document_id = :doc_id AND (is_deleted = FALSE OR is_deleted IS NULL)
    """)
    doc = db.execute(doc_query, {"doc_id": document_id}).mappings().first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found.")

    doc_dict = dict(doc)

    # 1. Admin has full access
    if is_user_dms_admin(db, user_id):
        return doc_dict

    # 2. Author or Custodian has full access
    if doc_dict.get("created_by") == user_id or doc_dict.get("custodian_id") == user_id:
        return doc_dict

    # 3. Check folder and sub-folder access
    is_unrestricted, allowed_folders, allowed_subfolders = get_user_dms_folder_access(db, user_id)
    if is_unrestricted:
        return doc_dict

    fid = doc_dict.get("folder_id")
    sfid = doc_dict.get("sub_folder_id")
    ssfid = doc_dict.get("sub_sub_folder_id")
    folder_ok = (allowed_folders is not None and fid in allowed_folders)
    subfolder_ok = (
        (sfid is None and ssfid is None)
        or (
            allowed_subfolders is not None
            and (
                (sfid is not None and sfid in allowed_subfolders)
                or (ssfid is not None and ssfid in allowed_subfolders)
            )
        )
    )

    if folder_ok and subfolder_ok:
        return doc_dict

    # 4. Check assigned individual engineers or custody_list
    for field in ["individual_engineer", "custody_list"]:
        raw_val = doc_dict.get(field)
        if raw_val:
            if isinstance(raw_val, str):
                try:
                    raw_val = json.loads(raw_val)
                except Exception:
                    raw_val = []
            if isinstance(raw_val, list):
                for item in raw_val:
                    if str(item) == str(user_id):
                        return doc_dict
                    if isinstance(item, dict) and (str(item.get("user_id")) == str(user_id) or str(item.get("id")) == str(user_id)):
                        return doc_dict

    # 5. Check approved access requests
    req_query = text("""
        SELECT 1 FROM dms_access_requests
        WHERE requester_id = :uid AND document_id = :doc_id AND UPPER(status) = 'APPROVED'
          AND (valid_to IS NULL OR valid_to >= CURRENT_DATE)
          AND (valid_from IS NULL OR valid_from <= CURRENT_DATE)
          AND (is_deleted = FALSE OR is_deleted IS NULL)
        LIMIT 1
    """)
    if db.execute(req_query, {"uid": user_id, "doc_id": document_id}).first() is not None:
        return doc_dict

    raise HTTPException(
        status_code=403,
        detail="Permission denied: You do not have access to view or process this document."
    )


def log_ocr_history(db: Session, ocr_row: DmsDocumentOcr) -> None:
    """Inserts a historical snapshot of the OCR record into dms_document_ocr_history."""
    try:
        hist = DmsDocumentOcrHistory(
            ocr_id=ocr_row.ocr_id,
            document_id=ocr_row.document_id,
            ocr_status=ocr_row.ocr_status,
            extracted_text=ocr_row.extracted_text,
            document_summary=ocr_row.document_summary,
            page_count=ocr_row.page_count,
            metadata_info=ocr_row.metadata_info,
            error_message=ocr_row.error_message,
            is_deleted=ocr_row.is_deleted,
            created_at=ocr_row.created_at,
            created_by=ocr_row.created_by,
            updated_at=ocr_row.updated_at,
            updated_by=ocr_row.updated_by
        )
        db.add(hist)
        db.flush()
    except Exception as e:
        logger.warning("Failed to log OCR history for ocr_id %s: %s", ocr_row.ocr_id, e)


def process_document_ocr(
    db: Session,
    document_id: int,
    user_id: int,
    force_reprocess: bool = False,
    custom_summary_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts text from document physical file and generates AI summary.
    Saves results to dms_document_ocr and logs to dms_document_ocr_history.
    """
    doc = verify_user_document_access(db, user_id, document_id)
    file_path = doc.get("file_path")
    if not file_path:
        raise HTTPException(
            status_code=400,
            detail="Cannot process OCR: Document does not have an attached physical file."
        )

    # Check existing OCR entry
    existing = db.query(DmsDocumentOcr).filter(
        DmsDocumentOcr.document_id == document_id,
        DmsDocumentOcr.is_deleted == False
    ).first()

    has_valid_text = (
        existing
        and bool(existing.extracted_text)
        and not (existing.extracted_text or "").startswith("[Binary file")
        and not (existing.extracted_text or "").startswith("[Unsupported file")
    )

    has_valid_summary = (
        existing
        and existing.ocr_status == "COMPLETED"
        and has_valid_text
        and bool(existing.document_summary)
        and "Navi System Notification" not in (existing.document_summary or "")
        and "has no readable text content to summarize" not in (existing.document_summary or "")
    )

    if existing and existing.ocr_status == "COMPLETED" and not force_reprocess and has_valid_summary:
        return {
            "ocr_id": existing.ocr_id,
            "document_id": existing.document_id,
            "ocr_status": existing.ocr_status,
            "page_count": existing.page_count,
            "character_count": len(existing.extracted_text) if existing.extracted_text else 0,
            "word_count": len(existing.extracted_text.split()) if existing.extracted_text else 0,
            "document_summary": existing.document_summary,
            "metadata_info": existing.metadata_info,
            "error_message": existing.error_message,
            "created_at": to_iso_ist(existing.created_at),
            "updated_at": to_iso_ist(existing.updated_at),
            "document_title": doc.get("document_title"),
            "document_number": doc.get("document_number"),
            "file_name": doc.get("file_name"),
            "file_type": doc.get("file_type"),
            "file_size": doc.get("file_size"),
            "is_cached": True
        }

    # Initialize or update to PROCESSING
    if not existing:
        existing = DmsDocumentOcr(
            document_id=document_id,
            ocr_status="PROCESSING",
            created_by=user_id
        )
        db.add(existing)
    else:
        existing.ocr_status = "PROCESSING"
        existing.updated_by = user_id
    db.commit()
    db.refresh(existing)

    try:
        # Step 1: Text extraction
        extract_res = extract_document_content(file_path)
        extracted_text = extract_res.get("extracted_text", "")
        page_count = extract_res.get("page_count", 1)
        meta_info = extract_res.get("metadata_info", {})
        err = extract_res.get("error")

        if err and not extracted_text:
            existing.ocr_status = "FAILED"
            existing.error_message = err
            existing.metadata_info = meta_info
            existing.updated_by = user_id
            db.commit()
            db.refresh(existing)
            log_ocr_history(db, existing)
            db.commit()

            raise HTTPException(
                status_code=422,
                detail=f"OCR Text Extraction failed: {err}"
            )

        # Step 2: Generate AI Summary
        doc_title = doc.get("document_title") or doc.get("document_number") or "Petronet Document"
        summary = generate_document_summary(
            document_text=extracted_text,
            document_title=doc_title,
            summary_type="detailed",
            custom_instructions=custom_summary_prompt
        )

        meta_info["character_count"] = extract_res.get("character_count", len(extracted_text))
        meta_info["word_count"] = extract_res.get("word_count", len(extracted_text.split()))

        # Update completed state
        existing.ocr_status = "COMPLETED"
        existing.extracted_text = extracted_text
        existing.document_summary = summary
        existing.page_count = page_count
        existing.metadata_info = meta_info
        existing.error_message = None
        existing.updated_by = user_id

        db.commit()
        db.refresh(existing)

        # Log history
        log_ocr_history(db, existing)
        db.commit()

        return {
            "ocr_id": existing.ocr_id,
            "document_id": existing.document_id,
            "ocr_status": existing.ocr_status,
            "page_count": existing.page_count,
            "character_count": meta_info.get("character_count"),
            "word_count": meta_info.get("word_count"),
            "document_summary": existing.document_summary,
            "metadata_info": existing.metadata_info,
            "error_message": None,
            "created_at": to_iso_ist(existing.created_at),
            "updated_at": to_iso_ist(existing.updated_at),
            "document_title": doc.get("document_title"),
            "document_number": doc.get("document_number"),
            "file_name": doc.get("file_name"),
            "file_type": doc.get("file_type"),
            "file_size": doc.get("file_size"),
            "is_cached": False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("OCR Processing unhandled failure for document %s: %s", document_id, e)
        existing.ocr_status = "FAILED"
        existing.error_message = str(e)
        existing.updated_by = user_id
        db.commit()
        log_ocr_history(db, existing)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing OCR for document ID {document_id}: {str(e)}"
        )


def get_document_ocr(
    db: Session,
    document_id: int,
    user_id: int,
    include_full_text: bool = True
) -> Dict[str, Any]:
    """Retrieves OCR extraction and AI summary status for a specific document."""
    doc = verify_user_document_access(db, user_id, document_id)

    ocr_row = db.query(DmsDocumentOcr).filter(
        DmsDocumentOcr.document_id == document_id,
        DmsDocumentOcr.is_deleted == False
    ).first()

    if not ocr_row:
        return {
            "ocr_id": None,
            "document_id": document_id,
            "ocr_status": "NOT_PROCESSED",
            "page_count": None,
            "character_count": 0,
            "word_count": 0,
            "document_summary": None,
            "extracted_text": None,
            "metadata_info": None,
            "error_message": None,
            "document_title": doc.get("document_title"),
            "document_number": doc.get("document_number"),
            "file_name": doc.get("file_name"),
            "file_type": doc.get("file_type"),
            "file_size": doc.get("file_size"),
            "created_at": None,
            "updated_at": None
        }

    char_count = len(ocr_row.extracted_text) if ocr_row.extracted_text else 0
    word_count = len(ocr_row.extracted_text.split()) if ocr_row.extracted_text else 0

    return {
        "ocr_id": ocr_row.ocr_id,
        "document_id": ocr_row.document_id,
        "ocr_status": ocr_row.ocr_status,
        "page_count": ocr_row.page_count,
        "character_count": char_count,
        "word_count": word_count,
        "document_summary": ocr_row.document_summary,
        "extracted_text": ocr_row.extracted_text if include_full_text else None,
        "metadata_info": ocr_row.metadata_info,
        "error_message": ocr_row.error_message,
        "document_title": doc.get("document_title"),
        "document_number": doc.get("document_number"),
        "file_name": doc.get("file_name"),
        "file_type": doc.get("file_type"),
        "file_size": doc.get("file_size"),
        "created_at": to_iso_ist(ocr_row.created_at),
        "updated_at": to_iso_ist(ocr_row.updated_at)
    }
