"""
fraud_risk_scoring_router.py
─────────────────────────────
FastAPI routes for the Fraud Risk Scoring MCP.

Tool / Endpoint map:
  get_fraud_risk_snapshot     GET  /api/fraud_risk_scoring/snapshot/{claim_id}
  get_ai_fraud_signals        GET  /api/fraud_risk_scoring/signals/{claim_id}
  get_fraud_flags             GET  /api/fraud_risk_scoring/flags/{claim_id}
  recompute_fraud_risk_score  POST /api/fraud_risk_scoring/recompute/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from fraud_risk_scoring_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/fraud_risk_scoring/snapshot/{claim_id}",
    operation_id="get_fraud_risk_snapshot",
    summary="Get the latest fraud risk snapshot for a claim",
    tags=["FraudRiskScoring"],
)
def get_fraud_risk_snapshot(claim_id: str):
    """Returns the most recent fraud_risk_snapshots row for the given claim_id, or null."""
    return handler.get_fraud_risk_snapshot(claim_id)


@router.get(
    "/api/fraud_risk_scoring/signals/{claim_id}",
    operation_id="get_ai_fraud_signals",
    summary="Get AI fraud signals for a claim",
    tags=["FraudRiskScoring"],
)
def get_ai_fraud_signals(claim_id: str):
    """Returns all ai_fraud_signals rows for the given claim_id."""
    return handler.get_ai_fraud_signals(claim_id)


@router.get(
    "/api/fraud_risk_scoring/flags/{claim_id}",
    operation_id="get_fraud_flags",
    summary="Get fraud flags for a claim",
    tags=["FraudRiskScoring"],
)
def get_fraud_flags(claim_id: str):
    """Returns all fraud_flags rows for the given claim_id."""
    return handler.get_fraud_flags(claim_id)


@router.post(
    "/api/fraud_risk_scoring/recompute/{claim_id}",
    operation_id="recompute_fraud_risk_score",
    summary="Recompute the aggregate fraud risk score for a claim",
    tags=["FraudRiskScoring"],
)
def recompute_fraud_risk_score(claim_id: str):
    """
    Reads all ai_fraud_signals and fraud_flags for the claim, computes an
    aggregate fraud_score, red_flag_count, prior_claims, and vendor_risk,
    writes a new fraud_risk_snapshots row, and returns it.
    """
    try:
        return handler.recompute_fraud_risk_score(claim_id)
    except Exception as e:
        log.exception("recompute_fraud_risk_score error")
        raise HTTPException(status_code=500, detail=str(e))
