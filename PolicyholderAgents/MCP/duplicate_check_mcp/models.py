from pydantic import BaseModel
from typing import Optional


class CheckDuplicateClaimRequest(BaseModel):
    policy_number: str
    loss_type: str
    date_of_loss: Optional[str] = None
    description: Optional[str] = None


class RecentClaimsRequest(BaseModel):
    policy_number: str
    days: Optional[int] = 90
