"""
network_analysis_router.py
───────────────────────────
Tool / Endpoint map:
  get_vendor_network_signals   GET  /api/network_analysis/signals/{vendor_id}
  detect_fraud_rings           POST /api/network_analysis/detect/{claim_id}
"""

import logging
from fastapi import APIRouter

from network_analysis_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/network_analysis/signals/{vendor_id}",
    operation_id="get_vendor_network_signals",
    summary="Read vendor_network_signals for a vendor",
    tags=["NetworkAnalysis"],
)
def get_vendor_network_signals(vendor_id: str):
    """Return all network signal records for a given vendor."""
    records = handler.get_vendor_network_signals(vendor_id)
    return {"vendor_id": vendor_id, "network_signals": records}


@router.post(
    "/api/network_analysis/detect/{claim_id}",
    operation_id="detect_fraud_rings",
    summary="Detect fraud rings and collusion patterns across network graph and vendor signals",
    tags=["NetworkAnalysis"],
)
def detect_fraud_rings(claim_id: str):
    """
    Cross-reference fraud_network_graph edges with vendor_network_signals to
    identify collusion clusters and fraud rings.  Persist results to
    siu_network_analysis_results.
    """
    return handler.detect_fraud_rings(claim_id)
