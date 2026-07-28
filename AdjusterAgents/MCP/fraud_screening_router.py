"""
fraud_screening_router.py
────────────────────────────
FastAPI routes for the Fraud Screening MCP.

Tool / Endpoint map:
  get_fraud_flags             GET  /api/fraud_screening/flags/{claim_id}
  write_fraud_flag            POST /api/fraud_screening/flags/{claim_id}
  get_ai_fraud_signals        GET  /api/fraud_screening/signals/{claim_id}
  write_ai_fraud_signal       POST /api/fraud_screening/signals/{claim_id}
  get_fraud_risk_snapshot     GET  /api/fraud_screening/snapshot/{claim_id}
  write_fraud_risk_snapshot   POST /api/fraud_screening/snapshot/{claim_id}
  run_fraud_screening         POST /api/fraud_screening/run/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from fraud_screening_mcp import handler
from fraud_screening_mcp.models import AiFraudSignalRequest, FraudFlagRequest, FraudRiskSnapshotRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/fraud_screening/flags/{claim_id}",
    operation_id="get_fraud_flags",
    summary="Get fraud flags for a claim",
    tags=["FraudScreening"],
)
def get_fraud_flags(claim_id: str):
    """Returns all fraud_flags rows for the given claim_id."""
    return handler.get_fraud_flags(claim_id)


@router.post(
    "/api/fraud_screening/flags/{claim_id}",
    operation_id="write_fraud_flag",
    summary="Write a fraud flag for a claim",
    tags=["FraudScreening"],
)
def write_fraud_flag(claim_id: str, body: FraudFlagRequest):
    """Inserts a new fraud_flags row for the given claim_id."""
    try:
        return handler.write_fraud_flag(claim_id, body.flag_type, body.flag_description, body.risk_score, body.detected_by)
    except Exception as e:
        log.exception("write_fraud_flag error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/fraud_screening/signals/{claim_id}",
    operation_id="get_ai_fraud_signals",
    summary="Get AI fraud signals for a claim",
    tags=["FraudScreening"],
)
def get_ai_fraud_signals(claim_id: str):
    """Returns all ai_fraud_signals rows for the given claim_id."""
    return handler.get_ai_fraud_signals(claim_id)


@router.post(
    "/api/fraud_screening/signals/{claim_id}",
    operation_id="write_ai_fraud_signal",
    summary="Write an AI fraud signal for a claim",
    tags=["FraudScreening"],
)
def write_ai_fraud_signal(claim_id: str, body: AiFraudSignalRequest):
    """Inserts a new ai_fraud_signals row for the given claim_id."""
    try:
        return handler.write_ai_fraud_signal(claim_id, body.fraud_score, body.indicator, body.value)
    except Exception as e:
        log.exception("write_ai_fraud_signal error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/fraud_screening/snapshot/{claim_id}",
    operation_id="get_fraud_risk_snapshot",
    summary="Get the latest fraud risk snapshot for a claim",
    tags=["FraudScreening"],
)
def get_fraud_risk_snapshot(claim_id: str):
    """Returns the most recent fraud_risk_snapshots row for the given claim_id, or null."""
    return handler.get_fraud_risk_snapshot(claim_id)


@router.post(
    "/api/fraud_screening/snapshot/{claim_id}",
    operation_id="write_fraud_risk_snapshot",
    summary="Write a fraud risk snapshot for a claim",
    tags=["FraudScreening"],
)
def write_fraud_risk_snapshot(claim_id: str, body: FraudRiskSnapshotRequest):
    """Inserts a new fraud_risk_snapshots row for the given claim_id."""
    try:
        return handler.write_fraud_risk_snapshot(claim_id, body.fraud_score, body.red_flag_count, body.prior_claims, body.vendor_risk)
    except Exception as e:
        log.exception("write_fraud_risk_snapshot error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/fraud_screening/run/{claim_id}",
    operation_id="run_fraud_screening",
    summary="Run AI-assisted fraud screening for a claim",
    tags=["FraudScreening"],
)
def run_fraud_screening(claim_id: str):
    """
    Fetches the claim, uses an LLM to identify 0-3 potential fraud
    indicators, writes ai_fraud_signals (and fraud_flags for indicators with
    risk_score >= 50), computes an aggregate fraud_score, writes a
    fraud_risk_snapshots row, and returns the full screening result.
    """
    try:
        return handler.run_fraud_screening(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("run_fraud_screening error")
        raise HTTPException(status_code=500, detail=str(e))
