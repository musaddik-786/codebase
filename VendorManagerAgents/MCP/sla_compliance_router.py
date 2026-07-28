"""
sla_compliance_router.py
─────────────────────────────
FastAPI routes for the SLA Compliance MCP.

Tool / Endpoint map:
  get_vendor_jobs_sla     GET  /api/sla_compliance/jobs/{vendor_id}
  compute_sla_compliance  POST /api/sla_compliance/compliance/{vendor_id}
  get_sla_tracker         GET  /api/sla_compliance/tracker/{vendor_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from sla_compliance_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/sla_compliance/jobs/{vendor_id}",
    operation_id="get_vendor_jobs_sla",
    summary="List vendor_jobs_input rows for a vendor (SLA view)",
    tags=["SLACompliance"],
)
def get_vendor_jobs_sla(vendor_id: str):
    """Returns vendor_jobs_input rows for the given vendor_id."""
    return handler.get_vendor_jobs_sla(vendor_id)


@router.post(
    "/api/sla_compliance/compliance/{vendor_id}",
    operation_id="compute_sla_compliance",
    summary="Compute SLA compliance percentage for a vendor",
    tags=["SLACompliance"],
)
def compute_sla_compliance(vendor_id: str):
    """
    Computes the percentage of vendor_jobs_input rows with sla_status !=
    'Overdue', derives placeholder avg_response_time/avg_completion_time
    from the vendor's avg_turnaround_days, and upserts sla_tracker_output.
    """
    try:
        return handler.compute_sla_compliance(vendor_id)
    except Exception as e:
        log.exception("compute_sla_compliance error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/sla_compliance/tracker/{vendor_id}",
    operation_id="get_sla_tracker",
    summary="Get the latest sla_tracker_output record for a vendor",
    tags=["SLACompliance"],
)
def get_sla_tracker(vendor_id: str):
    """Returns the sla_tracker_output row for the given vendor_id, or null."""
    return handler.get_sla_tracker(vendor_id)
