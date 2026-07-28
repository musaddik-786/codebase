"""
handler.py — SIU Closure
──────────────────────────
Validates closure readiness against a checklist of required investigation
steps before allowing final case closure. Writes the checklist result to
siu_progress_tracker.
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

_CLOSURE_CHECKLIST = [
    "evidence_correlation_complete",
    "network_analysis_complete",
    "behavioral_analysis_complete",
    "final_decision_recorded",
    "investigator_report_submitted",
]


def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


def get_siu_progress_tracker(siu_case_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM siu_progress_tracker WHERE siu_case_id = %s ORDER BY id DESC LIMIT 1",
            (siu_case_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def check_closure_readiness(siu_case_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM siu_case_master WHERE siu_case_id = %s ORDER BY id DESC LIMIT 1",
            (siu_case_id,),
        )
        case = row_to_dict(cur.fetchone())

        if not case:
            cur.execute(
                "SELECT * FROM siu_case_master WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
                (siu_case_id,),
            )
            case = row_to_dict(cur.fetchone())

        if not case:
            return {"error": f"SIU case {siu_case_id} not found"}

        claim_id = case.get("claim_id", "")

        evidence_corr = None
        try:
            cur.execute(
                "SELECT * FROM siu_evidence_correlation_results WHERE claim_id = %s ORDER BY correlated_at DESC LIMIT 1",
                (claim_id,),
            )
            evidence_corr = row_to_dict(cur.fetchone())
        except Exception:
            pass

        network_analysis = None
        try:
            cur.execute(
                "SELECT * FROM siu_network_analysis_results WHERE claim_id = %s ORDER BY analyzed_at DESC LIMIT 1",
                (claim_id,),
            )
            network_analysis = row_to_dict(cur.fetchone())
        except Exception:
            pass

        behavioral_analysis = None
        try:
            cur.execute(
                "SELECT * FROM siu_behavioral_analysis WHERE siu_case_id = %s ORDER BY analyzed_at DESC LIMIT 1",
                (siu_case_id,),
            )
            behavioral_analysis = row_to_dict(cur.fetchone())
        except Exception:
            pass

        decision = case.get("final_decision") or case.get("investigation_outcome")
        investigator_report = case.get("report_submitted_at") or case.get("report_url")

    finally:
        conn.close()

    checklist_status = {
        "evidence_correlation_complete": evidence_corr is not None,
        "network_analysis_complete": network_analysis is not None,
        "behavioral_analysis_complete": behavioral_analysis is not None,
        "final_decision_recorded": bool(decision),
        "investigator_report_submitted": bool(investigator_report),
    }

    incomplete_steps = [k for k, v in checklist_status.items() if not v]
    completed_count = len([v for v in checklist_status.values() if v])
    readiness_pct = round((completed_count / len(_CLOSURE_CHECKLIST)) * 100)
    is_ready = len(incomplete_steps) == 0

    try:
        client = _get_openai_client()
        prompt = (
            "You are an SIU case closure coordinator. Review the checklist below and "
            "provide a closure recommendation. Respond with JSON: "
            '{"closure_verdict": "Ready to Close|Pending Steps|Blocked", '
            '"closure_notes": "...", "next_steps": ["..."]}.\n\n'
            f"SIU Case: {siu_case_id}\n"
            f"Claim: {claim_id}\n"
            f"Checklist: {json.dumps(checklist_status)}\n"
            f"Incomplete steps: {incomplete_steps}\n"
            f"Readiness: {readiness_pct}%"
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        llm_result = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.warning("LLM closure check failed: %s", e)
        llm_result = {
            "closure_verdict": "Ready to Close" if is_ready else "Pending Steps",
            "closure_notes": f"{readiness_pct}% complete",
            "next_steps": incomplete_steps,
        }

    now = datetime.utcnow().isoformat()
    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        cur2.execute(
            """
            INSERT INTO siu_progress_tracker
              (siu_case_id, checklist_status, readiness_pct, incomplete_steps,
               closure_verdict, closure_notes, checked_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (siu_case_id) DO UPDATE SET
              checklist_status = EXCLUDED.checklist_status,
              readiness_pct = EXCLUDED.readiness_pct,
              incomplete_steps = EXCLUDED.incomplete_steps,
              closure_verdict = EXCLUDED.closure_verdict,
              closure_notes = EXCLUDED.closure_notes,
              checked_at = EXCLUDED.checked_at
            """,
            (
                siu_case_id,
                json.dumps(checklist_status),
                readiness_pct,
                json.dumps(incomplete_steps),
                llm_result.get("closure_verdict"),
                llm_result.get("closure_notes"),
                now,
            ),
        )
        conn2.commit()
    except Exception as e:
        conn2.rollback()
        log.warning("Could not write siu_progress_tracker: %s", e)
    finally:
        conn2.close()

    return {
        "siu_case_id": siu_case_id,
        "claim_id": claim_id,
        "checklist_status": checklist_status,
        "readiness_pct": readiness_pct,
        "incomplete_steps": incomplete_steps,
        **llm_result,
    }
