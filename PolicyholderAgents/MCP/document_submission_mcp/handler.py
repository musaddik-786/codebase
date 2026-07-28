"""
handler.py — Document Submission
─────────────────────────────────
Three responsibilities:
  1. upload   — accept file, detect category (Image/Video/Document),
                upload to Azure Blob Storage, record in documents table
  2. validate — confirm the DB record exists and the blob URL is reachable
  3. retrieve — list or fetch document records for a claim
"""

import logging
import mimetypes
import os
import sys
from datetime import datetime
from typing import Optional
import random

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from db import get_db_connection, row_to_dict  # noqa: E402
from dotenv import load_dotenv, find_dotenv
from claim_readiness_mcp.handler import score_claim_readiness  # noqa: E402

load_dotenv(find_dotenv())

log = logging.getLogger(__name__)

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "claims-evidence")

# Fallback local uploads dir when Azure Storage is not configured
_LOCAL_UPLOADS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "uploads")
)

_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp", "image/tiff"}
_VIDEO_TYPES = {"video/mp4", "video/mpeg", "video/quicktime", "video/webm", "video/x-msvideo", "video/x-ms-wmv"}


def _categorize(content_type: str, file_name: str) -> str:
    ct = (content_type or "").lower().split(";")[0].strip()
    if ct in _IMAGE_TYPES or ct.startswith("image/"):
        return "Image"
    if ct in _VIDEO_TYPES or ct.startswith("video/"):
        return "Video"
    return "Document"


def _upload_to_azure_blob(blob_name: str, data: bytes, content_type: str) -> str:
    """Upload bytes to Azure Blob Storage and return the public URL."""
    from azure.storage.blob import BlobServiceClient, ContentSettings
    service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container = service.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
    try:
        container.create_container()
    except Exception:
        pass  # container already exists
    blob = container.get_blob_client(blob_name)
    blob.upload_blob(
        data,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
    )
    return blob.url


def _save_locally(blob_name: str, data: bytes) -> str:
    """Fallback: save to local disk, return file path."""
    os.makedirs(_LOCAL_UPLOADS_DIR, exist_ok=True)
    file_path = os.path.join(_LOCAL_UPLOADS_DIR, blob_name.replace("/", "_"))
    with open(file_path, "wb") as f:
        f.write(data)
    return file_path


# def upload_document_file(
#     claim_id: str,
#     file,
#     uploaded_by: Optional[str] = None,
#     uploaded_by_role: str = "Policyholder",
# ) -> dict:
#     """
#     Accept a file upload, detect its category, store it in Azure Blob Storage
#     (or local disk as fallback), and record the metadata in the documents table.
#     """
#     timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#     document_id = f"DOC-{timestamp}-{random.randint(1000, 9999)}"

#     file_name = file.filename
#     raw_bytes = file.file.read()
#     file_size = len(raw_bytes)

#     content_type = (
#         file.content_type
#         or mimetypes.guess_type(file_name)[0]
#         or "application/octet-stream"
#     )
#     document_type = _categorize(content_type, file_name)

#     # Blob path: claims-evidence/<claim_id>/<document_id>/<file_name>
#     blob_name = f"{claim_id}/{document_id}/{file_name}"

#     if AZURE_STORAGE_CONNECTION_STRING:
#         try:
#             file_url = _upload_to_azure_blob(blob_name, raw_bytes, content_type)
#             storage_backend = "azure_blob"
#         except Exception as e:
#             log.warning("Azure Blob upload failed, falling back to local: %s", e)
#             file_url = _save_locally(blob_name, raw_bytes)
#             storage_backend = "local_fallback"
#     else:
#         log.info("AZURE_STORAGE_CONNECTION_STRING not set — saving locally")
#         file_url = _save_locally(blob_name, raw_bytes)
#         storage_backend = "local_fallback"

#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO documents (
#                 document_id, claim_id, file_name, file_url, file_size,
#                 content_type, document_type, classification_confidence,
#                 uploaded_by, uploaded_by_role, status, visibility, uploaded_at
#             ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Uploaded','public',NOW())
#             RETURNING *
#             """,
#             (
#                 document_id, claim_id, file_name, file_url, file_size,
#                 content_type, document_type, 100,
#                 uploaded_by, uploaded_by_role,
#             ),
#         )
#         record = row_to_dict(cur.fetchone())
#         conn.commit()
#     except Exception:
#         conn.rollback()
#         raise
#     finally:
#         conn.close()

#     record["storage_backend"] = storage_backend
#     return record

