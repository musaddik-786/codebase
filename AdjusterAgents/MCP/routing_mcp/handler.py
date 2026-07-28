"""
handler.py — Routing
─────────────────────
Assigns claims to the best adjuster/team using load-balancing and
skill-matching. Writes the result to auto_assignment_log and updates
assigned_adjuster on the claim.
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

log = logging.getLogger(__name__)

_ADJUSTER_POOL = [
    {"name": "Sarah Johnson", "specialties": ["Fire", "Water", "Wind"], "active_claims": 4},
    {"name": "Mike Thompson", "specialties": ["Auto", "Theft", "Vandalism"], "active_claims": 6},
    {"name": "Lisa Chen", "specialties": ["Liability", "Medical", "Flood"], "active_claims": 3},
    {"name": "David Park", "specialties": ["Commercial", "Business Interruption"], "active_claims": 7},
    {"name": "Emma Williams", "specialties": ["Residential", "Fire", "Theft"], "active_claims": 5},
]


def _get_llm():
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def get_auto_assignment_log(claim_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM auto_assignment_log WHERE claim_id = %s ORDER BY id DESC",
            (claim_id,),
        )
        return row_to_dict(cur.fetchall())
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


def _get_triage(claim_id: str) -> Optional[dict]:
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


def _write_assignment(claim_id: str, assigned_to: str, assignment_type: str, reason: str) -> dict:
    assignment_id = f"ASN-{claim_id}-{uuid.uuid4().hex[:8]}"
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO auto_assignment_log (assignment_id, claim_id, assigned_to, assignment_type, reason)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (assignment_id, claim_id, assigned_to, assignment_type, reason),
        )
        conn.commit()
        cur.execute(
            "UPDATE claims SET assigned_adjuster = %s WHERE claim_number = %s",
            (assigned_to, claim_id),
        )
        conn.commit()
        return {
            "assignment_id": assignment_id,
            "claim_id": claim_id,
            "assigned_to": assigned_to,
            "assignment_type": assignment_type,
            "reason": reason,
            "created_at": datetime.utcnow().isoformat(),
        }
    finally:
        conn.close()


def assign_claim(claim_id: str) -> dict:
    """
    Determines the best adjuster for a claim using skill-matching and
    workload-balancing. Handles SIU escalations, senior adjuster assignments
    for complex/critical claims, and LLM-based specialist matching otherwise.
    """
    claim = _get_claim(claim_id)
    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    triage = _get_triage(claim_id)
    routing_hint = triage.get("routing", "") if triage else ""
    severity = claim.get("severity") or "Medium"
    complexity = claim.get("complexity") or "Moderate"
    loss_type = claim.get("loss_type") or ""

    if "SIU" in routing_hint or "fraud" in routing_hint.lower():
        return _write_assignment(claim_id, "SIU Team", "SIU",
                                 f"High fraud risk — routing to SIU. Hint: {routing_hint}")

    if severity == "Critical" or complexity == "Complex":
        specialists = [a for a in _ADJUSTER_POOL
                       if any(s.lower() in loss_type.lower() for s in a["specialties"])]
        pool = specialists or _ADJUSTER_POOL
        adjuster = min(pool, key=lambda a: a["active_claims"])
        return _write_assignment(
            claim_id, adjuster["name"], "Senior Adjuster",
            f"High severity/complexity — lowest workload senior adjuster ({adjuster['active_claims']} active claims)",
        )

    llm = _get_llm()
    prompt = f"""
You are a claims routing specialist. Select the best adjuster from the pool
for this claim, balancing specialties with current workload.

Claim context:
  loss_type: {loss_type}
  severity: {severity}
  complexity: {complexity}
  routing_hint: {routing_hint}

Adjuster pool (name, specialties, active_claims):
{json.dumps(_ADJUSTER_POOL, indent=2)}

Respond with ONLY a JSON object:
{{"adjuster_name": "...", "assignment_type": "Standard|Specialist|Senior Adjuster", "reason": "..."}}
"""
    response = llm.invoke(prompt)
    content = response.content.strip().strip("`")
    if content.startswith("json"):
        content = content[4:]
    try:
        parsed = json.loads(content)
        assigned_to = parsed.get("adjuster_name", _ADJUSTER_POOL[0]["name"])
        assignment_type = parsed.get("assignment_type", "Standard")
        reason = parsed.get("reason", "LLM-based skill and workload matching")
    except Exception:
        adjuster = min(_ADJUSTER_POOL, key=lambda a: a["active_claims"])
        assigned_to = adjuster["name"]
        assignment_type = "Standard"
        reason = "Assigned to adjuster with lowest current workload"

    return _write_assignment(claim_id, assigned_to, assignment_type, reason)
