"""
damage_assessment_router.py
────────────────────────────────
FastAPI routes for the Damage Assessment MCP.

Tool / Endpoint map:
  get_claim_details                  GET  /api/damage_assessment/claim/{claim_number}
  get_damage_items                   GET  /api/damage_assessment/items/{claim_number}
  write_damage_item                  POST /api/damage_assessment/items/{claim_number}
  analyze_damage_from_description    POST /api/damage_assessment/analyze/{claim_number}
  get_repair_costs                   GET  /api/damage_assessment/repair-costs/{claim_id}
  write_repair_cost                  POST /api/damage_assessment/repair-costs/{claim_id}
  get_replacement_costs              GET  /api/damage_assessment/replacement-costs/{claim_id}
  write_replacement_cost             POST /api/damage_assessment/replacement-costs/{claim_id}
  compute_and_save_repair_replacement POST /api/damage_assessment/compute-costs/{claim_number}
"""

import logging
from fastapi import APIRouter, HTTPException

from damage_assessment_mcp import handler
from damage_assessment_mcp.models import (
    DamageItemRequest,
    RepairCostRequest,
    ReplacementCostRequest,
)

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/damage_assessment/claim/{claim_number}",
    operation_id="get_claim_details",
    summary="Fetch a claim record",
    tags=["DamageAssessment"],
)
def get_claim_details(claim_number: str):
    """Returns the claims row for the given claim_number."""
    record = handler.get_claim_details(claim_number)
    if not record:
        raise HTTPException(status_code=404, detail=f"Claim {claim_number} not found")
    return record


@router.get(
    "/api/damage_assessment/items/{claim_number}",
    operation_id="get_damage_items",
    summary="Get damage items for a claim",
    tags=["DamageAssessment"],
)
def get_damage_items(claim_number: str):
    """Returns all damage_items rows for the given claim_number."""
    return handler.get_damage_items(claim_number)


@router.post(
    "/api/damage_assessment/items/{claim_number}",
    operation_id="write_damage_item",
    summary="Write a damage item for a claim",
    tags=["DamageAssessment"],
)
def write_damage_item(claim_number: str, body: DamageItemRequest):
    """Inserts a new damage_items row (damage_id auto-generated) for the given claim_number."""
    try:
        return handler.write_damage_item(claim_number, body.category, body.severity, body.estimated_cost, body.adjuster_notes)
    except Exception as e:
        log.exception("write_damage_item error")
        raise HTTPException(status_code=500, detail=str(e))




@router.post(
    "/api/damage_assessment/analyze/{claim_number}",
    operation_id="analyze_damage_from_description",
    summary="Identify damage categories and compute reference-bundle costs (does not save)",
    tags=["DamageAssessment"],
)
def analyze_damage_from_description(claim_number: str):
    """
    Returns 1-4 damage items with categories constrained to a validated
    loss-type map (Water→Flooring/Drywall/Insulation, Fire→Kitchen
    Cabinets/Countertops/Appliances, Storm→Roof Shingles/Siding/Gutters).
    Costs use reference bundle formula: materialCost = avgCost×0.25×(1+i×0.15),
    laborHours = 8+i×4, laborRate=$75/hr, diagnosticFee=$150, urgencyFactor=1.15
    for fire else 1.0.  LLM assigns severity and notes only.
    Returns identified_items WITHOUT writing to DB.
    """
    try:
        return handler.analyze_damage_from_description(claim_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("analyze_damage_from_description error")
        raise HTTPException(status_code=500, detail=str(e))



@router.get(
    "/api/damage_assessment/repair-costs/{claim_id}",
    operation_id="get_repair_costs",
    summary="Get all repair cost records for a claim",
    tags=["DamageAssessment"],
)
def get_repair_costs(claim_id: str):
    """Returns all repair_costs rows for the given claim_id."""
    return handler.get_repair_costs(claim_id)


@router.post(
    "/api/damage_assessment/repair-costs/{claim_id}",
    operation_id="write_repair_cost",
    summary="Write a repair cost record for a damage item",
    tags=["DamageAssessment"],
)
def write_repair_cost(claim_id: str, body: RepairCostRequest):
    """Inserts a repair_costs row for the given claim_id and item_id."""
    try:
        return handler.write_repair_cost(
            claim_id, body.item_id, body.item_type, body.material_cost,
            body.labor_hours, body.labor_rate, body.diagnostic_fee,
            body.urgency_factor, body.total_repair_estimate, body.notes,
        )
    except Exception as e:
        log.exception("write_repair_cost error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/damage_assessment/replacement-costs/{claim_id}",
    operation_id="get_replacement_costs",
    summary="Get all replacement cost records for a claim",
    tags=["DamageAssessment"],
)
def get_replacement_costs(claim_id: str):
    """Returns all replacement_costs rows for the given claim_id."""
    return handler.get_replacement_costs(claim_id)


@router.post(
    "/api/damage_assessment/replacement-costs/{claim_id}",
    operation_id="write_replacement_cost",
    summary="Write a replacement cost record for a damage item",
    tags=["DamageAssessment"],
)
def write_replacement_cost(claim_id: str, body: ReplacementCostRequest):
    """Inserts a replacement_costs row for the given claim_id and item_id."""
    try:
        return handler.write_replacement_cost(
            claim_id, body.item_id, body.item_type, body.replacement_material_cost,
            body.installation_hours, body.labor_rate, body.delivery_fee,
            body.disposal_fee, body.total_replacement_estimate, body.notes,
        )
    except Exception as e:
        log.exception("write_replacement_cost error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/damage_assessment/compute-costs/{claim_number}",
    operation_id="compute_and_save_repair_replacement",
    summary="Compute and save repair + replacement costs for all damage items",
    tags=["DamageAssessment"],
)
def compute_and_save_repair_replacement(claim_number: str):
    """
    For every existing damage_item for the claim, computes and saves both
    repair and replacement costs using the reference bundle formulas.
    Repair: materialCost×(1+laborHours×laborRate+diagnosticFee)×urgencyFactor.
    Replacement: materialCost×1.8, installHrs=laborHrs×0.7, +$250 delivery +$150 disposal.
    Guards against duplication — safe to call multiple times.
    Returns items_processed, repair_costs list, replacement_costs list.
    """
    try:
        return handler.compute_and_save_repair_replacement(claim_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("compute_and_save_repair_replacement error")
        raise HTTPException(status_code=500, detail=str(e))
