"""
siu_closure_router.py
──────────────────────
Tool / Endpoint map:
  get_siu_progress_tracker    GET  /api/siu_closure/progress/{siu_case_id}
  check_closure_readiness     POST /api/siu_closure/check/{siu_case_id}
"""

import logging
from fastapi import APIRouter

from siu_closure_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/siu_closure/progress/{siu_case_id}",
    operation_id="get_siu_progress_tracker",
    summary="Read siu_progress_tracker for an SIU case",
    tags=["SiuClosure"],
)
def get_siu_progress_tracker(siu_case_id: str):
    """Return the latest closure progress record for a given SIU case."""
    record = handler.get_siu_progress_tracker(siu_case_id)
    if not record:
        return {"status": "not_found", "siu_case_id": siu_case_id}
    return record


@router.post(
    "/api/siu_closure/check/{siu_case_id}",
    operation_id="check_closure_readiness",
    summary="Validate all investigation steps are complete before case closure",
    tags=["SiuClosure"],
)
def check_closure_readiness(siu_case_id: str):
    """
    Run the closure readiness checklist: evidence correlation, network analysis,
    behavioral analysis, final decision, and investigator report. Returns a
    closure verdict and persists to siu_progress_tracker.
    """
    return handler.check_closure_readiness(siu_case_id)
