"""
vendor_escalation_router.py
────────────────────────────────
FastAPI routes for the Vendor Escalation MCP.

Tool / Endpoint map:
  create_vendor_escalation  POST /api/vendor_escalation/escalations
  get_vendor_escalations    GET  /api/vendor_escalation/escalations
  escalate_overdue_jobs      POST /api/vendor_escalation/escalate_overdue
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from vendor_escalation_mcp import handler
from vendor_escalation_mcp.models import CreateVendorEscalationRequest, EscalateOverdueJobsRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/vendor_escalation/escalations",
    operation_id="create_vendor_escalation",
    summary="Create a vendor escalation log entry",
    tags=["VendorEscalation"],
)
def create_vendor_escalation(body: CreateVendorEscalationRequest):
    """Inserts a new escalation_log_output row."""
    try:
        return handler.create_vendor_escalation(
            body.claim_id, body.vendor_id, body.severity, body.message, body.created_by,
        )
    except Exception as e:
        log.exception("create_vendor_escalation error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/vendor_escalation/escalations",
    operation_id="get_vendor_escalations",
    summary="List vendor escalations, optionally filtered by vendor_id/claim_id",
    tags=["VendorEscalation"],
)
def get_vendor_escalations(vendor_id: Optional[str] = None, claim_id: Optional[str] = None):
    """Returns escalation_log_output rows, optionally filtered."""
    return handler.get_vendor_escalations(vendor_id, claim_id)


@router.post(
    "/api/vendor_escalation/escalate_overdue",
    operation_id="escalate_overdue_jobs",
    summary="Scan for overdue vendor jobs and create escalations",
    tags=["VendorEscalation"],
)
def escalate_overdue_jobs(body: EscalateOverdueJobsRequest):
    """
    Scans vendor_jobs_input for rows with sla_status='Overdue' and
    active='Yes' (optionally filtered by vendor_id), creates an
    escalation_log_output row (severity 'High') for each, and
    upserts a job_status_update_output row (escalation_flag 'Yes',
    priority 'High') for each affected claim.
    """
    try:
        return handler.escalate_overdue_jobs(body.vendor_id)
    except Exception as e:
        log.exception("escalate_overdue_jobs error")
        raise HTTPException(status_code=500, detail=str(e))
