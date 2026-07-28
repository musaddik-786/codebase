"""
orchestration_router.py (Adjuster-local copy)
────────────────────────────────────────────────
FastAPI routes for the Orchestration MCP — HITL approval gates and per-claim
stage tracking, now hosted locally within AdjusterAgents' own MCP server so
AdjusterOrchestrator (and claims-solution-integration) no longer depend on
OrchestratorAgent's process being up. Same table names / same tool names as
the original at OrchestratorAgent/MCP/orchestration_router.py — this is a
duplicate service, not a fork of the data.

Route paths are deliberately NOT prefixed with "/api/orchestration" the way
the original is — this sub-app is already mounted at /api/v1/orchestration
in main.py, so repeating "orchestration" in each route's own path would just
reproduce the confusing doubled-prefix quirk
(.../api/v1/orchestration/api/orchestration/...) that claims-solution-
integration's ORCHESTRATOR_URL config never correctly accounted for. Since
this is a brand-new copy with no existing caller depending on that exact
path shape, there's no reason to carry the wart forward.

Tool / Endpoint map (full path = http://localhost:5800/api/v1/orchestration + below):
  get_claim_orchestration_state   GET  /state/{claim_id}
  set_claim_orchestration_state   POST /state/{claim_id}
  create_approval_request         POST /approvals/{claim_id}
  get_pending_approvals           GET  /approvals/pending
  decide_approval                 POST /approvals/{approval_id}/decide
  get_approval_status              GET  /approvals/{claim_id}/{gate_type}/status
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
    "/state/{claim_id}",
    operation_id="get_claim_orchestration_state",
    summary="Get the current orchestration stage/status for a claim",
    tags=["Orchestration"],
)
def get_claim_orchestration_state(claim_id: str):
    """Returns current_stage/status/last_action for the claim, or found=False if none exists."""
    return handler.get_claim_orchestration_state(claim_id)


@router.post(
    "/state/{claim_id}",
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
    "/approvals/{claim_id}",
    operation_id="create_approval_request",
    summary="Create a human approval request (HITL gate) for a claim",
    tags=["Orchestration"],
)
def create_approval_request(claim_id: str, body: CreateApprovalRequest):
    """
    Inserts a new human_approval_requests row with status 'Pending'.
    gate_type is one of AdjusterOrchestrator's own gates (triage_approval,
    coverage_verification_review) — see AdjusterOrchestrator/server.py.
    """
    try:
        return handler.create_approval_request(claim_id, body.gate_type, body.summary, body.requested_by)
    except Exception as e:
        log.exception("create_approval_request error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/approvals/pending",
    operation_id="get_pending_approvals",
    summary="List pending human approval requests, optionally filtered by claim_id/gate_type",
    tags=["Orchestration"],
)
def get_pending_approvals(claim_id: Optional[str] = None, gate_type: Optional[str] = None):
    """Returns all human_approval_requests rows with status='Pending', optionally filtered."""
    return handler.get_pending_approvals(claim_id, gate_type)


@router.post(
    "/approvals/{approval_id}/decide",
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
    "/approvals/{claim_id}/{gate_type}/status",
    operation_id="get_approval_status",
    summary="Get the status of the most recent approval request for a claim+gate_type",
    tags=["Orchestration"],
)
def get_approval_status(claim_id: str, gate_type: str):
    """
    Returns the most recent human_approval_requests row's status for this
    claim+gate_type, or status='None' if no such request exists. This is
    what AdjusterOrchestrator polls before proceeding past a blocking gate.
    """
    return handler.get_approval_status(claim_id, gate_type)
