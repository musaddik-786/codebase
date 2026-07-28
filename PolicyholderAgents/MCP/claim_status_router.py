"""
claim_status_router.py
─────────────────────────
FastAPI routes for the Claim Status ("Follow My Claim") MCP.

Tool / Endpoint map:
  get_claim_journey         GET  /api/claim_status/journey/{claim_number}
  get_claim_status_summary   GET  /api/claim_status/summary/{claim_number}
  advance_claim_stage         POST /api/claim_status/advance
  log_policyholder_action     POST /api/claim_status/log_action
  get_policyholder_actions    GET  /api/claim_status/actions/{claim_number}
"""

import logging
from fastapi import APIRouter, HTTPException

from claim_status_mcp.models import AdvanceClaimStageRequest, LogPolicyholderActionRequest
from claim_status_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/claim_status/journey/{claim_number}",
    operation_id="get_claim_journey",
    summary="Get the claim journey and SLA stage history",
    tags=["ClaimStatus"],
)
def get_claim_journey(claim_number: str):
    """
    Returns the claim_journey_master row (current stage, sub-status, SLA
    status) plus all stage_time_sla_tracking rows for the claim.
    """
    try:
        return handler.get_claim_journey(claim_number)
    except Exception as e:
        log.exception("get_claim_journey error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/claim_status/summary/{claim_number}",
    operation_id="get_claim_status_summary",
    summary="Get a combined claim status summary",
    tags=["ClaimStatus"],
)
def get_claim_status_summary(claim_number: str):
    """
    Combines claims.status with claim_journey_master's current_stage,
    current_stage_name, sub_status, and overall_sla_status into one
    summary dict for the policyholder.
    """
    record = handler.get_claim_status_summary(claim_number)
    if not record or record.get("error"):
        raise HTTPException(status_code=404, detail=f"Claim {claim_number} not found")
    return record


@router.post(
    "/api/claim_status/advance",
    operation_id="advance_claim_stage",
    summary="Advance the claim to a new journey stage",
    tags=["ClaimStatus"],
)
def advance_claim_stage(req: AdvanceClaimStageRequest):
    """
    Updates claim_journey_master with the new current_stage, current_stage_name,
    and (optionally) sub_status, and inserts a new stage_time_sla_tracking row.
    """
    try:
        return handler.advance_claim_stage(
            req.claim_number, req.new_stage, req.stage_name, req.sub_status
        )
    except Exception as e:
        log.exception("advance_claim_stage error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/claim_status/log_action",
    operation_id="log_policyholder_action",
    summary="Log an action taken by the policyholder on a claim",
    tags=["ClaimStatus"],
)
def log_policyholder_action(req: LogPolicyholderActionRequest):
    """
    Records an action the policyholder reports taking (e.g. uploading a
    document, calling support) into policyholder_actions, tagged with the
    current journey stage.
    """
    try:
        return handler.log_policyholder_action(
            req.claim_number, req.action_type, req.action_label, req.details
        )
    except Exception as e:
        log.exception("log_policyholder_action error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/claim_status/actions/{claim_number}",
    operation_id="get_policyholder_actions",
    summary="Get the policyholder action log for a claim",
    tags=["ClaimStatus"],
)
def get_policyholder_actions(claim_number: str):
    """
    Returns all policyholder_actions rows for the given claim_number,
    most recent first.
    """
    return handler.get_policyholder_actions(claim_number)
