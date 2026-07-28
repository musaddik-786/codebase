"""
payment_trigger_router.py
───────────────────────────────
FastAPI routes for the Payment Trigger MCP.

Tool / Endpoint map:
  check_claim_approved          GET  /api/payment_trigger/approved/{claim_number}
  create_payment_disbursement   POST /api/payment_trigger/disburse/{claim_number}
  update_payment_status         POST /api/payment_trigger/status/{payment_id}
  get_payment_disbursements      GET  /api/payment_trigger/disbursements/{claim_number}
"""

import logging
from fastapi import APIRouter, HTTPException

from payment_trigger_mcp import handler
from payment_trigger_mcp.models import CreatePaymentRequest, UpdatePaymentStatusRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/payment_trigger/eligibility/{claim_number}",
    operation_id="get_payment_eligibility",
    summary="Get the payment eligibility result from PaymentEligibilityAgent for a claim",
    tags=["PaymentTrigger"],
)
def get_payment_eligibility(claim_number: str):
    """
    Reads the latest auto_adjudication_records row for the claim.
    Returns eligible_for_auto_adjudication, decision, stp_category, and failed gates.
    Returns eligibility_checked=False if PaymentEligibilityAgent has not run yet.
    """
    return handler.get_payment_eligibility(claim_number)


@router.get(
    "/api/payment_trigger/approved/{claim_number}",
    operation_id="check_claim_approved",
    summary="Check whether a claim is approved for payment",
    tags=["PaymentTrigger"],
)
def check_claim_approved(claim_number: str):
    """
    Reads the most recent adjuster_findings row for the claim and returns
    whether coverage_confirmed indicates approval ('Yes'/'Confirmed'), plus
    the available settlement/reserve amount.
    """
    return handler.check_claim_approved(claim_number)


@router.post(
    "/api/payment_trigger/disburse/{claim_number}",
    operation_id="create_payment_disbursement",
    summary="Create a payment disbursement for an approved claim",
    tags=["PaymentTrigger"],
)
def create_payment_disbursement(claim_number: str, body: CreatePaymentRequest):
    """
    Verifies the claim is approved via check_claim_approved; if not approved,
    returns an error result without inserting. Else inserts a new
    payment_disbursements row (payment_id auto-generated, status='Initiated').
    """
    try:
        return handler.create_payment_disbursement(claim_number, body.amount, body.payment_method, body.approved_by)
    except Exception as e:
        log.exception("create_payment_disbursement error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/payment_trigger/status/{payment_id}",
    operation_id="update_payment_status",
    summary="Update the status of a payment disbursement",
    tags=["PaymentTrigger"],
)
def update_payment_status(payment_id: str, body: UpdatePaymentStatusRequest):
    """Updates payment_disbursements.status; sets completed_at if status == 'Completed'."""
    try:
        result = handler.update_payment_status(payment_id, body.status)
        if not result:
            raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.exception("update_payment_status error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/payment_trigger/disbursements/{claim_number}",
    operation_id="get_payment_disbursements",
    summary="Get all payment disbursements for a claim",
    tags=["PaymentTrigger"],
)
def get_payment_disbursements(claim_number: str):
    """Returns all payment_disbursements rows for the given claim_number."""
    return handler.get_payment_disbursements(claim_number)
