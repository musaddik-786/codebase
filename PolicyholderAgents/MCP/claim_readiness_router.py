"""
claim_readiness_router.py
──────────────────────────
Tool / Endpoint map:
  score_claim_readiness         POST /api/claim_readiness/score/{claim_number}
  acknowledge_missing_docs      POST /api/claim_readiness/acknowledge_docs/{claim_number}
  get_intake_validation_result  GET  /api/claim_readiness/validation/{claim_number}
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from claim_readiness_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


class AcknowledgeDocsRequest(BaseModel):
    notes: Optional[str] = None


@router.post(
    "/api/claim_readiness/acknowledge_docs/{claim_number}",
    operation_id="acknowledge_missing_docs",
    summary="Record that the policyholder has no documents to upload right now",
    tags=["ClaimReadiness"],
)
def acknowledge_missing_docs(claim_number: str, req: AcknowledgeDocsRequest = None):
    """
    Marks docs_status as 'Acknowledged - Not Available' in intake_validation_result_output.
    Call this only after the policyholder explicitly confirms they cannot upload
    evidence at this time. The FNOL and Claim ID remain intact.
    """
    notes = (req.notes if req else None)
    return handler.acknowledge_missing_docs(claim_number, notes)


@router.get(
    "/api/claim_readiness/validation/{claim_number}",
    operation_id="get_intake_validation_result",
    summary="Read the latest intake_validation_result_output for a claim",
    tags=["ClaimReadiness"],
)
def get_intake_validation_result(claim_number: str):
    """Read the most recent completeness-scoring result stored for a claim."""
    record = handler.get_intake_validation_result(claim_number)
    if not record:
        return {"status": "not_found", "claim_number": claim_number}
    return record


@router.post(
    "/api/claim_readiness/score/{claim_number}",
    operation_id="score_claim_readiness",
    summary="Score FNOL completeness and initial fraud risk for a claim",
    tags=["ClaimReadiness"],
)
def score_claim_readiness(claim_number: str):
    """
    Compute completeness_score against mandatory FNOL fields, assess
    coverage_status, run LLM fraud pre-screen, and persist the result to
    intake_validation_result_output.
    """
    return handler.score_claim_readiness(claim_number)
