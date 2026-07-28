"""
verification_router.py
───────────────────────────
FastAPI routes for the Verification MCP.

Tool / Endpoint map:
  get_external_verifications  GET  /api/verification/verifications/{claim_id}
  create_verification          POST /api/verification/verifications/{claim_id}
  get_verification_details      GET  /api/verification/details/{verification_id}
  write_verification_detail     POST /api/verification/details/{verification_id}
  run_verification               POST /api/verification/run/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from verification_mcp import handler
from verification_mcp.models import CreateVerificationRequest, VerificationDetailRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/verification/verifications/{claim_id}",
    operation_id="get_external_verifications",
    summary="Get external verifications for a claim",
    tags=["Verification"],
)
def get_external_verifications(claim_id: str):
    """Returns all external_verifications rows for the given claim_id."""
    return handler.get_external_verifications(claim_id)


@router.post(
    "/api/verification/verifications/{claim_id}",
    operation_id="create_verification",
    summary="Create an external verification record for a claim",
    tags=["Verification"],
)
def create_verification(claim_id: str, body: CreateVerificationRequest):
    """Inserts a new external_verifications row (verification_id auto-generated) for the given claim_id."""
    try:
        return handler.create_verification(claim_id, body.type, body.status, body.result)
    except Exception as e:
        log.exception("create_verification error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/verification/details/{verification_id}",
    operation_id="get_verification_details",
    summary="Get verification details for a verification record",
    tags=["Verification"],
)
def get_verification_details(verification_id: str):
    """Returns all verification_details rows for the given verification_id."""
    return handler.get_verification_details(verification_id)


@router.post(
    "/api/verification/details/{verification_id}",
    operation_id="write_verification_detail",
    summary="Write a verification detail row",
    tags=["Verification"],
)
def write_verification_detail(verification_id: str, body: VerificationDetailRequest):
    """Inserts a new verification_details row for the given verification_id."""
    try:
        return handler.write_verification_detail(verification_id, body.field, body.expected, body.actual, body.flag, body.severity)
    except Exception as e:
        log.exception("write_verification_detail error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/verification/run/{claim_id}",
    operation_id="run_verification",
    summary="Run verification cross-checks for a claim",
    tags=["Verification"],
)
def run_verification(claim_id: str):
    """
    Runs a comprehensive four-pillar verification for the claim:
    1. Policy — status, date window, loss type vs coverage type, deductible
    2. Loss Facts — cause, date/time, occupancy, area, sudden-vs-gradual (from fnol_submissions)
    3. Documents — completeness and required types for the loss category
    4. External Data — weather alignment, drone assessment, STP vs fraud risk cross-check

    Each check is written to verification_details with a flag:
    "Match" / "Mismatch" / "Unable to Verify" (upstream data not yet available),
    plus a severity: "Critical" for the 3 hard policy facts (policy_exists,
    policy_status, date_of_loss_in_policy_window), "Advisory" for everything else.

    Returns a summary with pillar_summary, total_checks, match/mismatch counts,
    plus a deterministic coverage_verdict ("Confirmed" / "Flagged") and
    critical_issues — any non-Match Critical check flags the claim so the
    orchestrator can halt before Reserve/Settlement run.
    """
    try:
        return handler.run_verification(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("run_verification error")
        raise HTTPException(status_code=500, detail=str(e))
