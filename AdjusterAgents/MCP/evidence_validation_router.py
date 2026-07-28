"""
evidence_validation_router.py
───────────────────────────────
Tool / Endpoint map:
  get_evidence_items         GET  /api/evidence_validation/items/{claim_id}
  get_claim_documents        GET  /api/evidence_validation/documents/{claim_id}
  get_damage_items           GET  /api/evidence_validation/damage_items/{claim_id}
  get_active_fraud_flags     GET  /api/evidence_validation/fraud-flags/{claim_id}
  run_evidence_validation    POST /api/evidence_validation/run/{claim_id}
  save_validation_result     POST /api/evidence_validation/save/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from evidence_validation_mcp import handler
from evidence_validation_mcp.models import SaveValidationResultRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/evidence_validation/items/{claim_id}",
    operation_id="get_evidence_items",
    summary="Read all evidence_items for a claim",
    tags=["EvidenceValidation"],
)
def get_evidence_items(claim_id: str):
    records = handler.get_evidence_items(claim_id)
    return {"claim_id": claim_id, "evidence_items": records}


@router.get(
    "/api/evidence_validation/documents/{claim_id}",
    operation_id="get_claim_documents",
    summary="Read all uploaded documents for a claim",
    tags=["EvidenceValidation"],
)
def get_claim_documents(claim_id: str):
    """Returns all documents from the shared documents table for the given claim_id."""
    records = handler.get_claim_documents(claim_id)
    return {"claim_id": claim_id, "documents": records}


@router.get(
    "/api/evidence_validation/damage_items/{claim_id}",
    operation_id="get_damage_items",
    summary="Read all assessed damage items for a claim (for cross-referencing)",
    tags=["EvidenceValidation"],
)
def get_damage_items(claim_id: str):
    """Returns all damage_items rows for the given claim_id."""
    records = handler.get_damage_items(claim_id)
    return {"claim_id": claim_id, "damage_items": records}


@router.get(
    "/api/evidence_validation/fraud-flags/{claim_id}",
    operation_id="get_active_fraud_flags",
    summary="Retrieve active fraud_flags records for a claim",
    tags=["EvidenceValidation"],
)
def get_active_fraud_flags(claim_id: str):
    """
    Returns the actual fraud_flags table records (status = 'Active') for the claim.
    Each record includes: flag_type, flag_description, risk_score, detected_by, flagged_at.

    Use this tool when the user asks about fraud flags, active flags, or what flags have
    been raised on a claim. These are distinct from drone/weather/image authenticity
    findings returned by run_evidence_validation — those are analysis-derived signals,
    not stored fraud_flags records.
    """
    try:
        return handler.get_active_fraud_flags(claim_id)
    except Exception as e:
        log.exception("get_active_fraud_flags error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/evidence_validation/run/{claim_id}",
    operation_id="run_evidence_validation",
    summary="Run LLM-based evidence completeness and authenticity check (does not save)",
    tags=["EvidenceValidation"],
)
def run_evidence_validation(claim_id: str):
    """
    Cross-checks evidence_items against required types for the claim's
    loss_type and runs an LLM authenticity check. Returns the validation
    result WITHOUT updating any DB statuses — call save_validation_result to persist.
    """
    try:
        return handler.run_evidence_validation(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("run_evidence_validation error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/evidence_validation/save/{claim_id}",
    operation_id="save_validation_result",
    summary="Persist validation result — update evidence item statuses",
    tags=["EvidenceValidation"],
)
def save_validation_result(claim_id: str, body: SaveValidationResultRequest):
    """
    Updates evidence_items statuses based on the validation result:
    flagged items → 'Flagged', pending unflagged items → 'Verified'.
    """
    try:
        return handler.save_validation_result(claim_id, body.overall_status, body.authenticity_flags)
    except Exception as e:
        log.exception("save_validation_result error")
        raise HTTPException(status_code=500, detail=str(e))
