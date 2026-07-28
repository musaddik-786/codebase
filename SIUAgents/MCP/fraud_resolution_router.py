"""
fraud_resolution_router.py
─────────────────────────────
FastAPI routes for the Fraud Resolution MCP.

Tool / Endpoint map:
  write_siu_decision   POST /api/fraud_resolution/decision/{claim_id}
  get_siu_decision     GET  /api/fraud_resolution/decision/{siu_case_id}
  resolve_siu_case     POST /api/fraud_resolution/resolve/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from fraud_resolution_mcp import handler
from fraud_resolution_mcp.models import ResolveSiuCaseRequest, WriteSiuDecisionRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/fraud_resolution/decision/{claim_id}",
    operation_id="write_siu_decision",
    summary="Record an SIU investigation decision",
    tags=["FraudResolution"],
)
def write_siu_decision(claim_id: str, body: WriteSiuDecisionRequest):
    """Inserts a new siu_decision row ("Fraud Confirmed"/"Fraud Cleared"/"Inconclusive")."""
    try:
        return handler.write_siu_decision(body.siu_case_id, claim_id, body.decision, body.confidence, body.closed_date)
    except Exception as e:
        log.exception("write_siu_decision error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/fraud_resolution/decision/{siu_case_id}",
    operation_id="get_siu_decision",
    summary="Get the most recent SIU decision for a case",
    tags=["FraudResolution"],
)
def get_siu_decision(siu_case_id: str):
    """Returns the most recent siu_decision row for the given siu_case_id, or null."""
    return handler.get_siu_decision(siu_case_id)


@router.post(
    "/api/fraud_resolution/resolve/{claim_id}",
    operation_id="resolve_siu_case",
    summary="Resolve and close an SIU case",
    tags=["FraudResolution"],
)
def resolve_siu_case(claim_id: str, body: ResolveSiuCaseRequest):
    """
    Writes the SIU decision, closes the siu_case_master record, updates the
    matching siu_escalation_records status, logs a 'Case Resolved' timeline
    event and an siu_activity_log entry, and (if decision == "Fraud
    Confirmed") sets siu_claim_master.fraud_flag for the claim.
    """
    try:
        return handler.resolve_siu_case(body.siu_case_id, claim_id, body.decision, body.confidence, body.notes)
    except Exception as e:
        log.exception("resolve_siu_case error")
        raise HTTPException(status_code=500, detail=str(e))
