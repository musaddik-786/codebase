"""
handler.py — Communication
───────────────────────────
Auto-drafts status-change notifications for policyholders using claim
status, sentiment data, and communication history. Writes drafted
messages to communication_history.
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
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-claims")


def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


def log_inbound_communication(claim_number: str, message_text: str, sentiment: str = "Neutral") -> dict:
    """Log the policyholder's inbound message to communication_history."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, policyholder_name FROM claims WHERE claim_number = %s", (claim_number,))
        claim_row = cur.fetchone()
        claim_id = claim_row["id"] if claim_row else None
        policyholder_name = claim_row["policyholder_name"] if claim_row else "Valued Policyholder"

        comm_id = f"COMM-IN-{claim_number}-{int(datetime.utcnow().timestamp())}"
        cur.execute(
            """
            INSERT INTO communication_history (
                communication_id, claim_row_id, claim_number, policyholder_name,
                communication_type, direction, subject, summary,
                sentiment_detected, handled_by, resolution_status, follow_up_required
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                comm_id, claim_id, claim_number, policyholder_name,
                "Portal", "Inbound",
                "Policyholder Message",
                message_text[:500],
                sentiment,
                "CommunicationAgent",
                "Logged",
                False,
            ),
        )
        result = row_to_dict(cur.fetchone())
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_communication_history(claim_number: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM communication_history WHERE claim_number = %s ORDER BY communication_date DESC",
            (claim_number,),
        )
        return row_to_dict(cur.fetchall()) or []
    finally:
        conn.close()


def draft_status_notification(claim_number: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_number,))
        claim = row_to_dict(cur.fetchone())
        if not claim:
            return {"error": f"Claim {claim_number} not found"}

        cur.execute(
            "SELECT * FROM communication_history WHERE claim_number = %s ORDER BY communication_date DESC LIMIT 5",
            (claim_number,),
        )
        history = row_to_dict(cur.fetchall()) or []

        sentiment_data = None
        try:
            cur.execute(
                "SELECT * FROM claim_sentiment_tracker WHERE claim_number = %s ORDER BY updated_at DESC LIMIT 1",
                (claim_number,),
            )
            sentiment_data = row_to_dict(cur.fetchone())
        except Exception:
            pass

        cur.execute(
            "SELECT * FROM claim_journey_master WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        journey = row_to_dict(cur.fetchone()) or {}

    finally:
        conn.close()

    sentiment_label = (sentiment_data or {}).get("current_sentiment", "Neutral")
    escalation_risk = (sentiment_data or {}).get("escalation_risk", "Low")
    claim_status = claim.get("status", "In Progress")
    current_stage_name = journey.get("current_stage_name", claim_status)
    claimant_name = claim.get("policyholder_name") or "Valued Policyholder"
    recent_summaries = [h.get("summary") for h in history[:3] if h.get("summary")]

    try:
        client = _get_openai_client()
        prompt = (
            "You are an insurance claims communication specialist. "
            "Draft a professional, empathetic status-update notification for the policyholder. "
            "Respond with JSON: "
            '{"subject": "...", "message_body": "...", "channel": "Email|SMS|Portal", '
            '"tone": "Empathetic|Informational|Urgent", "next_action": "..."}.\n\n'
            f"Claimant: {claimant_name}\n"
            f"Claim Number: {claim_number}\n"
            f"Current Status: {claim_status}\n"
            f"Current Stage: {current_stage_name}\n"
            f"Loss Type: {claim.get('loss_type', 'Unknown')}\n"
            f"Policyholder Sentiment: {sentiment_label}\n"
            f"Escalation Risk: {escalation_risk}\n"
            f"Recent Communication Summaries: {recent_summaries}"
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        draft = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.warning("LLM notification draft failed: %s", e)
        draft = {
            "subject": f"Update on Your Claim {claim_number}",
            "message_body": (
                f"Dear {claimant_name}, your claim {claim_number} is currently "
                f"at the '{current_stage_name}' stage. We will keep you updated."
            ),
            "channel": "Email",
            "tone": "Informational",
            "next_action": "No further action required at this time",
        }

    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        cur2.execute(
            """
            INSERT INTO communication_history (
                communication_id, claim_row_id, claim_number, policyholder_name,
                communication_type, direction, subject, summary,
                sentiment_detected, handled_by, resolution_status, follow_up_required
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                f"COMM-{claim_number}-{int(datetime.utcnow().timestamp())}",
                claim.get("id"),
                claim_number,
                claimant_name,
                draft.get("channel", "Email"),
                "Outbound",
                draft.get("subject"),
                draft.get("message_body"),
                sentiment_label,
                "CommunicationAgent",
                "Draft",
                False,
            ),
        )
        conn2.commit()
    except Exception as e:
        conn2.rollback()
        log.warning("Could not write communication_history: %s", e)
    finally:
        conn2.close()

    return {
        "claim_number": claim_number,
        "claim_status": claim_status,
        "current_stage": current_stage_name,
        "policyholder_sentiment": sentiment_label,
        "escalation_risk": escalation_risk,
        "drafted_notification": draft,
    }
