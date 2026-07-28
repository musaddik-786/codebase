from typing import Optional
from pydantic import BaseModel


class CreateVendorEscalationRequest(BaseModel):
    claim_id: str
    vendor_id: str
    severity: str
    message: str
    created_by: str = "Vendor Manager"


class EscalateOverdueJobsRequest(BaseModel):
    vendor_id: Optional[str] = None
