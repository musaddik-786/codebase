# """
# settlement_recommendation_router.py
# ──────────────────────────────────────
# Tool / Endpoint map:
#   get_ai_decision_recommendation  GET  /api/settlement_recommendation/recommendation/{claim_id}
#   recommend_settlement            POST /api/settlement_recommendation/calculate/{claim_id}
# """

# import logging
# from fastapi import APIRouter, HTTPException

# from settlement_recommendation_mcp import handler

# log = logging.getLogger(__name__)

# router = APIRouter()


# @router.get(
#     "/api/settlement_recommendation/recommendation/{claim_id}",
#     operation_id="get_ai_decision_recommendation",
#     summary="Read the latest AI settlement recommendation for a claim",
#     tags=["SettlementRecommendation"],
# )
# def get_ai_decision_recommendation(claim_id: str):
#     record = handler.get_ai_decision_recommendation(claim_id)
#     return {"claim_id": claim_id, "ai_decision_recommendation": record}


# @router.post(
#     "/api/settlement_recommendation/calculate/{claim_id}",
#     operation_id="recommend_settlement",
#     summary="Calculate and store a recommended settlement amount for a claim",
#     tags=["SettlementRecommendation"],
# )
# def recommend_settlement(claim_id: str):
#     try:
#         return handler.recommend_settlement(claim_id)
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         log.exception("recommend_settlement error")
#         raise HTTPException(status_code=500, detail=str(e))







# """
# settlement_recommendation_router.py
# ──────────────────────────────────────
# Tool / Endpoint map:
#   get_ai_decision_recommendation  GET  /api/settlement_recommendation/recommendation/{claim_id}
#   recommend_settlement            POST /api/settlement_recommendation/calculate/{claim_id}
# """

# import logging
# from fastapi import APIRouter, HTTPException

# from settlement_recommendation_mcp import handler

# log = logging.getLogger(__name__)

# router = APIRouter()


# @router.get(
#     "/api/settlement_recommendation/recommendation/{claim_id}",
#     operation_id="get_ai_decision_recommendation",
#     summary="Read the latest AI settlement recommendation for a claim",
#     tags=["SettlementRecommendation"],
# )
# def get_ai_decision_recommendation(claim_id: str):
#     record = handler.get_ai_decision_recommendation(claim_id)
#     return {"claim_id": claim_id, "ai_decision_recommendation": record}


# @router.post(
#     "/api/settlement_recommendation/calculate/{claim_id}",
#     operation_id="recommend_settlement",
#     summary="Calculate and store a recommended settlement amount for a claim",
#     tags=["SettlementRecommendation"],
# )
# def recommend_settlement(claim_id: str):
#     try:
#         return handler.recommend_settlement(claim_id)
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         log.exception("recommend_settlement error")
#         raise HTTPException(status_code=500, detail=str(e))




"""
settlement_recommendation_router.py
──────────────────────────────────────
Tool / Endpoint map:
  get_ai_decision_recommendation  GET  /api/settlement_recommendation/recommendation/{claim_id}
  recommend_settlement            POST /api/settlement_recommendation/calculate/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from settlement_recommendation_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/settlement_recommendation/recommendation/{claim_id}",
    operation_id="get_ai_decision_recommendation",
    summary="Read the latest AI settlement recommendation for a claim",
    tags=["SettlementRecommendation"],
)
def get_ai_decision_recommendation(claim_id: str):
    record = handler.get_ai_decision_recommendation(claim_id)
    return {"claim_id": claim_id, "ai_decision_recommendation": record}


@router.post(
    "/api/settlement_recommendation/calculate/{claim_id}",
    operation_id="recommend_settlement",
    summary="Calculate and store a recommended settlement amount for a claim",
    tags=["SettlementRecommendation"],
)
def recommend_settlement(claim_id: str):
    try:
        return handler.recommend_settlement(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("recommend_settlement error")
        raise HTTPException(status_code=500, detail=str(e))
