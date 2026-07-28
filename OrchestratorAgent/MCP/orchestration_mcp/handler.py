"""
handler.py — Orchestration
───────────────────────────
Reads/writes claim_orchestration_state and human_approval_requests in the
shared SQLite database. Used by the Brain Agent to track stage progression
and human-in-the-loop (HITL) approval gates across the whole claim lifecycle.
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


def get_claim_orchestration_state(claim_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM claim_orchestration_state WHERE claim_id = %s",
            (claim_id,),
        )
        row = cur.fetchone()
        if row is None:
            return {
                "claim_id": claim_id,
                "current_stage": None,
                "status": None,
                "last_action": None,
                "found": False,
            }
        result = row_to_dict(row)
        result["found"] = True
        return result
    finally:
        conn.close()


def set_claim_orchestration_state(claim_id: str, current_stage: str,
                                   status: Optional[str] = None,
                                   last_action: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, status FROM claim_orchestration_state WHERE claim_id = %s", (claim_id,))
        row = cur.fetchone()
        now = datetime.now().isoformat()
        if row is None:
            cur.execute(
                """
                INSERT INTO claim_orchestration_state (claim_id, current_stage, status, last_action, updated_at)
                VALUES (%s,%s,%s,%s,%s)
                """,
                (claim_id, current_stage, status or "Open", last_action, now),
            )
        else:
            effective_status = status if status is not None else row["status"]
            cur.execute(
                """
                UPDATE claim_orchestration_state
                SET current_stage = %s, status = %s, last_action = %s, updated_at = %s
                WHERE claim_id = %s
                """,
                (current_stage, effective_status, last_action, now, claim_id),
            )
        conn.commit()
        return get_claim_orchestration_state(claim_id)
    finally:
        conn.close()


def create_approval_request(claim_id: str, gate_type: str, summary: str,
                              requested_by: str = "Orchestrator") -> dict:
    approval_id = f"APR-{_rand_suffix(6)}"
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO human_approval_requests (approval_id, claim_id, gate_type, status, summary, requested_by)
            VALUES (%s,%s,%s, 'Pending', %s, %s)
            """,
            (approval_id, claim_id, gate_type, summary, requested_by),
        )
        conn.commit()
        return {
            "id": cur.lastrowid,
            "approval_id": approval_id,
            "claim_id": claim_id,
            "gate_type": gate_type,
            "status": "Pending",
            "summary": summary,
            "requested_by": requested_by,
        }
    finally:
        conn.close()


def get_pending_approvals(claim_id: Optional[str] = None, gate_type: Optional[str] = None) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query = "SELECT * FROM human_approval_requests WHERE status = 'Pending'"
        params = []
        if claim_id:
            query += " AND claim_id = %s"
            params.append(claim_id)
        if gate_type:
            query += " AND gate_type = %s"
            params.append(gate_type)
        query += " ORDER BY id DESC"
        cur.execute(query, params)
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def decide_approval(approval_id: str, decision: str, decided_by: str,
                     notes: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        now = datetime.now().isoformat()
        cur.execute(
            """
            UPDATE human_approval_requests
            SET status = %s, decided_by = %s, decided_at = %s, decision_notes = %s
            WHERE approval_id = %s
            """,
            (decision, decided_by, now, notes, approval_id),
        )
        conn.commit()
        cur.execute("SELECT * FROM human_approval_requests WHERE approval_id = %s", (approval_id,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_approval_status(claim_id: str, gate_type: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM human_approval_requests
            WHERE claim_id = %s AND gate_type = %s
            ORDER BY id DESC LIMIT 1
            """,
            (claim_id, gate_type),
        )
        row = cur.fetchone()
        if row is None:
            return {"claim_id": claim_id, "gate_type": gate_type, "status": "None", "approval_id": None}
        result = row_to_dict(row)
        return result
    finally:
        conn.close()
