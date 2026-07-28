"""
loss_assessment_router.py
──────────────────────────────
FastAPI routes for the Loss Assessment MCP.

Tool / Endpoint map:
  get_loss_assessment   GET  /api/loss_assessment/assessment/{claim_number}
  write_loss_assessment POST /api/loss_assessment/assessment/{claim_number}
  get_loss_estimation    GET  /api/loss_assessment/estimation/{claim_id}
  write_loss_estimation  POST /api/loss_assessment/estimation/{claim_id}
  run_loss_assessment     POST /api/loss_assessment/run/{claim_number}
"""

import logging
from fastapi import APIRouter, HTTPException

from loss_assessment_mcp import handler
from loss_assessment_mcp.models import LossAssessmentRequest, LossEstimationRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/loss_assessment/assessment/{claim_number}",
    operation_id="get_loss_assessment",
    summary="Get the latest loss assessment for a claim",
    tags=["LossAssessment"],
)
def get_loss_assessment(claim_number: str):
    """Returns the most recent loss_assessments row for the given claim_number, or null."""
    return handler.get_loss_assessment(claim_number)


@router.post(
    "/api/loss_assessment/assessment/{claim_number}",
    operation_id="write_loss_assessment",
    summary="Write a loss assessment for a claim",
    tags=["LossAssessment"],
)
def write_loss_assessment(claim_number: str, body: LossAssessmentRequest):
    """Inserts a new loss_assessments row (assessment_id auto-generated) for the given claim_number."""
    try:
        return handler.write_loss_assessment(
            claim_number, body.total_parts_cost, body.total_labor_cost, body.depreciation_percent,
            body.deductible, body.subrogation_likelihood, body.system_recommendation,
            body.final_recommendation, body.confidence_score, body.adjuster_override, body.notes,
        )
    except Exception as e:
        log.exception("write_loss_assessment error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/loss_assessment/estimation/{claim_id}",
    operation_id="get_loss_estimation",
    summary="Get the latest loss estimation output for a claim",
    tags=["LossAssessment"],
)
def get_loss_estimation(claim_id: str):
    """Returns the most recent loss_estimation_outputs row for the given claim_id, or null."""
    return handler.get_loss_estimation(claim_id)


@router.post(
    "/api/loss_assessment/estimation/{claim_id}",
    operation_id="write_loss_estimation",
    summary="Write a loss estimation output for a claim",
    tags=["LossAssessment"],
)
def write_loss_estimation(claim_id: str, body: LossEstimationRequest):
    """Inserts a new loss_estimation_outputs row for the given claim_id."""
    try:
        return handler.write_loss_estimation(
            claim_id, body.ai_estimated_loss, body.deductible, body.net_payable, body.repair_recommended, body.confidence,
        )
    except Exception as e:
        log.exception("write_loss_estimation error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/loss_assessment/run/{claim_number}",
    operation_id="run_loss_assessment",
    summary="Run a full loss assessment for a claim",
    tags=["LossAssessment"],
)
def run_loss_assessment(claim_number: str):
    """
    Sums damage_items.estimated_cost for the claim (falling back to
    claims.estimated_cost if none recorded), applies a 30% labor cost
    heuristic, looks up the policy deductible, computes depreciation from
    claim severity, uses an LLM for subrogation likelihood and
    recommendations, computes ai_estimated_loss and net_payable, and writes
    both loss_assessments and loss_estimation_outputs rows.
    """
    try:
        return handler.run_loss_assessment(claim_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("run_loss_assessment error")
        raise HTTPException(status_code=500, detail=str(e))
