from typing import Optional
from pydantic import BaseModel


class FraudFlagRequest(BaseModel):
    flag_type: str
    flag_description: str
    risk_score: int
    detected_by: str


class AiFraudSignalRequest(BaseModel):
    fraud_score: int
    indicator: str
    value: Optional[str] = None


class FraudRiskSnapshotRequest(BaseModel):
    fraud_score: int
    red_flag_count: int = 0
    prior_claims: str = "Low"
    vendor_risk: str = "Low"
