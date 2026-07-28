"""
handler.py — Behavioral Analytics
───────────────────────────────────
Analyzes claimant/vendor behavior patterns across the SIU activity log,
detecting frequency anomalies, timing shifts, and communication tone changes.
"""

import json
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from dotenv import load_dotenv, find_dotenv
from openai import AzureOpenAI

load_dotenv(find_dotenv())

log = logging.getLogger(__name__)

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-11-13")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5.1")


def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


def get_siu_activity_log(siu_case_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM siu_activity_log WHERE siu_case_id = %s ORDER BY activity_date ASC",
            (siu_case_id,),
        )
        return row_to_dict(cur.fetchall()) or []
    finally:
        conn.close()


def analyze_behavior(siu_case_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM siu_activity_log WHERE siu_case_id = %s ORDER BY activity_date ASC",
            (siu_case_id,),
        )
        activity_log = row_to_dict(cur.fetchall()) or []

        cur.execute(
            "SELECT * FROM siu_case_master WHERE siu_case_id = %s ORDER BY id DESC LIMIT 1",
            (siu_case_id,),
        )
        case = row_to_dict(cur.fetchone()) or {}
        claim_id = case.get("claim_id", "")

        communication_history = []
        if claim_id:
            try:
                cur.execute(
                    "SELECT * FROM communication_history WHERE claim_id = %s ORDER BY communication_date ASC",
                    (claim_id,),
                )
                communication_history = row_to_dict(cur.fetchall()) or []
            except Exception:
                pass

    finally:
        conn.close()

    if not activity_log:
        return {"siu_case_id": siu_case_id, "error": "No activity log found for this SIU case"}

    activity_types = [a.get("activity_type", "") for a in activity_log]
    actor_counts: dict = {}
    for a in activity_log:
        actor = a.get("actor") or a.get("performed_by") or "Unknown"
        actor_counts[actor] = actor_counts.get(actor, 0) + 1

    high_frequency_actors = [k for k, v in actor_counts.items() if v >= 3]

    try:
        client = _get_openai_client()
        prompt = (
            "You are an SIU behavioral analyst. Analyze the interaction patterns below "
            "for fraud indicators: unusual frequency, timing anomalies, tone shifts. "
            "Respond with JSON: "
            '{"anomaly_score": 0-100, "anomaly_flags": ["..."], '
            '"tone_shift_detected": true/false, '
            '"timing_anomaly_detected": true/false, '
            '"behavior_summary": "...", "recommendation": "..."}.\n\n'
            f"SIU Case: {siu_case_id}\n"
            f"Activity count: {len(activity_log)}\n"
            f"Activity types: {activity_types}\n"
            f"High-frequency actors: {high_frequency_actors}\n"
            f"Communication history count: {len(communication_history)}\n"
            f"Sample activities (last 5): {json.dumps(activity_log[-5:], default=str)}"
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        llm_result = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.warning("LLM behavioral analysis failed: %s", e)
        llm_result = {
            "anomaly_score": 0,
            "anomaly_flags": [],
            "tone_shift_detected": False,
            "timing_anomaly_detected": False,
            "behavior_summary": "Automated analysis failed; manual review needed",
            "recommendation": "Manual behavioral review required",
        }

    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        cur2.execute(
            """
            INSERT INTO siu_behavioral_analysis
              (siu_case_id, anomaly_score, anomaly_flags, tone_shift_detected,
               timing_anomaly_detected, behavior_summary, recommendation, analyzed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (siu_case_id) DO UPDATE SET
              anomaly_score = EXCLUDED.anomaly_score,
              anomaly_flags = EXCLUDED.anomaly_flags,
              tone_shift_detected = EXCLUDED.tone_shift_detected,
              timing_anomaly_detected = EXCLUDED.timing_anomaly_detected,
              behavior_summary = EXCLUDED.behavior_summary,
              recommendation = EXCLUDED.recommendation,
              analyzed_at = EXCLUDED.analyzed_at
            """,
            (
                siu_case_id,
                llm_result.get("anomaly_score", 0),
                json.dumps(llm_result.get("anomaly_flags", [])),
                1 if llm_result.get("tone_shift_detected") else 0,
                1 if llm_result.get("timing_anomaly_detected") else 0,
                llm_result.get("behavior_summary"),
                llm_result.get("recommendation"),
                datetime.utcnow().isoformat(),
            ),
        )
        conn2.commit()
    except Exception as e:
        conn2.rollback()
        log.warning("Could not write siu_behavioral_analysis: %s", e)
    finally:
        conn2.close()

    return {
        "siu_case_id": siu_case_id,
        "activity_count": len(activity_log),
        "high_frequency_actors": high_frequency_actors,
        **llm_result,
    }
