"""
payment_eligibility_router.py
───────────────────────────────
Tool / Endpoint map:
  get_auto_adjudication_thresholds  GET  /api/payment_eligibility/thresholds
  check_eligibility                 POST /api/payment_eligibility/check/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from payment_eligibility_mcp import handler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/payment_eligibility/thresholds",
    operation_id="get_auto_adjudication_thresholds",
    summary="Read all auto_adjudication_threshold_configs",
    tags=["PaymentEligibility"],
)
def get_auto_adjudication_thresholds():
    records = handler.get_auto_adjudication_thresholds()
    return {"auto_adjudication_threshold_configs": records}


@router.post(
    "/api/payment_eligibility/check/{claim_id}",
    operation_id="check_eligibility",
    summary="Determine if a claim is eligible for automated payment processing",
    tags=["PaymentEligibility"],
)
def check_eligibility(claim_id: str):
    try:
        return handler.check_eligibility(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("check_eligibility error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/payment_eligibility/adjudication/{claim_id}",
    operation_id="get_auto_adjudication_record",
    summary="Get the latest auto adjudication record for a claim",
    tags=["PaymentEligibility"],
)
def get_auto_adjudication_record(claim_id: str):
    record = handler.get_auto_adjudication_record(claim_id)
    return {"auto_adjudication_record": record}


@router.post(
    "/api/payment_eligibility/confirm/{claim_id}",
    operation_id="confirm_payment_approval",
    summary="Explicitly commit claims.status = Approved — only called after a human adjuster's final payment decision, never by check_eligibility itself",
    tags=["PaymentEligibility"],
)
def confirm_payment_approval(claim_id: str):
    try:
        return handler.confirm_payment_approval(claim_id)
    except Exception as e:
        log.exception("confirm_payment_approval error")
        raise HTTPException(status_code=500, detail=str(e))
