from typing import Any, List
from pydantic import BaseModel


class SaveValidationResultRequest(BaseModel):
    overall_status: str
    authenticity_flags: List[Any] = []
