"""
handler.py — Payment Trigger
────────────────────────────────
Checks claim approval status (via adjuster_findings.coverage_confirmed) and
triggers payment_disbursements rows.

Amount source priority:
  1. loss_estimation_outputs.net_payable  (most authoritative — set by LossAssessmentAgent)
  2. adjuster_findings.final_settlement
  3. adjuster_findings.adjusted_reserve

Write-back on disbursement created:
  - INSERT payment_disbursements (status = 'Initiated')
  - UPDATE claims.status = 'Payment Initiated'
"""

import logging
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)

_APPROVED_VALUES = {"yes", "confirmed"}


def check_claim_approved(claim_number: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM adjuster_findings WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        finding = row_to_dict(cur.fetchone())

        # net_payable from loss_estimation_outputs is the most authoritative amount
        cur.execute(
            "SELECT net_payable FROM loss_estimation_outputs WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        loss_row = row_to_dict(cur.fetchone())
    finally:
        conn.close()

    if not finding:
        return {
            "claim_number": claim_number,
            "approved": False,
            "reason": "No adjuster findings on record for this claim.",
            "available_amount": None,
        }

    coverage_confirmed = (finding.get("coverage_confirmed") or "").strip().lower()
    approved = coverage_confirmed in _APPROVED_VALUES

    # Priority: net_payable → final_settlement → adjusted_reserve
    net_payable = float(loss_row.get("net_payable") or 0) if loss_row else 0
    available_amount = net_payable if net_payable > 0 else finding.get("final_settlement")
    if available_amount in (None, 0):
        available_amount = finding.get("adjusted_reserve")

    return {
        "claim_number": claim_number,
        "approved": approved,
        "coverage_confirmed": finding.get("coverage_confirmed"),
        "available_amount": available_amount,
        "amount_source": (
            "loss_estimation_outputs.net_payable" if net_payable > 0
            else ("adjuster_findings.final_settlement" if finding.get("final_settlement") else "adjuster_findings.adjusted_reserve")
        ),
        "reason": None if approved else f"coverage_confirmed is '{finding.get('coverage_confirmed')}', not approved.",
    }


def get_payment_eligibility(claim_number: str) -> dict:
    """Reads the latest auto_adjudication_records row for the claim (written by PaymentEligibilityAgent)."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM auto_adjudication_records WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        record = row_to_dict(cur.fetchone())
    finally:
        conn.close()

    if not record:
        return {
            "claim_number": claim_number,
            "eligibility_checked": False,
            "eligible_for_auto_adjudication": False,
            "reason": "PaymentEligibilityAgent has not run for this claim. Run it before triggering payment.",
        }

    return {
        "claim_number": claim_number,
        "eligibility_checked": True,
        "eligible_for_auto_adjudication": record.get("eligible_for_auto_adjudication"),
        "decision": record.get("decision"),
        "stp_category": record.get("stp_category"),
        "failed_gate_list": record.get("failed_gate_list"),
        "threshold_config_id": record.get("threshold_config_id"),
        "recommendation": record.get("recommendation"),
    }


def create_payment_disbursement(claim_number: str, amount: float, payment_method: str, approved_by: str) -> dict:
    # Read eligibility — informational context, hard block only for Full STP path
    eligibility = get_payment_eligibility(claim_number)
    stp_category = (eligibility.get("stp_category") or "").strip()
    eligible = eligibility.get("eligible_for_auto_adjudication")
    eligibility_checked = eligibility.get("eligibility_checked", False)

    # Block only when the claim explicitly went through Full STP and failed eligibility gates
    if eligibility_checked and stp_category == "Full STP" and not eligible:
        return {
            "claim_number": claim_number,
            "error": "Payment blocked — Full STP claim did not pass all eligibility gates.",
            "reason": (
                f"stp_category is 'Full STP' but eligible_for_auto_adjudication is false. "
                f"Failed gates: {eligibility.get('failed_gate_list')}"
            ),
            "stp_category": stp_category,
        }

    # Gate: coverage must be confirmed (applies to all paths — STP and manual)
    approval = check_claim_approved(claim_number)
    if not approval["approved"]:
        return {
            "claim_number": claim_number,
            "error": "Claim is not approved for payment.",
            "reason": approval["reason"],
        }

    # Gate: net payable amount must be greater than 0
    available_amount = approval.get("available_amount")
    if not available_amount or float(available_amount) <= 0:
        return {
            "claim_number": claim_number,
            "error": "Payment cannot be initiated — net payable amount is zero or not yet calculated.",
            "reason": "Run LossAssessmentAgent first to calculate the net payable amount.",
            "amount_source": approval.get("amount_source"),
        }

    payment_id = f"PAY-{claim_number}-{uuid.uuid4().hex[:8].upper()}"

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM claims WHERE claim_number = %s", (claim_number,))
        claims_row = cur.fetchone()
        integer_claim_id = claims_row["id"] if claims_row else None

        cur.execute(
            """
            INSERT INTO payment_disbursements (
                payment_id, claim_id, claim_number, amount, payment_method, status, triggered_by, approved_by
            ) VALUES (%s, %s, %s, %s, %s, 'Initiated', 'PaymentTriggerAgent', %s)
            RETURNING id
            """,
            (payment_id, integer_claim_id, claim_number, amount, payment_method, approved_by),
        )
        new_id = cur.fetchone()["id"]

        cur.execute(
            "UPDATE claims SET status = 'Payment Initiated' WHERE claim_number = %s",
            (claim_number,),
        )
        conn.commit()
        return {
            "id": new_id,
            "payment_id": payment_id,
            "claim_id": integer_claim_id,
            "claim_number": claim_number,
            "amount": amount,
            "payment_method": payment_method,
            "status": "Initiated",
            "triggered_by": "PaymentTriggerAgent",
            "approved_by": approved_by,
            "stp_category": stp_category or "Not evaluated",
            "eligibility_path": "Full STP" if stp_category == "Full STP" else "Manual / Non-STP",
        }
    finally:
        conn.close()


def update_payment_status(payment_id: str, status: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if status == "Completed":
            cur.execute(
                "UPDATE payment_disbursements SET status = %s, completed_at = NOW() WHERE payment_id = %s",
                (status, payment_id),
            )
        else:
            cur.execute(
                "UPDATE payment_disbursements SET status = %s WHERE payment_id = %s",
                (status, payment_id),
            )
        conn.commit()
        cur.execute("SELECT * FROM payment_disbursements WHERE payment_id = %s", (payment_id,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_payment_disbursements(claim_number: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM payment_disbursements WHERE claim_number = %s ORDER BY id DESC",
            (claim_number,),
        )
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()
