from typing import Optional
from pydantic import BaseModel


class RecordVendorRatingRequest(BaseModel):
    rating: float
    feedback: Optional[str] = None