def upload_document_file(
    claim_number: str,
    file,
    uploaded_by: Optional[str] = None,
    uploaded_by_role: str = "Policyholder",
) -> dict:
    """
    Upload file, store in documents table, and also store same file_url
    in claims table (column: file_url using claim_number).
    """

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    document_id = f"DOC-{timestamp}-{random.randint(1000, 9999)}"

    file_name = file.filename
    raw_bytes = file.file.read()
    file_size = len(raw_bytes)

    content_type = (
        file.content_type
        or mimetypes.guess_type(file_name)[0]
        or "application/octet-stream"
    )

    document_type = _categorize(content_type, file_name)

    blob_name = f"{claim_number}/{document_id}/{file_name}"

    # ✅ Upload to Azure / Local
    upload_warning = None
    if AZURE_STORAGE_CONNECTION_STRING:
        try:
            file_url = _upload_to_azure_blob(blob_name, raw_bytes, content_type)
            storage_backend = "azure_blob"
        except Exception as e:
            log.warning("Azure upload failed, fallback to local: %s", e)
            file_url = _save_locally(blob_name, raw_bytes)
            storage_backend = "local_fallback"
            upload_warning = (
                "Cloud storage is temporarily unavailable, so this file was saved "
                "locally on the server instead. It's viewable in Document Hub, but "
                "let your administrator know so cloud storage can be restored."
            )
    else:
        log.info("Azure not configured — saving locally")
        file_url = _save_locally(blob_name, raw_bytes)
        storage_backend = "local_fallback"
        upload_warning = (
            "Cloud storage is not configured, so this file was saved locally on "
            "the server instead. It's viewable in Document Hub, but let your "
            "administrator know so cloud storage can be set up."
        )

    # ✅ Insert into documents table
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO documents (
                document_id, claim_number, file_name, file_url, file_size,
                content_type, document_type, classification_confidence,
                uploaded_by, uploaded_by_role, status, visibility, uploaded_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Uploaded','public',NOW())
            RETURNING *
            """,
            (
                document_id,
                claim_number,
                file_name,
                file_url,
                file_size,
                content_type,
                document_type,
                100,
                uploaded_by,
                uploaded_by_role,
            ),
        )

        record = row_to_dict(cur.fetchone())
        conn.commit()

    except Exception as e:
        conn.rollback()
        log.error("Document insert failed: %s", e)
        raise
    finally:
        conn.close()

    # ✅ ✅ Update claims table (NON-BLOCKING FIXED VERSION)
    try:
        conn2 = get_db_connection()
        cur2 = conn2.cursor()

        # ✅ LOG LOCATION (you asked this specifically)
        log.info(f"Updating claims with URL: {file_url} for claim_number: {claim_number}")

        # file_url is jsonb in the live DB — append new URL to the existing array
        # (or create a new single-element array if the column is null/non-array).
        cur2.execute(
            """
            UPDATE claims
            SET file_url = CASE
                WHEN file_url IS NULL THEN jsonb_build_array(%s::text)
                WHEN jsonb_typeof(file_url) = 'array' THEN file_url || jsonb_build_array(%s::text)
                ELSE jsonb_build_array(%s::text)
            END
            WHERE claim_number = %s
            """,
            (file_url, file_url, file_url, claim_number),
        )

        conn2.commit()

        if cur2.rowcount == 0:
            log.warning(f"No claim found for claim_number={claim_number}")

    except Exception as e:
        log.error(f"Claims update failed: {e}")
        try:
            conn2.rollback()
        except Exception:
            pass

    finally:
        try:
            conn2.close()
        except:
            pass

    # ✅ Refresh claim readiness — a new upload can move docs_status from
    # Incomplete to Complete, so the Follow My Claims UI must not keep
    # showing the pre-upload snapshot. Non-blocking: the upload has already
    # succeeded above, so a scoring failure here must not fail the request.
    try:
        score_claim_readiness(claim_number)
    except Exception as e:
        log.warning(f"score_claim_readiness refresh failed after upload: {e}")

    record["storage_backend"] = storage_backend
    if upload_warning:
        record["warning"] = upload_warning
    return record


def validate_document(document_id: str) -> dict:
    """
    Confirm a document record exists in the DB and its stored file/blob URL
    is reachable. Updates the document status to 'Validated' or 'Invalid'.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM documents WHERE document_id = %s", (document_id,))
        doc = row_to_dict(cur.fetchone())
    finally:
        conn.close()

    if not doc:
        return {
            "valid": False,
            "document_id": document_id,
            "reason": "Document not found in database",
        }

    file_url = doc.get("file_url", "")
    if not file_url:
        return {
            "valid": False,
            "document_id": document_id,
            "reason": "No file URL recorded — upload may have failed",
        }

    # Check accessibility: blob URL (HTTP HEAD) or local path existence
    accessible = False
    if file_url.startswith("http"):
        try:
            import httpx
            resp = httpx.head(file_url, timeout=10, follow_redirects=True)
            accessible = resp.status_code < 400
        except Exception as e:
            log.warning("Blob HEAD check failed for %s: %s", file_url, e)
    else:
        accessible = os.path.exists(file_url)

    new_status = "Validated" if accessible else "Invalid"
    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        cur2.execute(
            "UPDATE documents SET status = %s WHERE document_id = %s",
            (new_status, document_id),
        )
        conn2.commit()
    finally:
        conn2.close()

    return {
        "valid": accessible,
        "document_id": document_id,
        "file_name": doc.get("file_name"),
        "document_type": doc.get("document_type"),
        "file_url": file_url,
        "status": new_status,
        "claim_number": doc.get("claim_number"),
        "uploaded_by": doc.get("uploaded_by"),
        "uploaded_at": str(doc.get("uploaded_at", "")),
    }


def get_claim_documents(claim_number: str) -> list:
    """Return all documents uploaded for a claim, most recent first."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT document_id, claim_number, file_name, file_url, file_size, "
            "content_type, document_type, status, uploaded_by, uploaded_at "
            "FROM documents WHERE claim_number = %s ORDER BY uploaded_at DESC",
            (claim_number,),
        )
        return row_to_dict(cur.fetchall()) or []
    finally:
        conn.close()


def get_document(document_id: str) -> Optional[dict]:
    """Return a single document record by document_id."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT document_id, claim_number, file_name, file_url, file_size, "
            "content_type, document_type, status, uploaded_by, uploaded_at "
            "FROM documents WHERE document_id = %s",
            (document_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()
