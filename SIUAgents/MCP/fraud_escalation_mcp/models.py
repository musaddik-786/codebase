from typing import Optional
from pydantic import BaseModel


class CreateSiuEscalationRequest(BaseModel):
    escalation_reason: str
    fraud_score: Optional[int] = None
    evidence_notes: Optional[str] = None
    escalated_by: str = "Adjuster"


class CreateSiuCaseRequest(BaseModel):
    assigned_investigator: str = "Unassigned"


class LogTimelineEventRequest(BaseModel):
    siu_case_id: str
    event_type: str
    status: str


class ForwardToSiuRequest(BaseModel):
    escalation_reason: str
    evidence_notes: Optional[str] = None
    escalated_by: str = "Adjuster"
