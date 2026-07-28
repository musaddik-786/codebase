"""
vendor_matching_router.py
───────────────────────────
FastAPI routes for the Vendor Matching MCP.

Tool / Endpoint map:
  get_vendors                 GET  /api/vendor_matching/vendors
  get_vendor_master            GET  /api/vendor_matching/vendor_master/{vendor_id}
  match_vendor_for_claim       GET  /api/vendor_matching/match/{claim_id}
  assign_vendor_to_claim       POST /api/vendor_matching/assign/{claim_id}
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from vendor_matching_mcp import handler
from vendor_matching_mcp.models import AssignVendorRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/vendor_matching/vendors",
    operation_id="get_vendors",
    summary="List vendors, optionally filtered by specialty and/or city",
    tags=["VendorMatching"],
)
def get_vendors(specialty: Optional[str] = None, city: Optional[str] = None):
    """Returns vendors rows, ranked by rating desc and avg_turnaround_days asc."""
    return handler.get_vendors(specialty, city)


@router.get(
    "/api/vendor_matching/vendor_master/{vendor_id}",
    operation_id="get_vendor_master",
    summary="Get a vendor_master_input record by vendor_id",
    tags=["VendorMatching"],
)
def get_vendor_master(vendor_id: str):
    """Returns the vendor_master_input row for the given vendor_id, or null."""
    return handler.get_vendor_master(vendor_id)


@router.get(
    "/api/vendor_matching/match/{claim_id}",
    operation_id="match_vendor_for_claim",
    summary="Find top vendor candidates for a claim",
    tags=["VendorMatching"],
)
def match_vendor_for_claim(claim_id: str):
    """
    Reads the claim's loss_type/location, maps loss_type to a vendor
    specialty heuristically, and returns the top 3 candidate vendors ranked
    by rating desc then avg_turnaround_days asc.
    """
    try:
        return handler.match_vendor_for_claim(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("match_vendor_for_claim error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/vendor_matching/assign/{claim_id}",
    operation_id="assign_vendor_to_claim",
    summary="Assign a vendor to a claim",
    tags=["VendorMatching"],
)
def assign_vendor_to_claim(claim_id: str, body: AssignVendorRequest):
    """Upserts a vendor_assignment row for the claim (status 'Assigned', sla_status 'On Track')."""
    try:
        return handler.assign_vendor_to_claim(claim_id, body.vendor_id, body.vendor_type)
    except Exception as e:
        log.exception("assign_vendor_to_claim error")
        raise HTTPException(status_code=500, detail=str(e))
