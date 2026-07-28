"""
handler.py — Triage
────────────────────
Prioritizes claims by urgency/severity/SLA risk, computing a composite
priority score from severity, complexity, fraud_risk_score, and claim age,
then uses an LLM to recommend a routing decision.
"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

log = logging.getLogger(__name__)

_SEVERITY_SCORE = {"Critical": 40, "High": 30, "Medium": 20, "Low": 10}
_COMPLEXITY_SCORE = {"Complex": 20, "Moderate": 10, "Simple": 5}


def _get_llm():
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def get_claim_triage(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM claim_triage WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def _extract_json(content: str) -> str:
    """Safely extract the first JSON object from an LLM response."""
    match = re.search(r'\{.*\}', content, re.DOTALL)
    return match.group(0) if match else content


def _get_claim(claim_id: str) -> Optional[dict]:
    # Normalize to avoid whitespace/case mismatches
    claim_id = claim_id.strip().upper()
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


def _get_fraud_risk(claim_id: str) -> Optional[dict]:
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


def _write_triage(claim_id: str, damage_severity: str, complexity: str,
                  fraud_risk_score: int, routing: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO claim_triage (claim_id, damage_severity, complexity, fraud_risk_score, routing)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (claim_id, damage_severity, complexity, fraud_risk_score, routing),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return {
            "id": new_id,
            "claim_id": claim_id,
            "damage_severity": damage_severity,
            "complexity": complexity,
            "fraud_risk_score": fraud_risk_score,
            "routing": routing,
        }
    finally:
        conn.close()


def run_triage(claim_id: str) -> dict:
    """
    Computes a composite priority score for a claim and determines its
    SLA risk level and routing recommendation. Writes the result to
    claim_triage.
    """
    claim_id = claim_id.strip().upper()
    claim = _get_claim(claim_id)
    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    fraud_snapshot = _get_fraud_risk(claim_id)
    # Distinguish missing fraud data from a clean claim (score=0)
    fraud_data_missing = fraud_snapshot is None
    fraud_risk_score = int(fraud_snapshot.get("fraud_score") or 0) if fraud_snapshot else 0

    severity = claim.get("severity") or "Medium"
    complexity = claim.get("complexity") or "Moderate"

    severity_pts = _SEVERITY_SCORE.get(severity, 20)
    complexity_pts = _COMPLEXITY_SCORE.get(complexity, 10)
    fraud_pts = min(fraud_risk_score // 2, 30)

    filed_at = claim.get("filed_at") or datetime.utcnow().isoformat()
    try:
        delta_days = (datetime.utcnow() - datetime.fromisoformat(filed_at[:19])).days
    except Exception:
        delta_days = 0
    age_pts = min(delta_days * 2, 10)

    priority_score = severity_pts + complexity_pts + fraud_pts + age_pts

    log.info(
        "Triage score breakdown for %s: severity=%d complexity=%d fraud=%d age=%d total=%d",
        claim_id, severity_pts, complexity_pts, fraud_pts, age_pts, priority_score,
    )

    llm = _get_llm()
    fraud_context = "unknown (fraud screening not yet run)" if fraud_data_missing else str(fraud_risk_score)
    prompt = f"""
You are a claims triage specialist. Given the claim context below, determine:
- "sla_risk": "Low" | "Medium" | "High" | "Critical"
- "routing": a short routing recommendation (e.g. "Fast-track STP", "Assign senior adjuster", "Refer to SIU")
- "rationale": one sentence explaining the priority decision

Claim context:
  loss_type: {claim.get('loss_type')}
  severity: {severity}
  complexity: {complexity}
  fraud_risk_score: {fraud_context}
  priority_score: {priority_score}
  days_since_filed: {delta_days}

Note: if fraud_risk_score is "unknown", treat fraud risk as uncertain rather than zero.

Respond with ONLY a JSON object with keys: sla_risk, routing, rationale. No other text.
"""
    response = llm.invoke(prompt)
    content = _extract_json(response.content.strip())
    try:
        parsed = json.loads(content)
    except Exception:
        log.warning("Could not parse LLM JSON for triage of claim %s — raw: %s", claim_id, response.content.strip())
        parsed = {"sla_risk": "Medium", "routing": "Standard adjuster assignment", "rationale": ""}

    routing = parsed.get("routing", "Standard adjuster assignment")
    triage_record = _write_triage(claim_id, severity, complexity, fraud_risk_score, routing)

    return {
        "claim_id": claim_id,
        "priority_score": priority_score,
        "score_breakdown": {
            "severity_pts": severity_pts,
            "complexity_pts": complexity_pts,
            "fraud_pts": fraud_pts,
            "age_pts": age_pts,
        },
        "fraud_data_missing": fraud_data_missing,
        "sla_risk": parsed.get("sla_risk", "Medium"),
        "routing": routing,
        "rationale": parsed.get("rationale", ""),
        "triage_record": triage_record,
    }
