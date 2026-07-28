"""
eta_prediction_router.py
─────────────────────────────
FastAPI routes for the ETA Prediction MCP.

Tool / Endpoint map:
  get_eta_prediction  GET  /api/eta_prediction/predictions/{claim_id}
  predict_eta          POST /api/eta_prediction/predict/{claim_id}
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from eta_prediction_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/eta_prediction/predictions/{claim_id}",
    operation_id="get_eta_prediction",
    summary="Get stored ETA predictions for a claim",
    tags=["ETAPrediction"],
)
def get_eta_prediction(claim_id: str, vendor_id: Optional[str] = None):
    """Returns eta_predictions rows for the given claim_id, optionally filtered by vendor_id."""
    return handler.get_eta_prediction(claim_id, vendor_id)


@router.post(
    "/api/eta_prediction/predict/{claim_id}",
    operation_id="predict_eta",
    summary="Predict the ETA for vendor work on a claim",
    tags=["ETAPrediction"],
)
def predict_eta(claim_id: str, vendor_id: str):
    """
    Reads the vendor's benchmark/average eta_days as a baseline and the
    claim's loss_type/complexity, uses an LLM (JSON response) to adjust the
    baseline, falling back to a heuristic if the LLM call fails, and inserts
    a new eta_predictions row.
    """
    try:
        return handler.predict_eta(claim_id, vendor_id)
    except Exception as e:
        log.exception("predict_eta error")
        raise HTTPException(status_code=500, detail=str(e))
