from pydantic import BaseModel


class RecomputeFraudRiskRequest(BaseModel):
    claim_id: str
