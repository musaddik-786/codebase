"""
evidence_correlation_router.py
────────────────────────────────
Tool / Endpoint map:
  get_investigation_notes   GET  /api/evidence_correlation/notes/{claim_id}
  correlate_evidence        POST /api/evidence_correlation/correlate/{claim_id}
"""

import logging
from fastapi import APIRouter

from evidence_correlation_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/evidence_correlation/notes/{claim_id}",
    operation_id="get_investigation_notes",
    summary="Read investigation_notes for a claim",
    tags=["EvidenceCorrelation"],
)
def get_investigation_notes(claim_id: str):
    """Return all investigation notes for a given claim."""
    records = handler.get_investigation_notes(claim_id)
    return {"claim_id": claim_id, "investigation_notes": records}


@router.post(
    "/api/evidence_correlation/correlate/{claim_id}",
    operation_id="correlate_evidence",
    summary="Cross-reference investigation notes, timeline events, and evidence items for inconsistencies",
    tags=["EvidenceCorrelation"],
)
def correlate_evidence(claim_id: str):
    """
    Aggregate investigation notes, siu_timeline_events, and evidence_items,
    then use LLM analysis to surface inconsistencies and produce a
    corroboration score. Persist to siu_evidence_correlation_results.
    """
    return handler.correlate_evidence(claim_id)
