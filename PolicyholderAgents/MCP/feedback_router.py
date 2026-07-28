"""
feedback_router.py
─────────────────────
FastAPI routes for the Feedback / Sentiment Tracking MCP.

Tool / Endpoint map:
  write_customer_feedback   POST /api/feedback/write
  get_customer_feedback      GET  /api/feedback/claim/{claim_number}
  update_sentiment_tracker    POST /api/feedback/sentiment/update
  get_sentiment_tracker        GET  /api/feedback/sentiment/{claim_number}
"""

import logging
from fastapi import APIRouter, HTTPException

from feedback_mcp.models import WriteCustomerFeedbackRequest, UpdateSentimentTrackerRequest
from feedback_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/feedback/write",
    operation_id="write_customer_feedback",
    summary="Record policyholder feedback for a claim stage with sentiment analysis",
    tags=["Feedback"],
)
def write_customer_feedback(req: WriteCustomerFeedbackRequest):
    """
    Uses an LLM to classify the sentiment of the comment ("Positive",
    "Neutral", or "Negative") plus a 0-100 sentiment_score, inserts a row
    into customer_feedback_per_stage, then recomputes the aggregate
    claim_sentiment_tracker. Returns {feedback, sentiment_tracker}.
    """
    try:
        return handler.write_customer_feedback(
            claim_number=req.claim_number,
            comment=req.comment,
            claim_id=req.claim_id,
            stage_number=req.stage_number,
            stage_name=req.stage_name,
        )
    except Exception as e:
        log.exception("write_customer_feedback error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/feedback/claim/{claim_number}",
    operation_id="get_customer_feedback",
    summary="Get all stage feedback for a claim",
    tags=["Feedback"],
)
def get_customer_feedback(claim_number: str):
    """
    Returns all customer_feedback_per_stage rows for the given
    claim_number, ordered by submission time.
    """
    return handler.get_customer_feedback(claim_number)


@router.post(
    "/api/feedback/sentiment/update",
    operation_id="update_sentiment_tracker",
    summary="Recompute the aggregate sentiment tracker for a claim",
    tags=["Feedback"],
)
def update_sentiment_tracker(req: UpdateSentimentTrackerRequest):
    """
    Recomputes the average sentiment score, trend (Improving/Declining/
    Stable based on the last two feedback entries), and escalation_risk
    (High if avg<40, Medium if avg<70, else Low) from all
    customer_feedback_per_stage rows for the claim, then upserts the
    claim_sentiment_tracker row.
    """
    try:
        result = handler.update_sentiment_tracker(req.claim_number, req.policyholder_name)
        if result is None:
            raise HTTPException(status_code=404, detail="No feedback found for this claim")
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.exception("update_sentiment_tracker error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/feedback/sentiment/{claim_number}",
    operation_id="get_sentiment_tracker",
    summary="Get the sentiment tracker for a claim",
    tags=["Feedback"],
)
def get_sentiment_tracker(claim_number: str):
    """
    Returns the claim_sentiment_tracker row for the given claim_number,
    including current_sentiment, sentiment_score, sentiment_trend, and
    escalation_risk.
    """
    record = handler.get_sentiment_tracker(claim_number)
    if not record:
        raise HTTPException(status_code=404, detail=f"No sentiment tracker for {claim_number}")
    return record
