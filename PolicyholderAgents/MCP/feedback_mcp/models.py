from pydantic import BaseModel
from typing import Optional


class WriteCustomerFeedbackRequest(BaseModel):
    claim_number: str
    comment: str
    claim_id: Optional[str] = None
    stage_number: Optional[int] = None
    stage_name: Optional[str] = None


class UpdateSentimentTrackerRequest(BaseModel):
    claim_number: str
    policyholder_name: Optional[str] = None
