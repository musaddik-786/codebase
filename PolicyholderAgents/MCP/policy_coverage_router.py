# """
# policy_coverage_router.py
# ──────────────────────────
# Endpoints / MCP tools:
#   gw_search_policy        POST /gw_search_policy
#   gw_get_policy_coverages POST /gw_get_policy_coverages
#   save_policy_details     POST /save_policy_details
#   get_policy_details      GET  /get_policy_details/{policy_id}
#   verify_coverage         POST /api/policy_coverage/verify/{claim_id}
#   record_claim_payment    POST /api/policy_coverage/payment
# """

# import logging
# from fastapi import APIRouter, HTTPException

# from policy_coverage_mcp import handler
# from policy_coverage_mcp.models import (
#     GwSearchPolicyRequest,
#     SavePolicyDetailsRequest,
#     RecordClaimPaymentRequest,
# )

# log = logging.getLogger(__name__)
# router = APIRouter()


# @router.post(
#     "/gw_search_policy",
#     operation_id="gw_search_policy",
#     summary="Search Guidewire PolicyCenter for a policy by policy number",
# )
# def gw_search_policy(req: GwSearchPolicyRequest):
#     """
#     Look up a policy in Guidewire PolicyCenter using the policy number.
#     Returns found=True with policy details, or found=False with an error message.
#     """
#     return handler.gw_search_policy(req.policy_number)


# @router.post(
#     "/gw_get_policy_coverages",
#     operation_id="gw_get_policy_coverages",
#     summary="Fetch full policy coverage details from Guidewire",
# )
# def gw_get_policy_coverages(req: GwSearchPolicyRequest):
#     """
#     Fetches the detailed policy record from Guidewire PolicyCenter including
#     all lines of business, coverage clauses, deductibles, and limits.
#     """
#     return handler.gw_get_policy_coverages(req.policy_number)


# @router.post(
#     "/save_policy_details",
#     operation_id="save_policy_details",
#     summary="Fetch policy from Guidewire and persist to local database",
# )
# def save_policy_details(req: SavePolicyDetailsRequest):
#     """
#     Calls Guidewire (search + coverage detail), extracts deductible, coverage limit,
#     exclusions, and all policy metadata, then saves/updates the local policy_details table.
#     Sets remaining_coverage_limit = coverage_limit on first save (preserved on updates).
#     """
#     try:
#         return handler.save_policy_details(req.policy_number)
#     except Exception as e:
#         log.exception("save_policy_details error")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get(
#     "/get_policy_details/{policy_id}",
#     operation_id="get_policy_details",
#     summary="Read policy details from the local database",
# )
# def get_policy_details(policy_id: str):
#     """Returns the full policy_details record for the given policy_id."""
#     record = handler.get_policy_details(policy_id)
#     if not record:
#         return {"status": "not_found", "policy_id": policy_id}
#     return record


# @router.get(
#     "/api/policy_coverage/result/{claim_id}",
#     operation_id="get_coverage_verification_result",
#     summary="Read an existing coverage verification result for a claim",
# )
# def get_coverage_verification_result(claim_id: str):
#     """
#     Returns the most recent coverage verification result from the local DB
#     without re-running the LLM. Returns found=False if none exists yet.
#     """
#     return handler.get_coverage_verification_result(claim_id)


# @router.post(
#     "/api/policy_coverage/verify/{claim_id}",
#     operation_id="verify_coverage",
#     summary="Verify whether a claim's loss is covered by the linked policy",
# )
# def verify_coverage(claim_id: str):
#     """
#     Looks up the claim and its linked policy from the local DB, uses the LLM to
#     determine the coverage verdict (Covered / Partially Covered / Not Covered /
#     Needs Investigation), computes net payable after deductible and remaining limit,
#     and persists the result to coverage_verification_results.
#     """
#     return handler.verify_coverage(claim_id)


# @router.post(
#     "/api/policy_coverage/payment",
#     operation_id="record_claim_payment",
#     summary="Record an approved claim payment and reduce remaining policy coverage",
# )
# def record_claim_payment(req: RecordClaimPaymentRequest):
#     """
#     Records a payment released for an approved claim and reduces the
#     remaining_coverage_limit on the linked policy in the local policy_details table.
#     Also updates the claim status to 'Settled' and logs the payment in claim_payments.
#     """
#     try:
#         return handler.record_claim_payment(
#             req.claim_id, req.amount_paid, req.approved_by, req.notes
#         )
#     except Exception as e:
#         log.exception("record_claim_payment error")
#         raise HTTPException(status_code=500, detail=str(e))









