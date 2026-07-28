"""
segmentation_router.py
────────────────────────
FastAPI routes for the Claim Segmentation / STP Classification MCP.

Tool / Endpoint map:
  get_claim_for_segmentation  GET  /api/segmentation/claim/{claim_number}
  compute_stp_score            POST /api/segmentation/compute/{claim_number}
  get_segmentation_result      GET  /api/segmentation/result/{claim_number}
  get_stp_classification       GET  /api/segmentation/stp/{claim_number}
"""

import logging
from fastapi import APIRouter, HTTPException

from segmentation_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/segmentation/claim/{claim_number}",
    operation_id="get_claim_for_segmentation",
    summary="Fetch a claim record for segmentation",
    tags=["Segmentation"],
)
def get_claim_for_segmentation(claim_number: str):
    """
    Returns the claims row for the given claim_number, used as input to
    the STP scoring computation.
    """
    record = handler.get_claim_for_segmentation(claim_number)
    if not record:
        raise HTTPException(status_code=404, detail=f"Claim {claim_number} not found")
    return record


@router.post(
    "/api/segmentation/compute/{claim_number}",
    operation_id="compute_stp_score",
    summary="Compute and save the STP score/classification for a claim",
    tags=["Segmentation"],
)
def compute_stp_score(claim_number: str):
    """
    Computes a rule-based readiness score, fraud ambiguity, subrogation
    likelihood, and vendor involvement score (VIS) for the claim, derives
    a weighted stp_score (0-100) and stp_category in
    {"Full STP", "Fast Track", "Vendor STP", "Manual Review"}, and persists
    the result to stp_classification and segmentation_result_output.
    """
    try:
        return handler.compute_stp_score(claim_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("compute_stp_score error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/segmentation/result/{claim_number}",
    operation_id="get_segmentation_result",
    summary="Get the most recent segmentation result for a claim",
    tags=["Segmentation"],
)
def get_segmentation_result(claim_number: str):
    """
    Returns the most recently computed segmentation_result_output row
    for the given claim_number, or null if none exist.
    """
    return handler.get_segmentation_result(claim_number)


@router.get(
    "/api/segmentation/stp/{claim_number}",
    operation_id="get_stp_classification",
    summary="Get the most recent STP classification for a claim",
    tags=["Segmentation"],
)
def get_stp_classification(claim_number: str):
    """
    Returns the most recently computed stp_classification row for the
    given claim_number, or null if none exist.
    """
    return handler.get_stp_classification(claim_number)
