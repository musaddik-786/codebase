# """
# reserve_recommendation_router.py
# ──────────────────────────────────
# Tool / Endpoint map:
#   get_adjuster_findings  GET  /api/reserve_recommendation/findings/{claim_id}
#   recommend_reserve      POST /api/reserve_recommendation/recommend/{claim_id}
# """

# import logging
# from fastapi import APIRouter, HTTPException

# from reserve_recommendation_mcp import handler

# log = logging.getLogger(__name__)

# router = APIRouter()


# @router.get(
#     "/api/reserve_recommendation/findings/{claim_id}",
#     operation_id="get_adjuster_findings",
#     summary="Read the latest adjuster_findings record for a claim",
#     tags=["ReserveRecommendation"],
# )
# def get_adjuster_findings(claim_id: str):
#     record = handler.get_adjuster_findings(claim_id)
#     return {"claim_id": claim_id, "adjuster_findings": record}


# @router.post(
#     "/api/reserve_recommendation/recommend/{claim_id}",
#     operation_id="recommend_reserve",
#     summary="Compute and store a recommended financial reserve for a claim",
#     tags=["ReserveRecommendation"],
# )
# def recommend_reserve(claim_id: str):
#     try:
#         return handler.recommend_reserve(claim_id)
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         log.exception("recommend_reserve error")
#         raise HTTPException(status_code=500, detail=str(e))




"""
reserve_recommendation_router.py
──────────────────────────────────
Tool / Endpoint map:
  get_adjuster_findings  GET  /api/reserve_recommendation/findings/{claim_id}
  recommend_reserve      POST /api/reserve_recommendation/recommend/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from reserve_recommendation_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/reserve_recommendation/findings/{claim_id}",
    operation_id="get_adjuster_findings",
    summary="Read the latest adjuster_findings record for a claim",
    tags=["ReserveRecommendation"],
)
def get_adjuster_findings(claim_id: str):
    record = handler.get_adjuster_findings(claim_id)
    return {"claim_id": claim_id, "adjuster_findings": record}


@router.post(
    "/api/reserve_recommendation/recommend/{claim_id}",
    operation_id="recommend_reserve",
    summary="Compute and store a recommended financial reserve for a claim",
    tags=["ReserveRecommendation"],
)
def recommend_reserve(claim_id: str):
    try:
        return handler.recommend_reserve(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("recommend_reserve error")
        raise HTTPException(status_code=500, detail=str(e))
