"""
communication_router.py
────────────────────────
Tool / Endpoint map:
  get_communication_history    GET  /api/communication/history/{claim_number}
  draft_status_notification    POST /api/communication/draft/{claim_number}
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from communication_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


class LogInboundRequest(BaseModel):
    message_text: str
    sentiment: Optional[str] = "Neutral"


@router.post(
    "/api/communication/log_inbound/{claim_number}",
    operation_id="log_inbound_communication",
    summary="Log the policyholder's inbound message to communication_history",
    tags=["Communication"],
)
def log_inbound_communication(claim_number: str, req: LogInboundRequest):
    """
    Records the policyholder's inbound message as a new row in
    communication_history with direction='Inbound'. Call this BEFORE
    drafting the notification so the inbound message is persisted.
    """
    try:
        return handler.log_inbound_communication(claim_number, req.message_text, req.sentiment)
    except Exception as e:
        log.exception("log_inbound_communication error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/communication/history/{claim_number}",
    operation_id="get_communication_history",
    summary="Read communication_history for a claim",
    tags=["Communication"],
)
def get_communication_history(claim_number: str):
    """Return all communication history records for a given claim number."""
    records = handler.get_communication_history(claim_number)
    return {"claim_number": claim_number, "communication_history": records}


@router.post(
    "/api/communication/draft/{claim_number}",
    operation_id="draft_status_notification",
    summary="Auto-draft a status-change notification for the policyholder",
    tags=["Communication"],
)
def draft_status_notification(claim_number: str):
    """
    Uses the claim's current status, journey stage, sentiment, and recent
    communication history to generate an empathetic, channel-appropriate
    notification draft, saved to communication_history with status='Draft'.
    """
    result = handler.draft_status_notification(claim_number)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result
