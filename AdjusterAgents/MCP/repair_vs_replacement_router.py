# """
# repair_vs_replacement_router.py
# ─────────────────────────────────────
# FastAPI routes for the Repair vs Replacement MCP.

# Tool / Endpoint map:
#   get_estimates                GET  /api/repair_vs_replacement/estimates/{claim_id}
#   write_estimate               POST /api/repair_vs_replacement/estimates/{claim_id}
#   get_repair_cost_detail        GET  /api/repair_vs_replacement/repair_costs/{claim_id}
#   write_repair_cost             POST /api/repair_vs_replacement/repair_costs/{claim_id}
#   get_replacement_cost_detail   GET  /api/repair_vs_replacement/replacement_costs/{claim_id}
#   write_replacement_cost        POST /api/repair_vs_replacement/replacement_costs/{claim_id}
#   compare_repair_vs_replace     POST /api/repair_vs_replacement/compare/{claim_id}
# """

# import logging
# from fastapi import APIRouter, HTTPException

# from repair_vs_replacement_mcp import handler
# from repair_vs_replacement_mcp.models import (
#     CompareRequest,
#     EstimateRequest,
#     RepairCostRequest,
#     ReplacementCostRequest,
# )

# log = logging.getLogger(__name__)

# router = APIRouter()


# @router.get(
#     "/api/repair_vs_replacement/estimates/{claim_id}",
#     operation_id="get_estimates",
#     summary="Get repair-vs-replace estimates for a claim",
#     tags=["RepairVsReplacement"],
# )
# def get_estimates(claim_id: str):
#     """Returns all estimates rows for the given claim_id."""
#     return handler.get_estimates(claim_id)


# @router.post(
#     "/api/repair_vs_replacement/estimates/{claim_id}",
#     operation_id="write_estimate",
#     summary="Write a repair-vs-replace estimate for a claim",
#     tags=["RepairVsReplacement"],
# )
# def write_estimate(claim_id: str, body: EstimateRequest):
#     """Inserts a new estimates row for the given claim_id."""
#     try:
#         return handler.write_estimate(
#             claim_id, body.item_type, body.item_age, body.useful_life_remaining, body.repair_cost,
#             body.replacement_cost, body.labor_cost, body.material_cost, body.recommendation, body.confidence_score,
#         )
#     except Exception as e:
#         log.exception("write_estimate error")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get(
#     "/api/repair_vs_replacement/repair_costs/{claim_id}",
#     operation_id="get_repair_cost_detail",
#     summary="Get repair cost details for a claim",
#     tags=["RepairVsReplacement"],
# )
# def get_repair_cost_detail(claim_id: str):
#     """Returns all repair_costs rows for the given claim_id."""
#     return handler.get_repair_cost_detail(claim_id)


# @router.post(
#     "/api/repair_vs_replacement/repair_costs/{claim_id}",
#     operation_id="write_repair_cost",
#     summary="Write a repair cost detail row for a claim",
#     tags=["RepairVsReplacement"],
# )
# def write_repair_cost(claim_id: str, body: RepairCostRequest):
#     """Inserts a repair_costs row; total_repair_estimate is computed as
#     (material_cost + labor_hours*labor_rate + diagnostic_fee) * urgency_factor."""
#     try:
#         return handler.write_repair_cost(
#             body.item_id, claim_id, body.item_type, body.material_cost, body.labor_hours,
#             body.labor_rate, body.diagnostic_fee, body.urgency_factor, body.notes,
#         )
#     except Exception as e:
#         log.exception("write_repair_cost error")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get(
#     "/api/repair_vs_replacement/replacement_costs/{claim_id}",
#     operation_id="get_replacement_cost_detail",
#     summary="Get replacement cost details for a claim",
#     tags=["RepairVsReplacement"],
# )
# def get_replacement_cost_detail(claim_id: str):
#     """Returns all replacement_costs rows for the given claim_id."""
#     return handler.get_replacement_cost_detail(claim_id)


