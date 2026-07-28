"""
handler.py — Case Assignment
──────────────────────────────
Assigns an SIU investigator to a case using skill-based and workload-balanced
matching, then writes the assignment to siu_case_master.
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

_INVESTIGATOR_POOL = [
    {"name": "Agent Rivera",   "specialties": ["Medical", "Bodily Injury"], "active_cases": 3},
    {"name": "Agent Chen",     "specialties": ["Auto", "Property"],          "active_cases": 5},
    {"name": "Agent Williams", "specialties": ["Workers Comp", "Liability"], "active_cases": 2},
    {"name": "Agent Patel",    "specialties": ["Vendor Fraud", "Identity"],  "active_cases": 4},
    {"name": "Agent Okafor",   "specialties": ["General"],                   "active_cases": 1},
]


def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


def get_siu_case_master(claim_id: str) -> dict:
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


def assign_investigator(claim_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
        claim = row_to_dict(cur.fetchone())
        if not claim:
            return {"error": f"claim_id {claim_id} not found"}

        cur.execute(
            "SELECT * FROM siu_case_master WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        existing_case = row_to_dict(cur.fetchone())

    finally:
        conn.close()

    loss_type = claim.get("loss_type", "General")
    fraud_score = float(claim.get("fraud_score") or 0)
    severity = claim.get("severity", "Medium")

    lowest_workload = min(_INVESTIGATOR_POOL, key=lambda x: x["active_cases"])
    specialist = None
    for inv in sorted(_INVESTIGATOR_POOL, key=lambda x: x["active_cases"]):
        if any(loss_type in spec for spec in inv["specialties"]) or any("General" in spec for spec in inv["specialties"]):
            specialist = inv
            break
    candidate = specialist or lowest_workload

    try:
        client = _get_openai_client()
        prompt = (
            "You are an SIU case assignment coordinator. Select the best investigator "
            "from the pool below and respond with JSON: "
            '{"assigned_investigator": "...", "assignment_type": "Standard|Specialist|Senior", '
            '"rationale": "..."}.\n\n'
            f"Claim loss_type: {loss_type}\n"
            f"Fraud score: {fraud_score}\n"
            f"Severity: {severity}\n"
            f"Investigator pool (name | specialties | active_cases):\n"
            + "\n".join(
                f"  {inv['name']} | {inv['specialties']} | {inv['active_cases']} cases"
                for inv in _INVESTIGATOR_POOL
            )
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        llm_result = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.warning("LLM assignment failed: %s", e)
        llm_result = {
            "assigned_investigator": candidate["name"],
            "assignment_type": "Standard",
            "rationale": f"Fallback: lowest workload investigator for {loss_type}",
        }

    assigned_to = llm_result.get("assigned_investigator", candidate["name"])
    now = datetime.utcnow().isoformat()

    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        if existing_case:
            cur2.execute(
                "UPDATE siu_case_master SET assigned_investigator = %s, assignment_type = %s, "
                "assignment_rationale = %s, assigned_at = %s WHERE claim_id = %s",
                (
                    assigned_to,
                    llm_result.get("assignment_type"),
                    llm_result.get("rationale"),
                    now,
                    claim_id,
                ),
            )
        else:
            cur2.execute(
                """
                INSERT INTO siu_case_master
                  (claim_id, assigned_investigator, assignment_type,
                   assignment_rationale, assigned_at, case_status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    claim_id,
                    assigned_to,
                    llm_result.get("assignment_type"),
                    llm_result.get("rationale"),
                    now,
                    "Open",
                ),
            )
        conn2.commit()
    except Exception as e:
        conn2.rollback()
        log.warning("Could not update siu_case_master: %s", e)
    finally:
        conn2.close()

    return {
        "claim_id": claim_id,
        "assigned_investigator": assigned_to,
        "assignment_type": llm_result.get("assignment_type"),
        "rationale": llm_result.get("rationale"),
        "loss_type": loss_type,
        "fraud_score": fraud_score,
    }
