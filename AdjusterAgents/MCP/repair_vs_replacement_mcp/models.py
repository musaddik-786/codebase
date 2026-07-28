# from typing import Optional
# from pydantic import BaseModel


# class EstimateRequest(BaseModel):
#     item_type: str
#     item_age: int
#     useful_life_remaining: int
#     repair_cost: float
#     replacement_cost: float
#     labor_cost: float
#     material_cost: float
#     recommendation: str
#     confidence_score: float


# class RepairCostRequest(BaseModel):
#     item_id: str
#     item_type: str
#     material_cost: float
#     labor_hours: float
#     labor_rate: float
#     diagnostic_fee: float
#     urgency_factor: float
#     notes: Optional[str] = None


# class ReplacementCostRequest(BaseModel):
#     item_id: str
#     item_type: str
#     replacement_material_cost: float
#     installation_hours: float
#     labor_rate: float
#     delivery_fee: float
#     disposal_fee: float
#     notes: Optional[str] = None


# class CompareRequest(BaseModel):
#     item_type: str
#     item_age: int
#     useful_life_remaining: int


from typing import Optional
from pydantic import BaseModel


class EstimateRequest(BaseModel):
    item_type: str
    item_age: int
    useful_life_remaining: int
    repair_cost: float
    replacement_cost: float
    labor_cost: float
    material_cost: float
    recommendation: str
    confidence_score: float


class RepairCostRequest(BaseModel):
    item_id: str
    item_type: str
    material_cost: float
    labor_hours: float
    labor_rate: float
    diagnostic_fee: float
    urgency_factor: float
    notes: Optional[str] = None


class ReplacementCostRequest(BaseModel):
    item_id: str
    item_type: str
    replacement_material_cost: float
    installation_hours: float
    labor_rate: float
    delivery_fee: float
    disposal_fee: float
    notes: Optional[str] = None


class CompareRequest(BaseModel):
    # item_type: str
    item_age: int
    useful_life_remaining: int



class RepairVsReplacementDecisionRequest(BaseModel):
    claim_number: str
    recommended_action: str
    ai_generated_message: str



class RepairVsReplacementDecisionUpdateRequest(BaseModel):
    decision: str

    