# @router.post(
#     "/api/repair_vs_replacement/replacement_costs/{claim_id}",
#     operation_id="write_replacement_cost",
#     summary="Write a replacement cost detail row for a claim",
#     tags=["RepairVsReplacement"],
# )
# def write_replacement_cost(claim_id: str, body: ReplacementCostRequest):
#     """Inserts a replacement_costs row; total_replacement_estimate is computed as
#     replacement_material_cost + installation_hours*labor_rate + delivery_fee + disposal_fee."""
#     try:
#         return handler.write_replacement_cost(
#             body.item_id, claim_id, body.item_type, body.replacement_material_cost, body.installation_hours,
#             body.labor_rate, body.delivery_fee, body.disposal_fee, body.notes,
#         )
#     except Exception as e:
#         log.exception("write_replacement_cost error")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post(
#     "/api/repair_vs_replacement/compare/{claim_id}",
#     operation_id="compare_repair_vs_replace",
#     summary="Compare repair vs replacement for an item and recommend a course of action",
#     tags=["RepairVsReplacement"],
# )
# def compare_repair_vs_replace(claim_id: str, body: CompareRequest):
#     """
#     Looks up existing repair_costs/replacement_costs for the claim+item_type
#     (or uses an LLM to estimate plausible costs if none exist), applies the
#     rule: if repair_cost > 0.6 * replacement_cost OR item_age >=
#     useful_life_remaining then recommend "Replace" else "Repair", computes a
#     confidence_score, writes an estimates row, and returns the comparison.
#     """
#     try:
#         return handler.compare_repair_vs_replace(claim_id, body.item_type, body.item_age, body.useful_life_remaining)
#     except Exception as e:
#         log.exception("compare_repair_vs_replace error")
#         raise HTTPException(status_code=500, detail=str(e))






