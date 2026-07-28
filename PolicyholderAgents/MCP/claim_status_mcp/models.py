from pydantic import BaseModel
from typing import Optional


class AdvanceClaimStageRequest(BaseModel):
    claim_number: str
    new_stage: int
    stage_name: str
    sub_status: Optional[str] = None


class LogPolicyholderActionRequest(BaseModel):
    claim_number: str
    action_type: str
    action_label: str
    details: Optional[str] = None
