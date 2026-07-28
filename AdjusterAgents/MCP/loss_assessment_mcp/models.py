from typing import Optional
from pydantic import BaseModel


class LossAssessmentRequest(BaseModel):
    total_parts_cost: float
    total_labor_cost: float
    depreciation_percent: float
    deductible: float
    subrogation_likelihood: str
    system_recommendation: str
    final_recommendation: str
    confidence_score: float
    adjuster_override: Optional[str] = None
    notes: Optional[str] = None


class LossEstimationRequest(BaseModel):
    ai_estimated_loss: float
    deductible: float
    net_payable: float
    repair_recommended: str
    confidence: float
