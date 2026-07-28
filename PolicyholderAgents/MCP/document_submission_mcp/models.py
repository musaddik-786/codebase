from pydantic import BaseModel
from typing import Optional


class UploadDocumentRequest(BaseModel):
    claim_number: str
    file_name: str
    uploaded_by: Optional[str] = None
    uploaded_by_role: Optional[str] = "Policyholder"
