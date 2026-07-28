"""
orchestration_router.py
─────────────────────────
FastAPI routes for the Orchestration MCP — used by the Brain Agent to
track per-claim stage progression and human-in-the-loop approval gates.

Tool / Endpoint map:
  get_claim_orchestration_state   GET  /api/orchestration/state/{claim_id}
  set_claim_orchestration_state   POST /api/orchestration/state/{claim_id}
  create_approval_request         POST /api/orchestration/approvals/{claim_id}
  get_pending_approvals           GET  /api/orchestration/approvals/pending
  decide_approval                 POST /api/orchestration/approvals/{approval_id}/decide
  get_approval_status             GET  /api/orchestration/approvals/{claim_id}/{gate_type}/status
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException

from orchestration_mcp import handler
from orchestration_mcp.models import (
    CreateApprovalRequest,
    DecideApprovalRequest,
    SetOrchestrationStateRequest,
)

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/orchestration/state/{claim_id}",
    operation_id="get_claim_orchestration_state",
    summary="Get the current orchestration stage/status for a claim",
    tags=["Orchestration"],
)
def get_claim_orchestration_state(claim_id: str):
    """Returns current_stage/status/last_action for the claim, or found=False if none exists."""
    return handler.get_claim_orchestration_state(claim_id)


@router.post(
    "/api/orchestration/state/{claim_id}",
    operation_id="set_claim_orchestration_state",
    summary="Upsert the orchestration stage/status for a claim",
    tags=["Orchestration"],
)
def set_claim_orchestration_state(claim_id: str, body: SetOrchestrationStateRequest):
    """Creates or updates the claim_orchestration_state row for the claim."""
    try:
        return handler.set_claim_orchestration_state(claim_id, body.current_stage, body.status, body.last_action)
    except Exception as e:
        log.exception("set_claim_orchestration_state error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/orchestration/approvals/{claim_id}",
    operation_id="create_approval_request",
    summary="Create a human approval request (HITL gate) for a claim",
    tags=["Orchestration"],
)
def create_approval_request(claim_id: str, body: CreateApprovalRequest):
    """
    Inserts a new human_approval_requests row with status 'Pending'.
    gate_type is one of the 6 REQUIRED gates (damage_assessment_review,
    reserve_approval, settlement_approval, siu_decision_approval,
    payment_approval, claim_closure_approval) or 3 OPTIONAL gates
    (fnol_review, triage_approval, vendor_assignment_approval).
    """
    try:
        return handler.create_approval_request(claim_id, body.gate_type, body.summary, body.requested_by)
    except Exception as e:
        log.exception("create_approval_request error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/orchestration/approvals/pending",
    operation_id="get_pending_approvals",
    summary="List pending human approval requests, optionally filtered by claim_id/gate_type",
    tags=["Orchestration"],
)
def get_pending_approvals(claim_id: Optional[str] = None, gate_type: Optional[str] = None):
    """Returns all human_approval_requests rows with status='Pending', optionally filtered."""
    return handler.get_pending_approvals(claim_id, gate_type)


@router.post(
    "/api/orchestration/approvals/{approval_id}/decide",
    operation_id="decide_approval",
    summary="Record a human decision (Approved/Rejected) on an approval request",
    tags=["Orchestration"],
)
def decide_approval(approval_id: str, body: DecideApprovalRequest):
    """Updates status, decided_by, decided_at, decision_notes on the human_approval_requests row."""
    try:
        return handler.decide_approval(approval_id, body.decision, body.decided_by, body.notes)
    except Exception as e:
        log.exception("decide_approval error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/orchestration/approvals/{claim_id}/{gate_type}/status",
    operation_id="get_approval_status",
    summary="Get the status of the most recent approval request for a claim+gate_type",
    tags=["Orchestration"],
)
def get_approval_status(claim_id: str, gate_type: str):
    """
    Returns the most recent human_approval_requests row's status for this
    claim+gate_type, or status='None' if no such request exists. This is
    what the Brain Agent polls before proceeding past a REQUIRED gate.
    """
    return handler.get_approval_status(claim_id, gate_type)
