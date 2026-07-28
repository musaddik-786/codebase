from typing import Optional
from pydantic import BaseModel


class CreateWorkOrderRequest(BaseModel):
    claim_id: str
    claim_number: str
    expert_id: str
    expert_name: str
    expert_type: str
    scheduled_date: str
    scheduled_time: str
    customer_address: str
    assigned_by: str
    estimated_arrival: Optional[str] = None
    estimated_cost: Optional[float] = None
    priority: str = "Normal"
    notes_to_expert: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None


class UpdateWorkOrderStatusRequest(BaseModel):
    status: str
    action_by: str
    details: Optional[str] = None
