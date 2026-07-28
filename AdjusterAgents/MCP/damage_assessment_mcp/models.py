from typing import Optional
from pydantic import BaseModel


class DamageItemRequest(BaseModel):
    category: str
    severity: str
    estimated_cost: float
    adjuster_notes: Optional[str] = None



class RepairCostRequest(BaseModel):
    item_id: str
    item_type: str
    material_cost: float
    labor_hours: float
    labor_rate: float = 75.0
    diagnostic_fee: float = 150.0
    urgency_factor: float = 1.0
    total_repair_estimate: float
    notes: Optional[str] = None


class ReplacementCostRequest(BaseModel):
    item_id: str
    item_type: str
    replacement_material_cost: float
    installation_hours: float
    labor_rate: float = 75.0
    delivery_fee: float = 250.0
    disposal_fee: float = 150.0
    total_replacement_estimate: float
    notes: Optional[str] = None
