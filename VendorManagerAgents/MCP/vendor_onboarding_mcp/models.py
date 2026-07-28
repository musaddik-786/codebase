from typing import Optional
from pydantic import BaseModel


class SubmitVendorApplicationRequest(BaseModel):
    name: str
    specialty: str
    location: str
    license_number: Optional[str] = None
    license_expiry_date: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    submitted_date: Optional[str] = None


class RejectVendorApplicationRequest(BaseModel):
    reason: str
