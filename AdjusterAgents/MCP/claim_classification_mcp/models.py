from pydantic import BaseModel


class ClaimNumberRequest(BaseModel):
    claim_number: str


class SaveClassificationRequest(BaseModel):
    complexity: str
    routing: str
