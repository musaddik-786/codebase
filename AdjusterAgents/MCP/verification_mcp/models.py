from typing import Optional
from pydantic import BaseModel


class CreateVerificationRequest(BaseModel):
    type: str
    status: str = "Pending"
    result: Optional[str] = None


class VerificationDetailRequest(BaseModel):
    field: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    flag: str
    severity: str = "Advisory"
