"""
handler.py — Fraud Resolution
─────────────────────────────────
Records SIU investigation decisions and closes out SIU cases.
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

VALID_DECISIONS = {"Fraud Confirmed", "Fraud Cleared", "Inconclusive"}


def _rand_suffix(n: int) -> str:
    return "".join(random.choices("0123456789", k=n))


def write_siu_decision(siu_case_id: str, claim_id: str, decision: str,
                        confidence: Optional[float] = None, closed_date: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO siu_decision (siu_case_id, claim_id, decision, confidence, closed_date)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (siu_case_id, claim_id, decision, confidence, closed_date),
        )
        conn.commit()
        return {
            "id": cur.lastrowid, "siu_case_id": siu_case_id, "claim_id": claim_id,
            "decision": decision, "confidence": confidence, "closed_date": closed_date,
        }
    finally:
        conn.close()


def get_siu_decision(siu_case_id: str) -> dict:
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


def resolve_siu_case(siu_case_id: str, claim_id: str, decision: str,
                      confidence: Optional[float] = None, notes: Optional[str] = None) -> dict:
    closed_date = datetime.now().isoformat()
    decision_row = write_siu_decision(siu_case_id, claim_id, decision, confidence, closed_date)

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Close the SIU case
        cur.execute(
            "UPDATE siu_case_master SET status = 'Closed' WHERE siu_case_id = %s",
            (siu_case_id,),
        )

        # Update the most recent escalation record for this claim
        cur.execute(
            "SELECT id FROM siu_escalation_records WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        esc_row = cur.fetchone()
        if esc_row:
            cur.execute(
                "UPDATE siu_escalation_records SET status = %s WHERE id = %s",
                (f"Resolved - {decision}", esc_row["id"]),
            )

        # Log timeline event
        event_id = f"EVT-{_rand_suffix(6)}"
        timestamp = datetime.now().isoformat()
        cur.execute(
            """
            INSERT INTO siu_timeline_events (event_id, siu_case_id, claim_id, event_type, status, timestamp)
            VALUES (%s,%s,%s, 'Case Resolved', %s, %s)
            """,
            (event_id, siu_case_id, claim_id, decision, timestamp),
        )

        # Log activity
        activity_id = f"ACT-{_rand_suffix(6)}"
        activity = f"Case resolved: {decision}"
        if notes:
            activity += f" — {notes}"
        cur.execute(
            """
            INSERT INTO siu_activity_log (activity_id, siu_case_id, claim_id, activity, status, owner, timestamp)
            VALUES (%s,%s,%s,%s, 'Completed', 'SIU Investigator', %s)
            """,
            (activity_id, siu_case_id, claim_id, activity, timestamp),
        )

        # If fraud confirmed, update siu_claim_master.fraud_flag
        if decision == "Fraud Confirmed":
            cur.execute(
                "UPDATE siu_claim_master SET fraud_flag = 1 WHERE claim_id = %s",
                (claim_id,),
            )

        conn.commit()

        return {
            "siu_case_id": siu_case_id,
            "claim_id": claim_id,
            "decision": decision_row,
            "case_status": "Closed",
            "escalation_updated": bool(esc_row),
            "timeline_event_id": event_id,
            "activity_id": activity_id,
            "fraud_flag_set": decision == "Fraud Confirmed",
        }
    finally:
        conn.close()
