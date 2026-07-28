"""
vendor_capacity_router.py
──────────────────────────
Tool / Endpoint map:
  get_vendor_active_jobs      GET  /api/vendor_capacity/jobs/{vendor_id}
  manage_vendor_capacity      POST /api/vendor_capacity/manage/{vendor_id}
"""

import logging
from fastapi import APIRouter

from vendor_capacity_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/vendor_capacity/jobs/{vendor_id}",
    operation_id="get_vendor_active_jobs",
    summary="Read active vendor_jobs_input rows for a vendor",
    tags=["VendorCapacity"],
)
def get_vendor_active_jobs(vendor_id: str):
    """Return all active job records for a given vendor."""
    records = handler.get_vendor_active_jobs(vendor_id)
    return {"vendor_id": vendor_id, "active_job_count": len(records), "active_jobs": records}


@router.post(
    "/api/vendor_capacity/manage/{vendor_id}",
    operation_id="manage_vendor_capacity",
    summary="Evaluate vendor workload and throttle or re-enable assignment eligibility",
    tags=["VendorCapacity"],
)
def manage_vendor_capacity(vendor_id: str):
    """
    Compare active job count against the vendor's capacity_threshold.
    Throttle (set assignment_eligible='No') if at capacity, 'Conditional'
    if near capacity, 'Yes' if available. Update vendor_master_input.
    """
    return handler.manage_vendor_capacity(vendor_id)
