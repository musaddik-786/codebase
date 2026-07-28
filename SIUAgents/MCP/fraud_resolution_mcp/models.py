from typing import Optional
from pydantic import BaseModel


class WriteSiuDecisionRequest(BaseModel):
    siu_case_id: str
    decision: str
    confidence: Optional[float] = None
    closed_date: Optional[str] = None


class ResolveSiuCaseRequest(BaseModel):
    siu_case_id: str
    decision: str
    confidence: Optional[float] = None
    notes: Optional[str] = None
