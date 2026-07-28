from pydantic import BaseModel


class ClaimNumberRequest(BaseModel):
    claim_number: str
