"""
document_submission_router.py
──────────────────────────────
Endpoints:
  POST /api/documents/upload              — upload a file (image/video/document)
  GET  /api/documents/{document_id}/validate — validate a document is stored correctly
  GET  /api/documents/claim/{claim_id}    — list all documents for a claim
  GET  /api/documents/{document_id}       — get a single document record
"""

import logging
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from document_submission_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/documents/upload",
    operation_id="upload_document",
    summary="Upload evidence file (image, video, or document) for a claim",
    tags=["Documents"],
)
async def upload_document(
    claim_number: str = Form(...),
    uploaded_by: str = Form(None),
    uploaded_by_role: str = Form("Policyholder"),
    file: UploadFile = File(...),
):
    """
    Accepts any file type. Automatically:
    - Detects category: Image (jpg/png/…), Video (mp4/mov/…), or Document (pdf/docx/txt/…)
    - Uploads the file to Azure Blob Storage
    - Records filename, category, size, blob URL, and uploader in the documents table
    Returns the full document record including document_id and file_url.
    """
    try:
        return handler.upload_document_file(
            claim_number, file, uploaded_by, uploaded_by_role
        )
    except Exception as e:
        log.exception("upload_document error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/documents/{document_id}/validate",
    operation_id="validate_document",
    summary="Validate that a document is correctly stored and its record is in the database",
    tags=["Documents"],
)
def validate_document(document_id: str):
    """
    Checks:
    1. The document record exists in the documents table.
    2. The stored file URL (Azure Blob or local path) is accessible.
    Updates the document status to 'Validated' or 'Invalid' and returns the result.
    """
    try:
        return handler.validate_document(document_id)
    except Exception as e:
        log.exception("validate_document error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/documents/claim/{claim_number}",
    operation_id="get_claim_documents",
    summary="List all evidence files uploaded for a claim",
    tags=["Documents"],
)
def get_claim_documents(claim_number: str):
    """Returns all document records for the given claim_number, most recently uploaded first."""
    return handler.get_claim_documents(claim_number)


@router.get(
    "/api/documents/{document_id}",
    operation_id="get_document",
    summary="Get a single document record by document_id",
    tags=["Documents"],
)
def get_document(document_id: str):
    """Returns the document record including category, status, and storage URL."""
    record = handler.get_document(document_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return record
