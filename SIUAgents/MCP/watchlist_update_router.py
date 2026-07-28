"""
watchlist_update_router.py
─────────────────────────────
FastAPI routes for the Watchlist Update MCP.

Tool / Endpoint map:
  add_to_watchlist          POST /api/watchlist_update/watchlist
  get_watchlist              GET  /api/watchlist_update/watchlist
  check_watchlist             GET  /api/watchlist_update/watchlist/check/{entity_id}
  remove_from_watchlist        POST /api/watchlist_update/watchlist/{watchlist_id}/remove
  update_watchlist_from_case    POST /api/watchlist_update/update_from_case/{claim_id}
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException

from watchlist_update_mcp import handler
from watchlist_update_mcp.models import AddToWatchlistRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/watchlist_update/watchlist",
    operation_id="add_to_watchlist",
    summary="Add an entity to the fraud watchlist",
    tags=["WatchlistUpdate"],
)
def add_to_watchlist(body: AddToWatchlistRequest):
    """Inserts a new fraud_watchlist row with status 'Active'."""
    try:
        return handler.add_to_watchlist(
            body.entity_type, body.entity_id, body.entity_name, body.reason, body.severity, body.added_by,
        )
    except Exception as e:
        log.exception("add_to_watchlist error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/watchlist_update/watchlist",
    operation_id="get_watchlist",
    summary="List the fraud watchlist",
    tags=["WatchlistUpdate"],
)
def get_watchlist(entity_type: Optional[str] = None):
    """Returns all fraud_watchlist rows, optionally filtered by entity_type."""
    return handler.get_watchlist(entity_type)


@router.get(
    "/api/watchlist_update/watchlist/check/{entity_id}",
    operation_id="check_watchlist",
    summary="Check if an entity is on the active fraud watchlist",
    tags=["WatchlistUpdate"],
)
def check_watchlist(entity_id: str):
    """Returns matching active fraud_watchlist rows for the given entity_id."""
    return handler.check_watchlist(entity_id)


@router.post(
    "/api/watchlist_update/watchlist/{watchlist_id}/remove",
    operation_id="remove_from_watchlist",
    summary="Remove an entity from the fraud watchlist",
    tags=["WatchlistUpdate"],
)
def remove_from_watchlist(watchlist_id: str):
    """Sets status = 'Removed' on the fraud_watchlist row matching watchlist_id."""
    try:
        return handler.remove_from_watchlist(watchlist_id)
    except Exception as e:
        log.exception("remove_from_watchlist error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/watchlist_update/update_from_case/{claim_id}",
    operation_id="update_watchlist_from_case",
    summary="Update the fraud watchlist based on an SIU case resolution",
    tags=["WatchlistUpdate"],
)
def update_watchlist_from_case(claim_id: str):
    """
    Reads the most recent siu_decision for the claim (via siu_case_master).
    If decision == "Fraud Confirmed", adds the policyholder to the fraud
    watchlist. Otherwise explains no action was taken.
    """
    try:
        return handler.update_watchlist_from_case(claim_id)
    except Exception as e:
        log.exception("update_watchlist_from_case error")
        raise HTTPException(status_code=500, detail=str(e))