"""
policy_coverage_router.py
──────────────────────────
Endpoints / MCP tools:
  gw_search_policy        POST /gw_search_policy
  gw_get_policy_coverages POST /gw_get_policy_coverages
  save_policy_details     POST /save_policy_details
  get_policy_details      GET  /get_policy_details/{policy_id}
  verify_coverage         POST /api/policy_coverage/verify/{claim_id}
  record_claim_payment    POST /api/policy_coverage/payment
"""

import logging
from fastapi import APIRouter, HTTPException
# import GetClaimDetailsRequest

from policy_coverage_mcp import handler
from policy_coverage_mcp.models import (
    GwSearchPolicyRequest,
    SavePolicyDetailsRequest,
    RecordClaimPaymentRequest,
    GetClaimDetailsRequest,
)

log = logging.getLogger(__name__)
router = APIRouter()

@router.post(
   "/get_claim_details",
   operation_id="get_claim_details",
   summary="Fetch claim details from local database",
)
def get_claim_details(req: GetClaimDetailsRequest):
   return handler.get_claim_details(req.claim_number)



@router.post(
    "/gw_search_policy",
    operation_id="gw_search_policy",
    summary="Search Guidewire PolicyCenter for a policy by policy number",
)
def gw_search_policy(req: GwSearchPolicyRequest):
    """
    Look up a policy in Guidewire PolicyCenter using the policy number.
    Returns found=True with policy details, or found=False with an error message.
    """
    return handler.gw_search_policy(req.policy_number)


@router.post(
    "/gw_get_policy_coverages",
    operation_id="gw_get_policy_coverages",
    summary="Fetch full policy coverage details from Guidewire",
)
def gw_get_policy_coverages(req: GwSearchPolicyRequest):
    """
    Fetches the detailed policy record from Guidewire PolicyCenter including
    all lines of business, coverage clauses, deductibles, and limits.
    """
    return handler.gw_get_policy_coverages(req.policy_number)


@router.post(
    "/save_policy_details",
    operation_id="save_policy_details",
    summary="Fetch policy from Guidewire and persist to local database",
)
def save_policy_details(req: SavePolicyDetailsRequest):
    """
    Calls Guidewire (search + coverage detail), extracts deductible, coverage limit,
    exclusions, and all policy metadata, then saves/updates the local policy_details table.
    Sets remaining_coverage_limit = coverage_limit on first save (preserved on updates).
    """
    try:
        return handler.save_policy_details(req.policy_number)
    except Exception as e:
        log.exception("save_policy_details error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/get_policy_details/{policy_number}",
    operation_id="get_policy_details",
    summary="Read policy details from the local database",
)
def get_policy_details(policy_number: str):
    """Returns the full policy_details record for the given policy_number."""
    record = handler.get_policy_details(policy_number)
    if not record:
        return {"status": "not_found", "policy_number": policy_number}
    return record


@router.get(
    "/api/policy_coverage/result/{claim_number}",
    operation_id="get_coverage_verification_result",
    summary="Read an existing coverage verification result for a claim",
)
def get_coverage_verification_result(claim_number: str):
    """
    Returns the most recent coverage verification result from the local DB
    without re-running the LLM. Returns found=False if none exists yet.
    """
    return handler.get_coverage_verification_result(claim_number)


@router.post(
    "/api/policy_coverage/verify/{claim_number}",
    operation_id="verify_coverage",
    summary="Verify whether a claim's loss is covered by the linked policy",
)
def verify_coverage(claim_number: str):
    """
    Looks up the claim and its linked policy from the local DB, uses the LLM to
    determine the coverage verdict (Covered / Partially Covered / Not Covered /
    Needs Investigation), computes net payable after deductible and remaining limit,
    and persists the result to coverage_verification_results.
    """
    return handler.verify_coverage(claim_number)


@router.post(
    "/api/policy_coverage/payment",
    operation_id="record_claim_payment",
    summary="Record an approved claim payment and reduce remaining policy coverage",
)
def record_claim_payment(req: RecordClaimPaymentRequest):
    """
    Records a payment released for an approved claim and reduces the
    remaining_coverage_limit on the linked policy in the local policy_details table.
    Also updates the claim status to 'Settled' and logs the payment in claim_payments.
    """
    try:
        return handler.record_claim_payment(
            req.claim_number, req.amount_paid, req.approved_by, req.notes
        )
    except Exception as e:
        log.exception("record_claim_payment error")
        raise HTTPException(status_code=500, detail=str(e))
