# from pydantic import BaseModel, Field
# from typing import Optional


# class GwSearchPolicyRequest(BaseModel):
#     policy_number: str = Field(..., description="Policy number to look up in Guidewire, e.g. '9802322834'")


# class GwReportLossRequest(BaseModel):
#     policy_number: str = Field(..., description="Policy number the loss is reported against")
#     claim_number: str = Field(..., description="Local claim number, e.g. CLM-2026-1234")
#     loss_type: str = Field(..., description="Type of loss, e.g. 'Water Damage', 'Fire'")
#     loss_date: str = Field(..., description="Date of loss in YYYY-MM-DD format")
#     loss_description: str = Field(..., description="Free-text description of what happened")
#     loss_location: Optional[str] = Field(None, description="Address or area where loss occurred")
#     insured_name: str = Field(..., description="Name of the insured policyholder")
#     estimated_amount: Optional[float] = Field(None, description="Policyholder's estimated loss amount")


# class SavePolicyDetailsRequest(BaseModel):
#     policy_number: str = Field(..., description="Policy number to fetch from Guidewire and save locally")


# class RecordClaimPaymentRequest(BaseModel):
#     claim_id: str = Field(..., description="Claim number (e.g. CLM-2026-1001) for which payment is released")
#     amount_paid: float = Field(..., description="Amount paid out for this claim")
#     approved_by: Optional[str] = Field(None, description="Name or ID of the adjuster who approved the payment")
#     notes: Optional[str] = Field(None, description="Optional notes about the payment")






from pydantic import BaseModel, Field
from typing import Optional


class GetClaimDetailsRequest(BaseModel):
   claim_number: str = Field(
       ...,
       description="Claim number, e.g. CLM-2024-1003"
   )
   
class GwSearchPolicyRequest(BaseModel):
    policy_number: str = Field(..., description="Policy number to look up in Guidewire, e.g. '9802322834'")


class GwReportLossRequest(BaseModel):
    policy_number: str = Field(..., description="Policy number the loss is reported against")
    claim_number: str = Field(..., description="Local claim number, e.g. CLM-2026-1234")
    loss_type: str = Field(..., description="Type of loss, e.g. 'Water Damage', 'Fire'")
    loss_date: str = Field(..., description="Date of loss in YYYY-MM-DD format")
    loss_description: str = Field(..., description="Free-text description of what happened")
    loss_location: Optional[str] = Field(None, description="Address or area where loss occurred")
    policyholder_name: str = Field(..., description="Name of the insured policyholder")
    estimated_amount: Optional[float] = Field(None, description="Policyholder's estimated loss amount")


class SavePolicyDetailsRequest(BaseModel):
    policy_number: str = Field(..., description="Policy number to fetch from Guidewire and save locally")


class RecordClaimPaymentRequest(BaseModel):
    claim_number: str = Field(..., description="Claim number (e.g. CLM-2026-1001) for which payment is released")
    amount_paid: float = Field(..., description="Amount paid out for this claim")
    approved_by: Optional[str] = Field(None, description="Name or ID of the adjuster who approved the payment")
    notes: Optional[str] = Field(None, description="Optional notes about the payment")
