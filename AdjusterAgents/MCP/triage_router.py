"""
triage_router.py
─────────────────
Tool / Endpoint map:
  get_claim_triage  GET /api/triage/triage/{claim_id}
  run_triage        POST /api/triage/run/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from triage_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/triage/triage/{claim_id}",
    operation_id="get_claim_triage",
    summary="Read the latest claim_triage record for a claim",
    tags=["Triage"],
)
def get_claim_triage(claim_id: str):
    record = handler.get_claim_triage(claim_id)
    if not record:
        return {"claim_id": claim_id, "claim_triage": None}
    return {"claim_id": claim_id, "claim_triage": record}


@router.post(
    "/api/triage/run/{claim_id}",
    operation_id="run_triage",
    summary="Run triage scoring for a claim — computes priority score, SLA risk, and routing recommendation",
    tags=["Triage"],
)
def run_triage(claim_id: str):
    try:
        return handler.run_triage(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("run_triage error")
        raise HTTPException(status_code=500, detail=str(e))
