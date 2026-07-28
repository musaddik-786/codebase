from typing import Optional
from pydantic import BaseModel


class AssignVendorRequest(BaseModel):
    vendor_id: str
    vendor_type: Optional[str] = None
