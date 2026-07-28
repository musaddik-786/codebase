from typing import Optional
from pydantic import BaseModel


class CreateLegalEscalationRequest(BaseModel):
    siu_case_id: str
    reason: str
    fraud_score: Optional[int] = None
    referred_by: str = "SIU Investigator"


class UpdateLegalEscalationOutcomeRequest(BaseModel):
    status: str
    outcome: Optional[str] = None
