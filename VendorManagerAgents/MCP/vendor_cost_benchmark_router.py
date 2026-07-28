"""
vendor_cost_benchmark_router.py
──────────────────────────────────
FastAPI routes for the Vendor Cost Benchmark MCP.

Tool / Endpoint map:
  get_vendor_benchmark     GET  /api/vendor_cost_benchmark/benchmark/{vendor_id}
  get_vendor_cost_inputs   GET  /api/vendor_cost_benchmark/cost_inputs/{vendor_id}
  record_vendor_cost       POST /api/vendor_cost_benchmark/cost_inputs/{vendor_id}
  compute_cost_variance     POST /api/vendor_cost_benchmark/variance/{vendor_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from vendor_cost_benchmark_mcp import handler
from vendor_cost_benchmark_mcp.models import RecordVendorCostRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/vendor_cost_benchmark/benchmark/{vendor_id}",
    operation_id="get_vendor_benchmark",
    summary="Get the vendor_benchmarks record for a vendor",
    tags=["VendorCostBenchmark"],
)
def get_vendor_benchmark(vendor_id: str):
    """Returns the vendor_benchmarks row for the given vendor_id, or null."""
    return handler.get_vendor_benchmark(vendor_id)


@router.get(
    "/api/vendor_cost_benchmark/cost_inputs/{vendor_id}",
    operation_id="get_vendor_cost_inputs",
    summary="List recorded cost inputs for a vendor",
    tags=["VendorCostBenchmark"],
)
def get_vendor_cost_inputs(vendor_id: str):
    """Returns vendor_cost_input rows for the given vendor_id."""
    return handler.get_vendor_cost_inputs(vendor_id)


@router.post(
    "/api/vendor_cost_benchmark/cost_inputs/{vendor_id}",
    operation_id="record_vendor_cost",
    summary="Record an estimated/actual cost for a vendor on a claim",
    tags=["VendorCostBenchmark"],
)
def record_vendor_cost(vendor_id: str, body: RecordVendorCostRequest):
    """Inserts a new vendor_cost_input row."""
    try:
        return handler.record_vendor_cost(vendor_id, body.claim_id, body.estimated_cost, body.actual_cost)
    except Exception as e:
        log.exception("record_vendor_cost error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/vendor_cost_benchmark/variance/{vendor_id}",
    operation_id="compute_cost_variance",
    summary="Compute cost variance for a vendor against its benchmark",
    tags=["VendorCostBenchmark"],
)
def compute_cost_variance(vendor_id: str):
    """
    Aggregates vendor_cost_input rows with actual_cost, computes
    avg_estimate/avg_actual/variance, upserts cost_variance_output, and
    compares against vendor_benchmarks.avg_repair_cost.
    """
    try:
        return handler.compute_cost_variance(vendor_id)
    except Exception as e:
        log.exception("compute_cost_variance error")
        raise HTTPException(status_code=500, detail=str(e))
