"""
dispatch_router.py
─────────────────────
FastAPI routes for the Dispatch MCP.

Tool / Endpoint map:
  create_work_order         POST /api/dispatch/work_orders
  get_work_order            GET  /api/dispatch/work_orders/{work_order_id}
  list_work_orders          GET  /api/dispatch/work_orders
  update_work_order_status  POST /api/dispatch/work_orders/{work_order_id}/status
  get_dispatch_logs         GET  /api/dispatch/work_orders/{work_order_id}/logs
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from dispatch_mcp import handler
from dispatch_mcp.models import CreateWorkOrderRequest, UpdateWorkOrderStatusRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/dispatch/work_orders",
    operation_id="create_work_order",
    summary="Create a new work order and dispatch log entry",
    tags=["Dispatch"],
)
def create_work_order(body: CreateWorkOrderRequest):
    """Inserts a new work_orders row (status 'Scheduled') and a 'Created' dispatch_logs row."""
    try:
        return handler.create_work_order(
            body.claim_id, body.claim_number, body.expert_id, body.expert_name, body.expert_type,
            body.scheduled_date, body.scheduled_time, body.customer_address, body.assigned_by,
            body.estimated_arrival, body.estimated_cost, body.priority, body.notes_to_expert,
            body.customer_phone, body.customer_email,
        )
    except Exception as e:
        log.exception("create_work_order error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/dispatch/work_orders/{work_order_id}",
    operation_id="get_work_order",
    summary="Get a work order by work_order_id",
    tags=["Dispatch"],
)
def get_work_order(work_order_id: str):
    """Returns the work_orders row for the given work_order_id, or null."""
    return handler.get_work_order(work_order_id)


@router.get(
    "/api/dispatch/work_orders",
    operation_id="list_work_orders",
    summary="List work orders, optionally filtered by claim_id and/or status",
    tags=["Dispatch"],
)
def list_work_orders(claim_id: Optional[str] = None, status: Optional[str] = None):
    """Returns work_orders rows, optionally filtered."""
    return handler.list_work_orders(claim_id, status)


@router.post(
    "/api/dispatch/work_orders/{work_order_id}/status",
    operation_id="update_work_order_status",
    summary="Update a work order's status and log the transition",
    tags=["Dispatch"],
)
def update_work_order_status(work_order_id: str, body: UpdateWorkOrderStatusRequest):
    """
    Updates work_orders.status (setting started_at/completed_at/canceled_at
    as appropriate) and inserts a dispatch_logs row recording the previous
    and new status.
    """
    try:
        return handler.update_work_order_status(work_order_id, body.status, body.action_by, body.details)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("update_work_order_status error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/dispatch/work_orders/{work_order_id}/logs",
    operation_id="get_dispatch_logs",
    summary="Get the dispatch audit trail for a work order",
    tags=["Dispatch"],
)
def get_dispatch_logs(work_order_id: str):
    """Returns dispatch_logs rows for the given work_order_id, ordered chronologically."""
    return handler.get_dispatch_logs(work_order_id)
