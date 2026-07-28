"""
legal_escalation_router.py
─────────────────────────────
FastAPI routes for the Legal Escalation MCP.

Tool / Endpoint map:
  create_legal_escalation         POST /api/legal_escalation/escalation/{claim_id}
  get_legal_escalation            GET  /api/legal_escalation/escalation/{claim_id}
  update_legal_escalation_outcome POST /api/legal_escalation/escalation/{claim_id}/outcome/{escalation_id}
  refer_to_legal                  POST /api/legal_escalation/refer/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from legal_escalation_mcp import handler
from legal_escalation_mcp.models import CreateLegalEscalationRequest, UpdateLegalEscalationOutcomeRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/legal_escalation/escalation/{claim_id}",
    operation_id="create_legal_escalation",
    summary="Create a legal escalation for a claim",
    tags=["LegalEscalation"],
)
def create_legal_escalation(claim_id: str, body: CreateLegalEscalationRequest):
    """Inserts a new legal_escalations row with status 'Pending Review'."""
    try:
        return handler.create_legal_escalation(body.siu_case_id, claim_id, body.reason, body.fraud_score, body.referred_by)
    except Exception as e:
        log.exception("create_legal_escalation error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/legal_escalation/escalation/{claim_id}",
    operation_id="get_legal_escalation",
    summary="Get the most recent legal escalation for a claim",
    tags=["LegalEscalation"],
)
def get_legal_escalation(claim_id: str):
    """Returns the most recent legal_escalations row for the given claim_id, or null."""
    return handler.get_legal_escalation(claim_id)


@router.post(
    "/api/legal_escalation/escalation/{claim_id}/outcome/{escalation_id}",
    operation_id="update_legal_escalation_outcome",
    summary="Update the status/outcome of a legal escalation",
    tags=["LegalEscalation"],
)
def update_legal_escalation_outcome(claim_id: str, escalation_id: str, body: UpdateLegalEscalationOutcomeRequest):
    """Updates status and outcome on the legal_escalations row matching escalation_id."""
    try:
        return handler.update_legal_escalation_outcome(escalation_id, body.status, body.outcome)
    except Exception as e:
        log.exception("update_legal_escalation_outcome error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/legal_escalation/refer/{claim_id}",
    operation_id="refer_to_legal",
    summary="Refer a claim to Legal if SIU confirmed fraud",
    tags=["LegalEscalation"],
)
def refer_to_legal(claim_id: str):
    """
    Reads the most recent siu_case_master row and siu_decision for the
    claim. If decision == "Fraud Confirmed", creates a legal_escalations row
    and logs an siu_activity_log entry. Otherwise explains referral is not
    applicable.
    """
    try:
        return handler.refer_to_legal(claim_id)
    except Exception as e:
        log.exception("refer_to_legal error")
        raise HTTPException(status_code=500, detail=str(e))
