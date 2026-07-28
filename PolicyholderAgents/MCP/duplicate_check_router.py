"""
duplicate_check_router.py
──────────────────────────
FastAPI routes for the Duplicate Claim Check MCP.

Tool / Endpoint map:
  check_duplicate_claim        POST /api/duplicate_check/check
  get_recent_claims_for_policy GET  /api/duplicate_check/recent/{policy_number}
"""

import logging
from fastapi import APIRouter, HTTPException

from duplicate_check_mcp.models import CheckDuplicateClaimRequest
from duplicate_check_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/duplicate_check/check",
    operation_id="check_duplicate_claim",
    summary="Check whether a new FNOL/claim is a likely duplicate of an existing one",
    tags=["DuplicateCheck"],
)
def check_duplicate_claim(req: CheckDuplicateClaimRequest):
    """
    Searches claims and fnol_submissions for the same policy_number and
    loss_type with a date_of_loss within +/- 3 days of the supplied date.
    If matches are found and a description is supplied, an LLM compares
    the descriptions for similarity. Returns
    {is_duplicate, matches, confidence, similarity_note}.
    """
    try:
        return handler.check_duplicate_claim(
            req.policy_number, req.loss_type, req.date_of_loss, req.description
        )
    except Exception as e:
        log.exception("check_duplicate_claim error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/duplicate_check/recent/{policy_number}",
    operation_id="get_recent_claims_for_policy",
    summary="List recent claims filed under a policy",
    tags=["DuplicateCheck"],
)
def get_recent_claims_for_policy(policy_number: str, days: int = 90):
    """
    Returns claims filed under the given policy_number within the last
    `days` days (default 90), most recent first.
    """
    try:
        return handler.get_recent_claims_for_policy(policy_number, days)
    except Exception as e:
        log.exception("get_recent_claims_for_policy error")
        raise HTTPException(status_code=500, detail=str(e))
