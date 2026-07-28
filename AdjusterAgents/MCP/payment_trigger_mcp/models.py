from pydantic import BaseModel


class CreatePaymentRequest(BaseModel):
    amount: float
    payment_method: str
    approved_by: str


class UpdatePaymentStatusRequest(BaseModel):
    status: str
