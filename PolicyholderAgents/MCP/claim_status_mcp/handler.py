"""
handler.py — Claim Status ("Follow My Claim")
─────────────────────────────────────────────
Reads/writes claim journey, SLA tracking, and policyholder action log.
"""

import logging
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)


def get_claim_journey(claim_number: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM claim_journey_master WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        journey = row_to_dict(cur.fetchone())

        cur.execute(
            "SELECT * FROM stage_time_sla_tracking WHERE claim_number = %s ORDER BY stage_number",
            (claim_number,),
        )
        stages = row_to_dict(cur.fetchall())

        return {"journey": journey, "stages": stages}
    finally:
        conn.close()


def get_claim_status_summary(claim_number: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_number,))
        claim = row_to_dict(cur.fetchone())
        if not claim:
            return {"error": f"Claim {claim_number} not found"}

        cur.execute(
            "SELECT * FROM claim_journey_master WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        journey = row_to_dict(cur.fetchone()) or {}

        return {
            "claim_number": claim_number,
            "status": claim.get("status"),
            "current_stage": journey.get("current_stage"),
            "current_stage_name": journey.get("current_stage_name"),
            "sub_status": journey.get("sub_status"),
            "overall_sla_status": journey.get("overall_sla_status"),
            "expected_completion_date": journey.get("expected_completion_date"),
        }
    finally:
        conn.close()


def advance_claim_stage(claim_number: str, new_stage: int, stage_name: str,
                         sub_status: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT id FROM claims WHERE claim_number = %s", (claim_number,))
        claim_row = cur.fetchone()
        claim_id = claim_row["id"] if claim_row else None

        cur.execute(
            "SELECT id FROM claim_journey_master WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        journey_row = cur.fetchone()

        if journey_row:
            set_clauses = ["current_stage = %s", "current_stage_name = %s", "last_stage_change_date = NOW()"]
            params = [new_stage, stage_name]
            if sub_status is not None:
                set_clauses.append("sub_status = %s")
                params.append(sub_status)
            params.append(journey_row["id"])
            cur.execute(
                f"UPDATE claim_journey_master SET {', '.join(set_clauses)} WHERE id = %s",
                params,
            )
        else:
            cur.execute(
                """
                INSERT INTO claim_journey_master (
                    claim_id, claim_number, current_stage, current_stage_name, sub_status
                ) VALUES (%s,%s,%s,%s,%s)
                """,
                (claim_id, claim_number, new_stage, stage_name, sub_status or "Under Review"),
            )

        cur.execute(
            """
            INSERT INTO stage_time_sla_tracking (
                claim_id, claim_number, stage_number, stage_name, entered_at
            ) VALUES (%s,%s,%s,%s,NOW())
            """,
            (claim_id, claim_number, new_stage, stage_name),
        )

        conn.commit()
        return get_claim_journey(claim_number)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def log_policyholder_action(claim_number: str, action_type: str, action_label: str,
                             details: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT id FROM claims WHERE claim_number = %s", (claim_number,))
        claim_row = cur.fetchone()
        claim_id = claim_row["id"] if claim_row else None

        cur.execute(
            "SELECT current_stage FROM claim_journey_master WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        journey_row = cur.fetchone()
        stage = journey_row["current_stage"] if journey_row else None

        cur.execute(
            """
            INSERT INTO policyholder_actions (
                claim_row_id, claim_number, action_type, action_label, details,
                stage_at_action, performed_by, timestamp
            ) VALUES (%s,%s,%s,%s,%s,%s,'Policyholder',NOW())
            RETURNING *
            """,
            (claim_id, claim_number, action_type, action_label, details, stage),
        )
        result = row_to_dict(cur.fetchone())
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_policyholder_actions(claim_number: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM policyholder_actions WHERE claim_number = %s ORDER BY timestamp DESC",
            (claim_number,),
        )
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()
