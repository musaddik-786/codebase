"""
handler.py — Evidence Correlation
───────────────────────────────────
Cross-references investigation notes, timeline events, and evidence items
to surface inconsistencies between sources and build a correlated finding.
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


def get_investigation_notes(claim_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM investigation_notes WHERE claim_id = %s ORDER BY created_at ASC",
            (claim_id,),
        )
        return row_to_dict(cur.fetchall()) or []
    finally:
        conn.close()


def correlate_evidence(claim_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
        claim = row_to_dict(cur.fetchone())
        if not claim:
            return {"error": f"claim_id {claim_id} not found"}

        cur.execute(
            "SELECT * FROM investigation_notes WHERE claim_id = %s ORDER BY created_at ASC",
            (claim_id,),
        )
        notes = row_to_dict(cur.fetchall()) or []

        timeline_events = []
        try:
            cur.execute(
                "SELECT * FROM siu_timeline_events WHERE claim_id = %s ORDER BY event_date ASC",
                (claim_id,),
            )
            timeline_events = row_to_dict(cur.fetchall()) or []
        except Exception:
            pass

        evidence_items = []
        try:
            cur.execute(
                "SELECT * FROM evidence_items WHERE claim_id = %s ORDER BY id ASC",
                (claim_id,),
            )
            evidence_items = row_to_dict(cur.fetchall()) or []
        except Exception:
            pass

    finally:
        conn.close()

    note_texts = [n.get("note_text") or n.get("content", "") for n in notes]
    event_summaries = [e.get("event_description") or e.get("summary", "") for e in timeline_events]
    evidence_types = [e.get("evidence_type", "") for e in evidence_items]

    try:
        client = _get_openai_client()
        prompt = (
            "You are an SIU evidence analyst. Cross-reference the investigation notes, "
            "timeline events, and evidence items below for inconsistencies. "
            "Respond with JSON: "
            '{"inconsistencies": ["..."], "corroboration_score": 0-100, '
            '"key_conflicts": ["..."], "overall_finding": "Consistent|Inconsistent|Partially Consistent", '
            '"recommendation": "..."}.\n\n'
            f"Claim: {claim_id}\n"
            f"Loss type: {claim.get('loss_type')}, Date: {claim.get('date_of_loss')}\n"
            f"Investigation notes ({len(notes)}): {note_texts[:5]}\n"
            f"Timeline events ({len(timeline_events)}): {event_summaries[:5]}\n"
            f"Evidence items ({len(evidence_items)}): {evidence_types}"
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        llm_result = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.warning("LLM evidence correlation failed: %s", e)
        llm_result = {
            "inconsistencies": [],
            "corroboration_score": 50,
            "key_conflicts": [],
            "overall_finding": "Partially Consistent",
            "recommendation": "Manual cross-reference of evidence sources required",
        }

    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        cur2.execute(
            """
            INSERT INTO siu_evidence_correlation_results
              (claim_id, inconsistencies, corroboration_score, key_conflicts,
               overall_finding, recommendation, correlated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (claim_id) DO UPDATE SET
              inconsistencies = EXCLUDED.inconsistencies,
              corroboration_score = EXCLUDED.corroboration_score,
              key_conflicts = EXCLUDED.key_conflicts,
              overall_finding = EXCLUDED.overall_finding,
              recommendation = EXCLUDED.recommendation,
              correlated_at = EXCLUDED.correlated_at
            """,
            (
                claim_id,
                json.dumps(llm_result.get("inconsistencies", [])),
                llm_result.get("corroboration_score", 50),
                json.dumps(llm_result.get("key_conflicts", [])),
                llm_result.get("overall_finding"),
                llm_result.get("recommendation"),
                datetime.utcnow().isoformat(),
            ),
        )
        conn2.commit()
    except Exception as e:
        conn2.rollback()
        log.warning("Could not write siu_evidence_correlation_results: %s", e)
    finally:
        conn2.close()

    return {
        "claim_id": claim_id,
        "notes_count": len(notes),
        "timeline_events_count": len(timeline_events),
        "evidence_items_count": len(evidence_items),
        **llm_result,
    }
