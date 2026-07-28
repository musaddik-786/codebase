from typing import Optional
from pydantic import BaseModel


class RecordVendorCostRequest(BaseModel):
    claim_id: str
    estimated_cost: float
    actual_cost: Optional[float] = None
