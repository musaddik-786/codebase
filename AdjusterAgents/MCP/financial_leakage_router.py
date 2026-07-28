# """
# financial_leakage_router.py
# ─────────────────────────────
# Tool / Endpoint map:
#   get_cost_variance  GET  /api/financial_leakage/cost_variance/{vendor_id}
#   score_leakage      POST /api/financial_leakage/score/{claim_id}
# """

# import logging
# from fastapi import APIRouter, HTTPException

# from financial_leakage_mcp import handler

# log = logging.getLogger(__name__)

# router = APIRouter()


# @router.get(
#     "/api/financial_leakage/cost_variance/{vendor_id}",
#     operation_id="get_cost_variance",
#     summary="Read cost_variance_output records for a vendor",
#     tags=["FinancialLeakage"],
# )
# def get_cost_variance(vendor_id: str):
#     records = handler.get_cost_variance(vendor_id)
#     return {"vendor_id": vendor_id, "cost_variance_output": records}


# @router.post(
#     "/api/financial_leakage/score/{claim_id}",
#     operation_id="score_leakage",
#     summary="Score financial leakage risk across all vendor line items for a claim",
#     tags=["FinancialLeakage"],
# )
# def score_leakage(claim_id: str):
#     try:
#         return handler.score_leakage(claim_id)
#     except Exception as e:
#         log.exception("score_leakage error")
#         raise HTTPException(status_code=500, detail=str(e))



# new code with adjuster input also 
"""
financial_leakage_router.py
─────────────────────────────
Tool / Endpoint map:
  get_cost_variance                GET  /api/financial_leakage/cost_variance/{vendor_id}
  score_leakage                    POST /api/financial_leakage/score/{claim_id}
  get_financial_leakage_score      GET  /api/financial_leakage/result/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from financial_leakage_mcp import handler
from pydantic import BaseModel
from typing import Literal

log = logging.getLogger(__name__)

router = APIRouter()

class AdjusterOverrideRequest(BaseModel):
    adjuster_override_risk_level: Literal[
        "Low",
        "Medium",
        "High",
        "Critical"
    ]
    adjuster_notes: str

@router.get(
    "/api/financial_leakage/cost_variance/{vendor_id}",
    operation_id="get_cost_variance",
    summary="Read cost_variance_output records for a vendor",
    tags=["FinancialLeakage"],
)
def get_cost_variance(vendor_id: str):
    records = handler.get_cost_variance(vendor_id)
    return {"vendor_id": vendor_id, "cost_variance_output": records}


@router.post(
    "/api/financial_leakage/score/{claim_id}",
    operation_id="score_leakage",
    summary="Score financial leakage risk across all vendor line items for a claim",
    tags=["FinancialLeakage"],
)
def score_leakage(claim_id: str):
    try:
        return handler.score_leakage(claim_id)
    except Exception as e:
        log.exception("score_leakage error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/financial_leakage/result/{claim_id}",
    operation_id="get_financial_leakage_score",
    summary="Get stored financial leakage score",
    tags=["FinancialLeakage"],
)
def get_financial_leakage_score(claim_id: str):
    try:
        result = handler.get_financial_leakage_score(claim_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No financial leakage score found for claim {claim_id}"
            )

        return result

    except HTTPException:
        raise

    except Exception as e:
        log.exception("get_financial_leakage_score error")
        raise HTTPException(status_code=500, detail=str(e))

@router.put(
    "/api/financial_leakage/override/{claim_id}",
    operation_id="update_adjuster_override",
    summary="Save adjuster override details",
    tags=["FinancialLeakage"],
)
def update_adjuster_override(
    claim_id: str,
    request: AdjusterOverrideRequest,
):
    try:
        return handler.update_adjuster_override(
            claim_id=claim_id,
            adjuster_override_risk_level=request.adjuster_override_risk_level,
            adjuster_notes=request.adjuster_notes,
        )

    except Exception as e:
        log.exception("update_adjuster_override error")
        raise HTTPException(status_code=500, detail=str(e))