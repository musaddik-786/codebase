"""
handler.py — Legal Escalation
─────────────────────────────────
Refers confirmed-fraud SIU cases to the Legal team.
"""

import logging
import os
import random
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)


def _rand_suffix(n: int) -> str:
    return "".join(random.choices("0123456789", k=n))


def create_legal_escalation(siu_case_id: str, claim_id: str, reason: str,
                             fraud_score: Optional[int] = None, referred_by: str = "SIU Investigator") -> dict:
    escalation_id = f"LEGAL-{claim_id}-{_rand_suffix(4)}"
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO legal_escalations (escalation_id, siu_case_id, claim_id, reason, fraud_score,
                                            status, referred_by)
            VALUES (%s,%s,%s,%s,%s, 'Pending Review', %s)
            """,
            (escalation_id, siu_case_id, claim_id, reason, fraud_score, referred_by),
        )
        conn.commit()
        return {
            "id": cur.lastrowid, "escalation_id": escalation_id, "siu_case_id": siu_case_id,
            "claim_id": claim_id, "reason": reason, "fraud_score": fraud_score,
            "status": "Pending Review", "referred_by": referred_by,
        }
    finally:
        conn.close()


def get_legal_escalation(claim_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM legal_escalations WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def update_legal_escalation_outcome(escalation_id: str, status: str, outcome: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE legal_escalations SET status = %s, outcome = %s WHERE escalation_id = %s",
            (status, outcome, escalation_id),
        )
        conn.commit()
        cur.execute("SELECT * FROM legal_escalations WHERE escalation_id = %s", (escalation_id,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def _get_latest_siu_case(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM siu_case_master WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def _get_latest_decision(siu_case_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM siu_decision WHERE siu_case_id = %s ORDER BY id DESC LIMIT 1",
            (siu_case_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def _get_fraud_score(claim_id: str) -> Optional[int]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT fraud_score FROM fraud_risk_snapshots WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        row = cur.fetchone()
        return row["fraud_score"] if row else None
    finally:
        conn.close()


def _log_activity(siu_case_id: str, claim_id: str, activity: str) -> str:
    activity_id = f"ACT-{_rand_suffix(6)}"
    timestamp = datetime.now().isoformat()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO siu_activity_log (activity_id, siu_case_id, claim_id, activity, status, owner, timestamp)
            VALUES (%s,%s,%s,%s, 'Completed', 'SIU Investigator', %s)
            """,
            (activity_id, siu_case_id, claim_id, activity, timestamp),
        )
        conn.commit()
        return activity_id
    finally:
        conn.close()


def refer_to_legal(claim_id: str) -> dict:
    siu_case = _get_latest_siu_case(claim_id)
    if not siu_case:
        return {"claim_id": claim_id, "referred": False, "reason": "No SIU case found for this claim"}

    siu_case_id = siu_case["siu_case_id"]
    decision = _get_latest_decision(siu_case_id)

    if not decision or decision.get("decision") != "Fraud Confirmed":
        return {
            "claim_id": claim_id,
            "siu_case_id": siu_case_id,
            "referred": False,
            "reason": "Legal referral not applicable — SIU decision is not 'Fraud Confirmed'",
            "current_decision": decision.get("decision") if decision else None,
        }

    fraud_score = _get_fraud_score(claim_id)
    reason = f"SIU investigation concluded 'Fraud Confirmed' for claim {claim_id} (fraud_score={fraud_score})."

    escalation = create_legal_escalation(siu_case_id, claim_id, reason, fraud_score, referred_by="SIU Investigator")
    activity_id = _log_activity(siu_case_id, claim_id, f"Referred to Legal: {escalation['escalation_id']}")

    return {
        "claim_id": claim_id,
        "siu_case_id": siu_case_id,
        "referred": True,
        "escalation": escalation,
        "activity_id": activity_id,
    }
