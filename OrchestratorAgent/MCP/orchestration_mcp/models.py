from typing import Optional
from pydantic import BaseModel


class SetOrchestrationStateRequest(BaseModel):
    current_stage: str
    status: Optional[str] = None
    last_action: Optional[str] = None


class CreateApprovalRequest(BaseModel):
    gate_type: str
    summary: str
    requested_by: str = "Orchestrator"


class DecideApprovalRequest(BaseModel):
    decision: str
    decided_by: str
    notes: Optional[str] = None
