"""
handler.py — Feedback / Sentiment Tracking
─────────────────────────────────────────────
Records per-stage customer feedback with LLM sentiment classification,
and maintains an aggregate claim_sentiment_tracker row.

stage_number and stage_name are auto-looked up from claim_journey_master
when not provided — policyholders don't know their stage number.
sentiment_score is persisted to customer_feedback_per_stage for accurate
trend analysis.
"""

import json
import logging
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from dotenv import load_dotenv, find_dotenv
from openai import AzureOpenAI

load_dotenv(find_dotenv())

log = logging.getLogger(__name__)

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-claims")


def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


def _classify_sentiment(comment: str) -> dict:
    try:
        client = _get_openai_client()
        prompt = (
            "Classify the sentiment of this insurance claim policyholder feedback "
            "comment. Return JSON: "
            '{"sentiment": "Positive"|"Neutral"|"Negative", "sentiment_score": 0-100}.\n\n'
            f"Comment: {comment}"
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "sentiment": result.get("sentiment", "Neutral"),
            "sentiment_score": result.get("sentiment_score", 50),
        }
    except Exception as e:
        log.warning("sentiment classification failed: %s", e)
        return {"sentiment": "Neutral", "sentiment_score": 50}


def _lookup_current_stage(claim_number: str) -> tuple:
    """Return (stage_number, stage_name) from claim_journey_master, or (1, 'Claim Initiated')."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT current_stage, current_stage_name FROM claim_journey_master "
            "WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        row = cur.fetchone()
        if row:
            return row["current_stage"], row["current_stage_name"]
        return 1, "Claim Initiated"
    finally:
        conn.close()


def write_customer_feedback(
    claim_number: str,
    comment: str,
    claim_id: Optional[str] = None,
    stage_number: Optional[int] = None,
    stage_name: Optional[str] = None,
) -> dict:
    # Auto-lookup stage if not provided — policyholder won't know their stage number
    if not stage_number or not stage_name:
        stage_number, stage_name = _lookup_current_stage(claim_number)

    # Resolve integer claim_id from claims table if not explicitly provided
    if not claim_id:
        try:
            _conn = get_db_connection()
            _cur = _conn.cursor()
            _cur.execute("SELECT id FROM claims WHERE claim_number = %s LIMIT 1", (claim_number,))
            _row = _cur.fetchone()
            claim_id = _row["id"] if _row else None
            _conn.close()
        except Exception:
            claim_id = None

    classification = _classify_sentiment(comment)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO customer_feedback_per_stage (
                claim_id, claim_number, stage_number, stage_name,
                sentiment, sentiment_score, comment, submitted_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING *
            """,
            (
                claim_id, claim_number, stage_number, stage_name,
                classification["sentiment"], classification["sentiment_score"], comment,
            ),
        )
        feedback_row = row_to_dict(cur.fetchone())
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    tracker = update_sentiment_tracker(claim_number)
    return {"feedback": feedback_row, "sentiment_tracker": tracker}


def get_customer_feedback(claim_number: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM customer_feedback_per_stage WHERE claim_number = %s ORDER BY submitted_at",
            (claim_number,),
        )
        return row_to_dict(cur.fetchall()) or []
    finally:
        conn.close()


_SENTIMENT_LABEL_SCORE = {"Positive": 80, "Neutral": 50, "Negative": 20}


def update_sentiment_tracker(claim_number: str, policyholder_name: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM customer_feedback_per_stage WHERE claim_number = %s ORDER BY submitted_at",
            (claim_number,),
        )
        rows = row_to_dict(cur.fetchall()) or []

        if not rows:
            return {"error": f"No feedback found for claim {claim_number}"}

        # Use persisted sentiment_score where available, fall back to label map
        scores = [
            float(r["sentiment_score"]) if r.get("sentiment_score") is not None
            else _SENTIMENT_LABEL_SCORE.get(r.get("sentiment"), 50)
            for r in rows
        ]
        avg_score = sum(scores) / len(scores)

        if len(scores) >= 2:
            trend = "Improving" if scores[-1] > scores[-2] else (
                "Declining" if scores[-1] < scores[-2] else "Stable"
            )
        else:
            trend = "Stable"

        if avg_score < 40:
            escalation_risk = "High"
        elif avg_score < 70:
            escalation_risk = "Medium"
        else:
            escalation_risk = "Low"

        current_sentiment = rows[-1].get("sentiment")
        last_interaction_date = rows[-1].get("submitted_at")

        claim_id_int = None
        cur.execute("SELECT id FROM claims WHERE claim_number = %s", (claim_number,))
        claim_row = cur.fetchone()
        if claim_row:
            claim_id_int = claim_row["id"]

        if not policyholder_name:
            cur.execute("SELECT policyholder_name FROM claims WHERE claim_number = %s", (claim_number,))
            ph_row = cur.fetchone()
            policyholder_name = ph_row["policyholder_name"] if ph_row else None

        tracker_id = f"SENT-{claim_number}"

        cur.execute("SELECT id FROM claim_sentiment_tracker WHERE tracker_id = %s", (tracker_id,))
        existing = cur.fetchone()

        if existing:
            cur.execute(
                """
                UPDATE claim_sentiment_tracker SET
                    current_sentiment = %s, sentiment_score = %s, sentiment_trend = %s,
                    last_interaction_date = %s, escalation_risk = %s,
                    policyholder_name = %s, updated_at = NOW()
                WHERE tracker_id = %s
                """,
                (
                    current_sentiment, avg_score, trend, last_interaction_date,
                    escalation_risk, policyholder_name, tracker_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO claim_sentiment_tracker (
                    tracker_id, claim_row_id, claim_number, policyholder_name,
                    current_sentiment, sentiment_score, sentiment_trend,
                    last_interaction_date, escalation_risk, created_at, updated_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                """,
                (
                    tracker_id, claim_id_int, claim_number, policyholder_name,
                    current_sentiment, avg_score, trend, last_interaction_date, escalation_risk,
                ),
            )

        conn.commit()
        cur.execute("SELECT * FROM claim_sentiment_tracker WHERE tracker_id = %s", (tracker_id,))
        return row_to_dict(cur.fetchone())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_sentiment_tracker(claim_number: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM claim_sentiment_tracker WHERE claim_number = %s",
            (claim_number,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()
