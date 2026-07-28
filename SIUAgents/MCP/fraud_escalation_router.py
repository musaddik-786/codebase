"""
fraud_escalation_router.py
─────────────────────────────
FastAPI routes for the Fraud Escalation MCP.

Tool / Endpoint map:
  create_siu_escalation    POST /api/fraud_escalation/escalation/{claim_id}
  get_siu_escalation       GET  /api/fraud_escalation/escalation/{claim_id}
  create_siu_case          POST /api/fraud_escalation/case/{claim_id}
  log_siu_timeline_event   POST /api/fraud_escalation/timeline/{claim_id}
  forward_to_siu           POST /api/fraud_escalation/forward/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from fraud_escalation_mcp import handler
from fraud_escalation_mcp.models import (
    CreateSiuCaseRequest,
    CreateSiuEscalationRequest,
    ForwardToSiuRequest,
    LogTimelineEventRequest,
)

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/fraud_escalation/escalation/{claim_id}",
    operation_id="create_siu_escalation",
    summary="Create an SIU escalation record for a claim",
    tags=["FraudEscalation"],
)
def create_siu_escalation(claim_id: str, body: CreateSiuEscalationRequest):
    """Inserts a new siu_escalation_records row with status 'Under Review'."""
    try:
        return handler.create_siu_escalation(
            claim_id, body.escalation_reason, body.fraud_score, body.evidence_notes, body.escalated_by,
        )
    except Exception as e:
        log.exception("create_siu_escalation error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/fraud_escalation/escalation/{claim_id}",
    operation_id="get_siu_escalation",
    summary="Get the most recent SIU escalation record for a claim",
    tags=["FraudEscalation"],
)
def get_siu_escalation(claim_id: str):
    """Returns the most recent siu_escalation_records row for the given claim_id, or null."""
    return handler.get_siu_escalation(claim_id)


@router.post(
    "/api/fraud_escalation/case/{claim_id}",
    operation_id="create_siu_case",
    summary="Create an SIU case for a claim",
    tags=["FraudEscalation"],
)
def create_siu_case(claim_id: str, body: CreateSiuCaseRequest):
    """Inserts a new siu_case_master row with status 'Open'."""
    try:
        return handler.create_siu_case(claim_id, body.assigned_investigator)
    except Exception as e:
        log.exception("create_siu_case error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/fraud_escalation/timeline/{claim_id}",
    operation_id="log_siu_timeline_event",
    summary="Log an SIU timeline event for a claim",
    tags=["FraudEscalation"],
)
def log_siu_timeline_event(claim_id: str, body: LogTimelineEventRequest):
    """Inserts a new siu_timeline_events row."""
    try:
        return handler.log_siu_timeline_event(body.siu_case_id, claim_id, body.event_type, body.status)
    except Exception as e:
        log.exception("log_siu_timeline_event error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/fraud_escalation/forward/{claim_id}",
    operation_id="forward_to_siu",
    summary="Forward a claim to SIU for investigation",
    tags=["FraudEscalation"],
)
def forward_to_siu(claim_id: str, body: ForwardToSiuRequest):
    """
    Reads the latest fraud_risk_snapshots fraud_score for the claim, creates
    an siu_escalation_records row, opens a new siu_case_master row, logs a
    'Case Opened' siu_timeline_events row, and inserts a matching
    siu_claim_master row (fraud_flag set if fraud_score >= 70).
    """
    try:
        return handler.forward_to_siu(claim_id, body.escalation_reason, body.evidence_notes, body.escalated_by)
    except Exception as e:
        log.exception("forward_to_siu error")
        raise HTTPException(status_code=500, detail=str(e))
