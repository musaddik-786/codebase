"""
vendor_qualification_router.py
────────────────────────────────
Tool / Endpoint map:
  get_vendor_master              GET  /api/vendor_qualification/vendor/{vendor_id}
  score_vendor_qualification     POST /api/vendor_qualification/score/{vendor_id}
"""

import logging
from fastapi import APIRouter

from vendor_qualification_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/vendor_qualification/vendor/{vendor_id}",
    operation_id="get_vendor_master",
    summary="Read vendor_master_input for a vendor",
    tags=["VendorQualification"],
)
def get_vendor_master(vendor_id: str):
    """Return the raw vendor_master_input record including license and eligibility fields."""
    record = handler.get_vendor_master(vendor_id)
    if not record:
        return {"status": "not_found", "vendor_id": vendor_id}
    return record


@router.post(
    "/api/vendor_qualification/score/{vendor_id}",
    operation_id="score_vendor_qualification",
    summary="Score vendor qualification against compliance criteria and update assignment_eligible",
    tags=["VendorQualification"],
)
def score_vendor_qualification(vendor_id: str):
    """
    Check license validity, insurance, certifications, and background checks.
    Use LLM to produce a qualification verdict and update assignment_eligible
    in vendor_master_input.
    """
    return handler.score_vendor_qualification(vendor_id)
