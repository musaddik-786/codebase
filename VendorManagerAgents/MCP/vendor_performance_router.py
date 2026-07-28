"""
vendor_performance_router.py
─────────────────────────────────
FastAPI routes for the Vendor Performance MCP.

Tool / Endpoint map:
  get_vendor_jobs                      GET  /api/vendor_performance/jobs/{vendor_id}
  record_vendor_rating                  POST /api/vendor_performance/rating/{vendor_id}
  compute_vendor_performance_score       POST /api/vendor_performance/score/{vendor_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from vendor_performance_mcp import handler
from vendor_performance_mcp.models import RecordVendorRatingRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/vendor_performance/jobs/{vendor_id}",
    operation_id="get_vendor_jobs",
    summary="List vendor_jobs_input rows for a vendor",
    tags=["VendorPerformance"],
)
def get_vendor_jobs(vendor_id: str):
    """Returns vendor_jobs_input rows for the given vendor_id."""
    return handler.get_vendor_jobs(vendor_id)


@router.post(
    "/api/vendor_performance/rating/{vendor_id}",
    operation_id="record_vendor_rating",
    summary="Record a rating/feedback for a vendor",
    tags=["VendorPerformance"],
)
def record_vendor_rating(vendor_id: str, body: RecordVendorRatingRequest):
    """Inserts a new vendor_rating_input row."""
    try:
        return handler.record_vendor_rating(vendor_id, body.rating, body.feedback)
    except Exception as e:
        log.exception("record_vendor_rating error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/vendor_performance/score/{vendor_id}",
    operation_id="compute_vendor_performance_score",
    summary="Compute the Vendor Intelligence Score (VIS) for a vendor",
    tags=["VendorPerformance"],
)
def compute_vendor_performance_score(vendor_id: str):
    """
    Computes sla_score (job completion rate, adjusted for overdue jobs),
    quality (avg rating scaled to 0-100), and cost_efficiency (from
    cost_variance_output variance), averages them into vis, upserts
    vendor_performance_score_output, and updates
    vendor_master_input.vis_score.
    """
    try:
        return handler.compute_vendor_performance_score(vendor_id)
    except Exception as e:
        log.exception("compute_vendor_performance_score error")
        raise HTTPException(status_code=500, detail=str(e))
