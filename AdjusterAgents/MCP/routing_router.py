"""
routing_router.py
──────────────────
Tool / Endpoint map:
  get_auto_assignment_log  GET  /api/routing/assignment_log/{claim_id}
  assign_claim             POST /api/routing/assign/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from routing_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/routing/assignment_log/{claim_id}",
    operation_id="get_auto_assignment_log",
    summary="Read all auto_assignment_log entries for a claim",
    tags=["Routing"],
)
def get_auto_assignment_log(claim_id: str):
    records = handler.get_auto_assignment_log(claim_id)
    return {"claim_id": claim_id, "auto_assignment_log": records}


@router.post(
    "/api/routing/assign/{claim_id}",
    operation_id="assign_claim",
    summary="Assign a claim to the best adjuster/team using skill-matching and workload-balancing",
    tags=["Routing"],
)
def assign_claim(claim_id: str):
    try:
        return handler.assign_claim(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("assign_claim error")
        raise HTTPException(status_code=500, detail=str(e))
