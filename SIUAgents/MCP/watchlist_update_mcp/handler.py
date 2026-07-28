"""
handler.py — Watchlist Update
─────────────────────────────────
Maintains the SIU fraud watchlist (entities flagged for confirmed fraud).
"""

import logging
import os
import random
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)


def _rand_suffix(n: int) -> str:
    return "".join(random.choices("0123456789", k=n))


def add_to_watchlist(entity_type: str, entity_id: str, entity_name: str, reason: str,
                      severity: str = "Medium", added_by: str = "SIU Investigator") -> dict:
    watchlist_id = f"WL-{_rand_suffix(6)}"
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO fraud_watchlist (watchlist_id, entity_type, entity_id, entity_name, reason,
                                          severity, added_by, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s, 'Active')
            """,
            (watchlist_id, entity_type, entity_id, entity_name, reason, severity, added_by),
        )
        conn.commit()
        return {
            "id": cur.lastrowid, "watchlist_id": watchlist_id, "entity_type": entity_type,
            "entity_id": entity_id, "entity_name": entity_name, "reason": reason,
            "severity": severity, "added_by": added_by, "status": "Active",
        }
    finally:
        conn.close()


def get_watchlist(entity_type: Optional[str] = None) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if entity_type:
            cur.execute("SELECT * FROM fraud_watchlist WHERE entity_type = %s ORDER BY id DESC", (entity_type,))
        else:
            cur.execute("SELECT * FROM fraud_watchlist ORDER BY id DESC")
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def check_watchlist(entity_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM fraud_watchlist WHERE entity_id = %s AND status = 'Active' ORDER BY id DESC",
            (entity_id,),
        )
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def remove_from_watchlist(watchlist_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE fraud_watchlist SET status = 'Removed' WHERE watchlist_id = %s", (watchlist_id,))
        conn.commit()
        cur.execute("SELECT * FROM fraud_watchlist WHERE watchlist_id = %s", (watchlist_id,))
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


def update_watchlist_from_case(claim_id: str) -> dict:
    siu_case = _get_latest_siu_case(claim_id)
    if not siu_case:
        return {"claim_id": claim_id, "watchlisted": False, "reason": "No SIU case found for this claim"}

    decision = _get_latest_decision(siu_case["siu_case_id"])
    if not decision or decision.get("decision") != "Fraud Confirmed":
        return {
            "claim_id": claim_id,
            "watchlisted": False,
            "reason": "No watchlist action taken — SIU decision is not 'Fraud Confirmed'",
            "current_decision": decision.get("decision") if decision else None,
        }

    claim = _get_claim(claim_id)
    if not claim:
        return {"claim_id": claim_id, "watchlisted": False, "reason": "Claim not found"}

    policy_number = claim.get("policy_number")
    policyholder_name = claim.get("policyholder_name")

    entry = add_to_watchlist(
        entity_type="policyholder",
        entity_id=policy_number,
        entity_name=policyholder_name,
        reason=f"Confirmed fraud on claim {claim_id}",
        severity="High",
    )

    return {"claim_id": claim_id, "watchlisted": True, "watchlist_entry": entry}
