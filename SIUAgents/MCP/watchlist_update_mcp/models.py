from typing import Optional
from pydantic import BaseModel


class AddToWatchlistRequest(BaseModel):
    entity_type: str
    entity_id: str
    entity_name: str
    reason: str
    severity: str = "Medium"
    added_by: str = "SIU Investigator"