"""
repair_vs_replacement_router.py
─────────────────────────────────────
FastAPI routes for the Repair vs Replacement MCP.

Tool / Endpoint map:
  get_estimates                GET  /api/repair_vs_replacement/estimates/{claim_id}
  write_estimate               POST /api/repair_vs_replacement/estimates/{claim_id}
  get_repair_cost_detail        GET  /api/repair_vs_replacement/repair_costs/{claim_id}
  write_repair_cost             POST /api/repair_vs_replacement/repair_costs/{claim_id}
  get_replacement_cost_detail   GET  /api/repair_vs_replacement/replacement_costs/{claim_id}
  write_replacement_cost        POST /api/repair_vs_replacement/replacement_costs/{claim_id}
  compare_repair_vs_replace     POST /api/repair_vs_replacement/compare/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from repair_vs_replacement_mcp import handler
# from repair_vs_replacement_mcp.models import (
#     CompareRequest,
#     EstimateRequest,
#     RepairCostRequest,
#     ReplacementCostRequest,
# )

from repair_vs_replacement_mcp.models import (
    CompareRequest,
    EstimateRequest,
    RepairCostRequest,
    ReplacementCostRequest,
    RepairVsReplacementDecisionRequest,
    RepairVsReplacementDecisionUpdateRequest,
)

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/repair_vs_replacement/estimates/{claim_id}",
    operation_id="get_estimates",
    summary="Get repair-vs-replace estimates for a claim",
    tags=["RepairVsReplacement"],
)
def get_estimates(claim_id: str):
    """Returns all estimates rows for the given claim_id."""
    return handler.get_estimates(claim_id)


@router.post(
    "/api/repair_vs_replacement/estimates/{claim_id}",
    operation_id="write_estimate",
    summary="Write a repair-vs-replace estimate for a claim",
    tags=["RepairVsReplacement"],
)
def write_estimate(claim_id: str, body: EstimateRequest):
    """Inserts a new estimates row for the given claim_id."""
    try:
        return handler.write_estimate(
            claim_id, body.item_type, body.item_age, body.useful_life_remaining, body.repair_cost,
            body.replacement_cost, body.labor_cost, body.material_cost, body.recommendation, body.confidence_score,
        )
    except Exception as e:
        log.exception("write_estimate error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/repair_vs_replacement/repair_costs/{claim_id}",
    operation_id="get_repair_cost_detail",
    summary="Get repair cost details for a claim",
    tags=["RepairVsReplacement"],
)
def get_repair_cost_detail(claim_id: str):
    """Returns all repair_costs rows for the given claim_id."""
    return handler.get_repair_cost_detail(claim_id)


@router.post(
    "/api/repair_vs_replacement/repair_costs/{claim_id}",
    operation_id="write_repair_cost",
    summary="Write a repair cost detail row for a claim",
    tags=["RepairVsReplacement"],
)
def write_repair_cost(claim_id: str, body: RepairCostRequest):
    """Inserts a repair_costs row; total_repair_estimate is computed as
    (material_cost + labor_hours*labor_rate + diagnostic_fee) * urgency_factor."""
    try:
        return handler.write_repair_cost(
            body.item_id, claim_id, body.item_type, body.material_cost, body.labor_hours,
            body.labor_rate, body.diagnostic_fee, body.urgency_factor, body.notes,
        )
    except Exception as e:
        log.exception("write_repair_cost error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/repair_vs_replacement/replacement_costs/{claim_id}",
    operation_id="get_replacement_cost_detail",
    summary="Get replacement cost details for a claim",
    tags=["RepairVsReplacement"],
)
def get_replacement_cost_detail(claim_id: str):
    """Returns all replacement_costs rows for the given claim_id."""
    return handler.get_replacement_cost_detail(claim_id)


@router.post(
    "/api/repair_vs_replacement/replacement_costs/{claim_id}",
    operation_id="write_replacement_cost",
    summary="Write a replacement cost detail row for a claim",
    tags=["RepairVsReplacement"],
)
def write_replacement_cost(claim_id: str, body: ReplacementCostRequest):
    """Inserts a replacement_costs row; total_replacement_estimate is computed as
    replacement_material_cost + installation_hours*labor_rate + delivery_fee + disposal_fee."""
    try:
        return handler.write_replacement_cost(
            body.item_id, claim_id, body.item_type, body.replacement_material_cost, body.installation_hours,
            body.labor_rate, body.delivery_fee, body.disposal_fee, body.notes,
        )
    except Exception as e:
        log.exception("write_replacement_cost error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/repair_vs_replacement/compare/{claim_number}",
    operation_id="compare_repair_vs_replace",
    summary="Compare repair vs replacement for an item and recommend a course of action",
    tags=["RepairVsReplacement"],
)
def compare_repair_vs_replace(claim_number: str, body: CompareRequest):
    """
    Looks up existing repair_costs/replacement_costs for the claim+item_type
    (or uses an LLM to estimate plausible costs if none exist), applies the
    rule: if repair_cost > 0.6 * replacement_cost OR item_age >=
    useful_life_remaining then recommend "Replace" else "Repair", computes a
    confidence_score, writes an estimates row, and returns the comparison.
    """
    try:
        return handler.compare_repair_vs_replace(claim_number, body.item_age, body.useful_life_remaining)
    except Exception as e:
        log.exception("compare_repair_vs_replace error")
        raise HTTPException(status_code=500, detail=str(e))




@router.post(
    "/api/repair_vs_replacement/decision",
    operation_id="write_repair_vs_replacement_decision",
    summary="Write repair vs replacement decision record",
    tags=["RepairVsReplacement"],
)
def write_repair_vs_replacement_decision(body: RepairVsReplacementDecisionRequest):
    try:
        return handler.write_repair_vs_replacement_decision(
            body.claim_number,
            body.recommended_action,
            body.ai_generated_message,
        )
    except Exception as e:
        log.exception("write decision error")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )




@router.post(
    "/api/repair_vs_replacement/decision/{claim_number}",
    operation_id="update_repair_vs_replacement_decision",
    summary="Record Adjuster's Repair vs Replacement decision",
    tags=["RepairVsReplacement"],
)
def update_repair_vs_replacement_decision(
    claim_number: str,
    body: RepairVsReplacementDecisionUpdateRequest,
):
    try:
        return handler.update_repair_vs_replacement_decision(
            claim_number,
            body.decision,
        )
    except Exception as e:
        log.exception("update decision error")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
