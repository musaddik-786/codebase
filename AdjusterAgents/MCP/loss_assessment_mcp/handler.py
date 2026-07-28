"""
handler.py — Loss Assessment
────────────────────────────────
Orchestrates a loss assessment for a claim: sums damage_items costs,
applies a labor heuristic and severity-based depreciation, looks up the
policy deductible, and uses an LLM for subrogation likelihood and
recommendation text. Persists to loss_assessments and
loss_estimation_outputs.
"""

import json
import logging
import os
import random
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

log = logging.getLogger(__name__)

_DEPRECIATION_BY_SEVERITY = {"Low": 5, "Medium": 10, "High": 20, "Critical": 30}


def _get_llm():
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def get_loss_assessment(claim_number: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM loss_assessments WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def write_loss_assessment(claim_number: str, total_parts_cost: float, total_labor_cost: float,
                           depreciation_percent: float, deductible: float, subrogation_likelihood: str,
                           system_recommendation: str, final_recommendation: str, confidence_score: float,
                           adjuster_override: Optional[str] = None, notes: Optional[str] = None) -> dict:
    assessment_id = f"LA-{claim_number}-{random.randint(1000, 9999)}"
    assessment_date = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO loss_assessments (
                assessment_id, claim_number, total_parts_cost, total_labor_cost, depreciation_percent,
                deductible, subrogation_likelihood, system_recommendation, adjuster_override,
                final_recommendation, confidence_score, notes, assessment_date
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (assessment_id, claim_number, total_parts_cost, total_labor_cost, depreciation_percent,
             deductible, subrogation_likelihood, system_recommendation, adjuster_override,
             final_recommendation, confidence_score, notes, assessment_date),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return {
            "id": new_id, "assessment_id": assessment_id, "claim_number": claim_number,
            "total_parts_cost": total_parts_cost, "total_labor_cost": total_labor_cost,
            "depreciation_percent": depreciation_percent, "deductible": deductible,
            "subrogation_likelihood": subrogation_likelihood, "system_recommendation": system_recommendation,
            "adjuster_override": adjuster_override, "final_recommendation": final_recommendation,
            "confidence_score": confidence_score, "notes": notes, "assessment_date": assessment_date,
        }
    finally:
        conn.close()


def get_loss_estimation(claim_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM loss_estimation_outputs WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def write_loss_estimation(claim_id: str, ai_estimated_loss: float, deductible: float, net_payable: float,
                           repair_recommended: str, confidence: float) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO loss_estimation_outputs (claim_id, ai_estimated_loss, deductible, net_payable, repair_recommended, confidence)
            VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (claim_id, ai_estimated_loss, deductible, net_payable, repair_recommended, confidence),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return {
            "id": new_id, "claim_id": claim_id, "ai_estimated_loss": ai_estimated_loss,
            "deductible": deductible, "net_payable": net_payable,
            "repair_recommended": repair_recommended, "confidence": confidence,
        }
    finally:
        conn.close()


def _get_claim(claim_number: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_number,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def _get_damage_items(claim_number: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM damage_items WHERE claim_number = %s", (claim_number,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def _get_policy(policy_number: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM policy_details WHERE policy_number = %s", (policy_number,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def run_loss_assessment(claim_number: str) -> dict:
    claim = _get_claim(claim_number)
    if not claim:
        raise ValueError(f"Claim {claim_number} not found")

    damage_items = _get_damage_items(claim_number)
    total_parts_cost = sum(float(d.get("estimated_cost") or 0) for d in damage_items)
    if total_parts_cost == 0:
        total_parts_cost = float(claim.get("estimated_cost") or 0)
    total_labor_cost = round(total_parts_cost * 0.30, 2)

    policy = _get_policy(claim.get("policy_number") or "")
    deductible = float(policy.get("deductible")) if policy and policy.get("deductible") is not None else 0.0

    severity = (claim.get("severity") or "Medium").strip().title()
    depreciation_percent = _DEPRECIATION_BY_SEVERITY.get(severity, 10)

    llm = _get_llm()
    prompt = f"""
You are an insurance claims adjuster's assistant performing a loss
assessment. Given the claim context below, determine:
  - "subrogation_likelihood": "Low" | "Medium" | "High"
  - "system_recommendation": a short recommendation text (e.g. "Approve
    repair estimate and proceed to settlement")
  - "final_recommendation": a short final recommendation text
  - "confidence_score": a decimal between 0 and 1

Claim context:
  loss_type: {claim.get('loss_type')}
  short_description: {claim.get('short_description')}
  severity: {severity}
  total_parts_cost: {total_parts_cost}
  total_labor_cost: {total_labor_cost}
  depreciation_percent: {depreciation_percent}
  deductible: {deductible}

Respond with ONLY a JSON object with the four keys above.
"""
    response = llm.invoke(prompt)
    content = response.content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    try:
        parsed = json.loads(content)
    except Exception:
        log.warning("Could not parse LLM JSON, defaulting: %s", content)
        parsed = {
            "subrogation_likelihood": "Low",
            "system_recommendation": "Proceed with standard settlement based on estimated costs.",
            "final_recommendation": "Proceed with standard settlement based on estimated costs.",
            "confidence_score": 0.6,
        }

    subrogation_likelihood = parsed.get("subrogation_likelihood", "Low")
    system_recommendation = parsed.get("system_recommendation", "")
    final_recommendation = parsed.get("final_recommendation", system_recommendation)
    confidence_score = float(parsed.get("confidence_score", 0.6))

    ai_estimated_loss = total_parts_cost + total_labor_cost
    
    depreciation_amount = (
        ai_estimated_loss * depreciation_percent / 100
    )

    net_payable = max(0.0, ai_estimated_loss - depreciation_amount - deductible)
    
    repair_recommended = "Yes" if final_recommendation and "replace" not in final_recommendation.lower() else "No"

    assessment = write_loss_assessment(
        claim_number, total_parts_cost, total_labor_cost, depreciation_percent, deductible,
        subrogation_likelihood, system_recommendation, final_recommendation, confidence_score,
    )

    estimation = write_loss_estimation(
        claim_number, ai_estimated_loss, deductible, net_payable, repair_recommended, confidence_score,
    )

    return {
        "claim_number": claim_number,
        "loss_assessment": assessment,
        "loss_estimation": estimation,
    }
