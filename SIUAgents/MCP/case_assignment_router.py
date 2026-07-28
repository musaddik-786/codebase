"""
case_assignment_router.py
──────────────────────────
Tool / Endpoint map:
  get_siu_case_master   GET  /api/case_assignment/case/{claim_id}
  assign_investigator   POST /api/case_assignment/assign/{claim_id}
"""

import logging
from fastapi import APIRouter

from case_assignment_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/case_assignment/case/{claim_id}",
    operation_id="get_siu_case_master",
    summary="Read siu_case_master for a claim",
    tags=["CaseAssignment"],
)
def get_siu_case_master(claim_id: str):
    """Return the latest SIU case record for a given claim."""
    record = handler.get_siu_case_master(claim_id)
    if not record:
        return {"status": "not_found", "claim_id": claim_id}
    return record


@router.post(
    "/api/case_assignment/assign/{claim_id}",
    operation_id="assign_investigator",
    summary="Assign an SIU investigator to a claim using skill and workload matching",
    tags=["CaseAssignment"],
)
def assign_investigator(claim_id: str):
    """
    Select the best available investigator based on loss type specialization
    and current workload, then update siu_case_master.
    """
    return handler.assign_investigator(claim_id)
