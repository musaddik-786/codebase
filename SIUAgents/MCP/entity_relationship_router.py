"""
entity_relationship_router.py
───────────────────────────────
Tool / Endpoint map:
  get_fraud_network_graph   GET  /api/entity_relationship/graph/{entity_id}
  build_entity_graph        POST /api/entity_relationship/build/{claim_id}
"""

import logging
from fastapi import APIRouter

from entity_relationship_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/entity_relationship/graph/{entity_id}",
    operation_id="get_fraud_network_graph",
    summary="Read fraud_network_graph edges for an entity",
    tags=["EntityRelationship"],
)
def get_fraud_network_graph(entity_id: str):
    """Return all fraud network graph edges connected to an entity."""
    records = handler.get_fraud_network_graph(entity_id)
    return {"entity_id": entity_id, "graph_edges": records}


@router.post(
    "/api/entity_relationship/build/{claim_id}",
    operation_id="build_entity_graph",
    summary="Build the entity relationship graph for a claim and detect suspicious connections",
    tags=["EntityRelationship"],
)
def build_entity_graph(claim_id: str):
    """
    Link claimants, vendors, adjusters, and addresses across claims into a
    graph. Use LLM to score suspicious connection patterns and persist edges
    to fraud_network_graph.
    """
    return handler.build_entity_graph(claim_id)
