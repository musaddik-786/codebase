"""
handler.py — Fraud Risk Scoring
────────────────────────────────
Reads fraud signals/flags/snapshots for a claim, and recomputes an
aggregate fraud risk snapshot for SIU investigators.
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)


def get_fraud_risk_snapshot(claim_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM fraud_risk_snapshots WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_ai_fraud_signals(claim_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ai_fraud_signals WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def get_fraud_flags(claim_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM fraud_flags WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def recompute_fraud_risk_score(claim_id: str) -> dict:
    """
    Reads all ai_fraud_signals and fraud_flags for the claim, computes an
    aggregate fraud_score (average of signal scores, weighted up if any
    active flag has risk_score >= 70), red_flag_count = count of active
    fraud_flags, and prior_claims/vendor_risk heuristics (default "Low"
    unless an active flag suggests otherwise). Upserts a new
    fraud_risk_snapshots row and returns it.
    """
    signals = get_ai_fraud_signals(claim_id)
    flags = get_fraud_flags(claim_id)

    if signals:
        avg_score = sum(int(s.get("fraud_score") or 0) for s in signals) / len(signals)
    else:
        avg_score = 0.0

    active_flags = [f for f in flags if (f.get("status") or "Active") == "Active"]
    high_risk_flag = any(int(f.get("risk_score") or 0) >= 70 for f in active_flags)

    fraud_score = avg_score
    if high_risk_flag:
        fraud_score = min(100, fraud_score + 20)
    fraud_score = round(fraud_score)

    red_flag_count = len(active_flags)

    prior_claims = "High" if red_flag_count >= 3 else "Low"
    vendor_risk = "High" if high_risk_flag else "Low"

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO fraud_risk_snapshots (claim_id, fraud_score, red_flag_count, prior_claims, vendor_risk)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (claim_id, fraud_score, red_flag_count, prior_claims, vendor_risk),
        )
        conn.commit()
        return {
            "id": cur.lastrowid,
            "claim_id": claim_id,
            "fraud_score": fraud_score,
            "red_flag_count": red_flag_count,
            "prior_claims": prior_claims,
            "vendor_risk": vendor_risk,
            "signal_count": len(signals),
            "active_flag_count": red_flag_count,
        }
    finally:
        conn.close()
