"""
handler.py — Orchestration (Adjuster-local copy)
──────────────────────────────────────────────────
Reads/writes claim_orchestration_state and human_approval_requests in the
shared Azure PostgreSQL database. Originally owned exclusively by
OrchestratorAgent/MCP/orchestration_mcp — copied here so AdjusterOrchestrator
and the claims-solution-integration UI no longer need OrchestratorAgent's
process running at all for HITL approval gates. Same table names as the
original (human_approval_requests, claim_orchestration_state) — one shared
Postgres database across all personas, so this is the exact same data, just
reachable through a second, self-contained door owned by AdjusterAgents.
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
                              requested_by: str = "AdjusterOrchestrator") -> dict:
    """
    Idempotent per (claim_id, gate_type): if a Pending request already exists,
    refreshes its summary/requested_by/requested_at instead of inserting a
    duplicate. This is enforced here rather than relying on the LLM to check
    first, since AdjusterOrchestrator's local conversation history resets on
    every fresh "Run" — the LLM has no memory across separate runs to know a
    prior request exists, but the DB does. Without this, audit-only gates
    (e.g. triage_approval, which the prompt always opens unconditionally,
    never checking first since it never blocks) would accumulate one new
    Pending row per run, forever.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT approval_id FROM human_approval_requests WHERE claim_id = %s AND gate_type = %s AND status = 'Pending' ORDER BY id DESC LIMIT 1",
            (claim_id, gate_type),
        )
        existing = cur.fetchone()
        if existing:
            approval_id = existing["approval_id"]
            now = datetime.now().isoformat()
            cur.execute(
                "UPDATE human_approval_requests SET summary = %s, requested_by = %s, requested_at = %s WHERE approval_id = %s",
                (summary, requested_by, now, approval_id),
            )
            conn.commit()
            return {
                "id": None,
                "approval_id": approval_id,
                "claim_id": claim_id,
                "gate_type": gate_type,
                "status": "Pending",
                "summary": summary,
                "requested_by": requested_by,
                "refreshed": True,
            }

        approval_id = f"APR-{_rand_suffix(6)}"
        cur.execute(
            """
            INSERT INTO human_approval_requests (approval_id, claim_id, gate_type, status, summary, requested_by)
            VALUES (%s,%s,%s, 'Pending', %s, %s)
            RETURNING id
            """,
            (approval_id, claim_id, gate_type, summary, requested_by),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return {
            "id": new_id,
            "approval_id": approval_id,
            "claim_id": claim_id,
            "gate_type": gate_type,
            "status": "Pending",
            "summary": summary,
            "requested_by": requested_by,
            "refreshed": False,
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


# ── Claim journey stage 7 advancement (2026-07-23) ──────────────────────────
# See AdjusterAgents/AdjusterOrchestrator/server.py's own "Claim journey
# stage advancement" comment block for the full picture (stages 2-6 wired
# there, stage 8 wired in its /payment-decision endpoint). Stage 7 "Decision
# & Settlement" lives here instead because reserve_approval/settlement_approval/
# financial_leakage_review are decided independently, from three separate
# Loss Assessment page save actions — this decide_approval function is the
# ONE place all three (and every other gate) funnel through, so it's the
# natural single checkpoint rather than three separate frontend call sites.
_JOURNEY_STAGE_NUMBERS = {
    "Claim Initiated": 1,
    "Claim Intake Validation": 2,
    "Segmentation & Triage": 3,
    "Loss Investigation": 4,
    "Loss Assessment": 5,
    "Decision Pending": 6,
    "Decision & Settlement": 7,
    "Claim Closed": 8,
}

_DECISION_SETTLEMENT_GATES = {"reserve_approval", "settlement_approval", "financial_leakage_review"}


def _advance_claim_journey_stage(claim_number: str, stage_name: str, sub_status: Optional[str] = None) -> None:
    """
    Direct-SQL equivalent of PolicyholderAgents' advance_claim_stage tool —
    duplicated here (rather than imported) matching this codebase's existing
    per-agent-module convention. Never moves current_stage backward. Also
    fixes a bug found in the original tool: its stage_time_sla_tracking
    INSERT used a nonexistent "entered_at" column (real column:
    stage_start_time) — since that INSERT shared a transaction with the
    claim_journey_master update and a single trailing commit, that bug meant
    the original tool would silently roll back its own journey update too,
    every time it's ever called.
    """
    new_stage = _JOURNEY_STAGE_NUMBERS[stage_name]
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM claims WHERE claim_number = %s", (claim_number,))
        claim_row = row_to_dict(cur.fetchone())
        claim_id = claim_row.get("id") if claim_row else None

        cur.execute(
            "SELECT id, current_stage FROM claim_journey_master WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        journey_row = row_to_dict(cur.fetchone())

        if journey_row:
            if (journey_row.get("current_stage") or 0) >= new_stage:
                return
            set_clauses = ["current_stage = %s", "current_stage_name = %s", "last_stage_change_date = NOW()"]
            params = [new_stage, stage_name]
            if sub_status is not None:
                set_clauses.append("sub_status = %s")
                params.append(sub_status)
            params.append(journey_row["id"])
            cur.execute(f"UPDATE claim_journey_master SET {', '.join(set_clauses)} WHERE id = %s", params)
        else:
            cur.execute(
                """INSERT INTO claim_journey_master
                   (claim_id, claim_number, current_stage, current_stage_name, sub_status)
                   VALUES (%s,%s,%s,%s,%s)""",
                (claim_id, claim_number, new_stage, stage_name, sub_status or "Under Review"),
            )

        cur.execute(
            """INSERT INTO stage_time_sla_tracking
               (claim_id, claim_number, stage_number, stage_name, stage_start_time)
               VALUES (%s,%s,%s,%s,NOW())""",
            (claim_id, claim_number, new_stage, stage_name),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        log.exception("ADVANCE_CLAIM_STAGE_FAILED claim=%s stage=%s", claim_number, stage_name)
    finally:
        conn.close()


def _maybe_advance_to_decision_settlement(claim_id: str) -> None:
    """Advances to stage 7 once reserve_approval, settlement_approval, AND
    financial_leakage_review are all Approved for this claim (checks the
    latest decision for each, not just the one that just got decided)."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT gate_type, status FROM human_approval_requests "
            "WHERE claim_id = %s AND gate_type = ANY(%s) ORDER BY id DESC",
            (claim_id, list(_DECISION_SETTLEMENT_GATES)),
        )
        rows = row_to_dict(cur.fetchall())
    finally:
        conn.close()

    latest_status_by_gate = {}
    for row in rows:
        gate = row.get("gate_type")
        if gate not in latest_status_by_gate:
            latest_status_by_gate[gate] = row.get("status")

    if all(latest_status_by_gate.get(g) == "Approved" for g in _DECISION_SETTLEMENT_GATES):
        _advance_claim_journey_stage(
            claim_id, "Decision & Settlement",
            sub_status="Reserve, Settlement, and Financial Leakage all approved",
        )
        set_claim_orchestration_state(
            claim_id, "Decision & Settlement", status="In Progress",
            last_action="Reserve, Settlement, and Financial Leakage all approved",
        )


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
        result = row_to_dict(cur.fetchone())
    finally:
        conn.close()

    if result and decision == "Approved" and result.get("gate_type") in _DECISION_SETTLEMENT_GATES:
        _maybe_advance_to_decision_settlement(result.get("claim_id"))

    return result


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
