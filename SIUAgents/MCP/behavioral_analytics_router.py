"""
behavioral_analytics_router.py
────────────────────────────────
Tool / Endpoint map:
  get_siu_activity_log   GET  /api/behavioral_analytics/log/{siu_case_id}
  analyze_behavior       POST /api/behavioral_analytics/analyze/{siu_case_id}
"""

import logging
from fastapi import APIRouter

from behavioral_analytics_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/behavioral_analytics/log/{siu_case_id}",
    operation_id="get_siu_activity_log",
    summary="Read siu_activity_log for an SIU case",
    tags=["BehavioralAnalytics"],
)
def get_siu_activity_log(siu_case_id: str):
    """Return all activity log records for a given SIU case."""
    records = handler.get_siu_activity_log(siu_case_id)
    return {"siu_case_id": siu_case_id, "activity_log": records}


@router.post(
    "/api/behavioral_analytics/analyze/{siu_case_id}",
    operation_id="analyze_behavior",
    summary="Analyze behavioral patterns for frequency, timing, and tone anomalies",
    tags=["BehavioralAnalytics"],
)
def analyze_behavior(siu_case_id: str):
    """
    Aggregate activity log and communication history, apply LLM behavioral
    analysis, and persist results to siu_behavioral_analysis.
    """
    return handler.analyze_behavior(siu_case_id)
