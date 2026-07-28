"""
claim_classification_router.py
─────────────────────────────────
FastAPI routes for the Claim Classification MCP.

Tool / Endpoint map:
  get_claim_details          GET  /api/claim_classification/claim/{claim_number}
  classify_claim             POST /api/claim_classification/classify/{claim_number}
  save_classification        POST /api/claim_classification/save/{claim_number}
  get_claim_classification   GET  /api/claim_classification/result/{claim_number}
"""

import logging
from fastapi import APIRouter, HTTPException, Query

from claim_classification_mcp import handler
from claim_classification_mcp.handler import FraudScoreUnavailableError

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/claim_classification/claim/{claim_number}",
    operation_id="get_claim_details",
    summary="Fetch a claim record for classification",
    tags=["ClaimClassification"],
)
def get_claim_details(claim_number: str):
    """Returns the claims row for the given claim_number."""
    record = handler.get_claim_details(claim_number)
    if not record:
        raise HTTPException(status_code=404, detail=f"Claim {claim_number} not found")
    return record


@router.post(
    "/api/claim_classification/classify/{claim_number}",
    operation_id="classify_claim",
    summary="Deterministically classify claim complexity and routing (does not save)",
    tags=["ClaimClassification"],
)
def classify_claim(claim_number: str):
    """
    Determines complexity ("Simple"/"Moderate"/"Complex") and routing
    ("Fast Track"/"Standard"/"Specialist Review") using cost thresholds
    and the claim's fraud score from fraud_risk_snapshots.

    Returns HTTP 422 if the fraud score cannot be retrieved — routing is
    never performed on fabricated data (missing data ≠ score 0).
    Returns the result without persisting — call save_classification to persist.
    """
    try:
        return handler.classify_claim(claim_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FraudScoreUnavailableError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "fraud_score_unavailable",
                "message": str(e),
                "action_required": "Run fraud screening for this claim before classification.",
            },
        )
    except Exception as e:
        log.exception("classify_claim error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/claim_classification/save/{claim_number}",
    operation_id="save_classification",
    summary="Persist a classification result to claim_triage and update claims.complexity",
    tags=["ClaimClassification"],
)
def save_classification(
    claim_number: str,
    complexity: str = Query(..., description="Claim complexity: Simple, Moderate, or Complex"),
    routing: str = Query(..., description="Routing track: Fast Track, Standard, or Specialist Review"),
):
    """
    Inserts the given complexity and routing into claim_triage and updates
    claims.complexity for the given claim_number.
    """
    try:
        return handler.save_classification(claim_number, complexity, routing)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FraudScoreUnavailableError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "fraud_score_unavailable",
                "message": str(e),
                "action_required": "Run fraud screening for this claim before saving classification.",
            },
        )
    except Exception as e:
        log.exception("save_classification error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/claim_classification/result/{claim_number}",
    operation_id="get_claim_classification",
    summary="Get the most recent classification result for a claim",
    tags=["ClaimClassification"],
)
def get_claim_classification(claim_number: str):
    """Returns the most recent claim_triage row for the given claim_number, or null."""
    return handler.get_claim_classification(claim_number)


@router.post(
    "/api/claim_classification/intake-validate/{claim_number}",
    operation_id="run_intake_validation",
    summary="Validate 7 mandatory FNOL fields and write intake_validation_result_output",
    tags=["ClaimClassification"],
)
def run_intake_validation(claim_number: str):
    """
    Checks 7 mandatory FNOL fields (policy_number, policyholder_name, loss_type,
    short_description, location, date_of_loss, severity).
    completeness_score = (filled / 7) * 100.
    passed = completeness_score >= 85 AND no blocking failure.
    Blocking failures: missing short_description, missing location, coverage == 0.
    Writes result to intake_validation_result_output. Run before compute_stp_score.
    """
    try:
        return handler.run_intake_validation(claim_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("run_intake_validation error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/claim_classification/stp-score/{claim_number}",
    operation_id="compute_stp_score",
    summary="Compute 8-factor weighted STP score and determine routing path",
    tags=["ClaimClassification"],
)
def compute_stp_score(claim_number: str):
    """
    Computes STP score using 8 weighted factors from the reference bundle formula:
      fnolCompleteness×20%, readiness×15%, coverage×15%, severity×10%,
      fraudAmbiguity×10%, subrogationRisk×10%, VIS×15%, similarityIndex×5%
    STP category: ≥85+Low fraud+no high subrogation→Full STP, ≥70→Vendor STP,
      ≥50→Fast Track, else→Manual. High/Critical severity → always Manual.
    Routing: Full STP→Fast Track, Vendor/Fast Track STP→Standard, Manual→Specialist Review.
    Saves to stp_score_input_factors, stp_calculation_result, segmentation_result_output.
    Returns 422 if fraud score is unavailable.
    """
    try:
        return handler.compute_stp_score(claim_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FraudScoreUnavailableError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "fraud_score_unavailable",
                "message": str(e),
                "action_required": "Run fraud screening before computing STP score.",
            },
        )
    except Exception as e:
        log.exception("compute_stp_score error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/claim_classification/stp-result/{claim_number}",
    operation_id="get_stp_result",
    summary="Get the most recent STP calculation result for a claim",
    tags=["ClaimClassification"],
)
def get_stp_result(claim_number: str):
    """Returns the most recent stp_calculation_result row for the given claim_number, or null."""
    return handler.get_stp_result(claim_number)


@router.get(
    "/api/claim_classification/intake-result/{claim_number}",
    operation_id="get_intake_validation_result",
    summary="Get the most recent intake validation result for a claim",
    tags=["ClaimClassification"],
)
def get_intake_validation_result(claim_number: str):
    """Returns the most recent intake_validation_result_output row for the given claim_number, or null."""
    return handler.get_intake_validation_result(claim_number)
