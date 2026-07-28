"""
handler.py — Fraud Escalation
────────────────────────────────
Creates SIU escalation records and opens SIU cases for claims forwarded
from Adjuster (or other) personas for investigation.
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


def create_siu_escalation(claim_id: str, escalation_reason: str, fraud_score: Optional[int] = None,
                           evidence_notes: Optional[str] = None, escalated_by: str = "Adjuster") -> dict:
    siu_id = f"SIUESC-{claim_id}-{_rand_suffix(4)}"
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO siu_escalation_records (siu_id, claim_id, escalation_reason, fraud_score,
                                                  evidence_notes, escalated_by, status)
            VALUES (%s,%s,%s,%s,%s,%s, 'Under Review')
            """,
            (siu_id, claim_id, escalation_reason, fraud_score, evidence_notes, escalated_by),
        )
        conn.commit()
        return {
            "id": cur.lastrowid, "siu_id": siu_id, "claim_id": claim_id,
            "escalation_reason": escalation_reason, "fraud_score": fraud_score,
            "evidence_notes": evidence_notes, "escalated_by": escalated_by, "status": "Under Review",
        }
    finally:
        conn.close()


def get_siu_escalation(claim_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM siu_escalation_records WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def create_siu_case(claim_id: str, assigned_investigator: str = "Unassigned") -> dict:
    siu_case_id = f"SIU-{datetime.now().year}-{_rand_suffix(4)}"
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO siu_case_master (siu_case_id, claim_id, status, assigned_investigator)
            VALUES (%s,%s, 'Open', %s)
            """,
            (siu_case_id, claim_id, assigned_investigator),
        )
        conn.commit()
        return {
            "id": cur.lastrowid, "siu_case_id": siu_case_id, "claim_id": claim_id,
            "status": "Open", "assigned_investigator": assigned_investigator,
        }
    finally:
        conn.close()


def log_siu_timeline_event(siu_case_id: str, claim_id: str, event_type: str, status: str) -> dict:
    event_id = f"EVT-{_rand_suffix(6)}"
    timestamp = datetime.now().isoformat()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO siu_timeline_events (event_id, siu_case_id, claim_id, event_type, status, timestamp)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (event_id, siu_case_id, claim_id, event_type, status, timestamp),
        )
        conn.commit()
        return {
            "id": cur.lastrowid, "event_id": event_id, "siu_case_id": siu_case_id,
            "claim_id": claim_id, "event_type": event_type, "status": status, "timestamp": timestamp,
        }
    finally:
        conn.close()


def _get_claim(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_id,))
        row = cur.fetchone()
        if row:
            return row_to_dict(row)
        if claim_id.isdigit():
            cur.execute("SELECT * FROM claims WHERE id = %s", (int(claim_id),))
            return row_to_dict(cur.fetchone())
        return None
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


def _insert_siu_claim_master(claim_id: str, policy_id: Optional[str], loss_type: Optional[str], fraud_flag: bool) -> None:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO siu_claim_master (claim_id, stage, status, policy_id, loss_type, fnol_complete, fraud_flag)
            VALUES (%s, 'Investigation', 'Open', %s, %s, 'Yes', %s)
            """,
            (claim_id, policy_id, loss_type, 1 if fraud_flag else 0),
        )
        conn.commit()
    finally:
        conn.close()


def forward_to_siu(claim_id: str, escalation_reason: str, evidence_notes: Optional[str] = None,
                    escalated_by: str = "Adjuster") -> dict:
    fraud_score = _get_fraud_score(claim_id)

    escalation = create_siu_escalation(claim_id, escalation_reason, fraud_score, evidence_notes, escalated_by)
    case = create_siu_case(claim_id, assigned_investigator="Unassigned")
    timeline_event = log_siu_timeline_event(case["siu_case_id"], claim_id, event_type="Case Opened", status="Open")

    claim = _get_claim(claim_id)
    policy_id = claim.get("policy_number") if claim else None
    loss_type = claim.get("loss_type") if claim else None
    fraud_flag = fraud_score is not None and fraud_score >= 70

    _insert_siu_claim_master(claim_id, policy_id, loss_type, fraud_flag)

    return {
        "claim_id": claim_id,
        "escalation": escalation,
        "siu_case": case,
        "timeline_event": timeline_event,
        "fraud_score": fraud_score,
        "fraud_flag": fraud_flag,
    }
