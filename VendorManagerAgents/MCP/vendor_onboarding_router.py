"""
vendor_onboarding_router.py
────────────────────────────
FastAPI routes for the Vendor Onboarding MCP.

Tool / Endpoint map:
  list_vendor_applications      GET  /api/vendor_onboarding/applications
  get_vendor_application        GET  /api/vendor_onboarding/applications/{application_id}
  submit_vendor_application     POST /api/vendor_onboarding/applications
  approve_vendor_application     POST /api/vendor_onboarding/applications/{application_id}/approve
  reject_vendor_application      POST /api/vendor_onboarding/applications/{application_id}/reject
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from vendor_onboarding_mcp import handler
from vendor_onboarding_mcp.models import (
    RejectVendorApplicationRequest,
    SubmitVendorApplicationRequest,
)

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/vendor_onboarding/applications",
    operation_id="list_vendor_applications",
    summary="List vendor applications, optionally filtered by status",
    tags=["VendorOnboarding"],
)
def list_vendor_applications(status: Optional[str] = None):
    """Returns all vendor_applications rows, optionally filtered by status."""
    return handler.list_vendor_applications(status)


@router.get(
    "/api/vendor_onboarding/applications/{application_id}",
    operation_id="get_vendor_application",
    summary="Get a single vendor application by id",
    tags=["VendorOnboarding"],
)
def get_vendor_application(application_id: int):
    """Returns the vendor_applications row for the given id, or null."""
    return handler.get_vendor_application(application_id)


@router.post(
    "/api/vendor_onboarding/applications",
    operation_id="submit_vendor_application",
    summary="Submit a new vendor application",
    tags=["VendorOnboarding"],
)
def submit_vendor_application(body: SubmitVendorApplicationRequest):
    """Inserts a new vendor_applications row with status 'Pending'."""
    try:
        return handler.submit_vendor_application(
            body.name, body.specialty, body.location, body.license_number,
            body.license_expiry_date, body.contact_email, body.contact_phone, body.submitted_date,
        )
    except Exception as e:
        log.exception("submit_vendor_application error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/vendor_onboarding/applications/{application_id}/approve",
    operation_id="approve_vendor_application",
    summary="Approve a pending vendor application and provision a new vendor",
    tags=["VendorOnboarding"],
)
def approve_vendor_application(application_id: int):
    """
    Marks the application 'Approved', inserts a new vendors row, and a
    corresponding vendor_master_input row (status 'Active',
    assignment_eligible 'Yes', vis_score 70).
    """
    try:
        return handler.approve_vendor_application(application_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.exception("approve_vendor_application error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/vendor_onboarding/applications/{application_id}/reject",
    operation_id="reject_vendor_application",
    summary="Reject a pending vendor application",
    tags=["VendorOnboarding"],
)
def reject_vendor_application(application_id: int, body: RejectVendorApplicationRequest):
    """Marks the application 'Rejected' and stores the rejection reason."""
    try:
        return handler.reject_vendor_application(application_id, body.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.exception("reject_vendor_application error")
        raise HTTPException(status_code=500, detail=str(e))
