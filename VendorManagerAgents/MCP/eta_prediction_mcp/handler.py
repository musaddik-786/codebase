"""
handler.py — ETA Prediction
────────────────────────────
Predicts vendor work ETA for a claim using benchmark/turnaround data and an
LLM-adjusted heuristic, with a deterministic fallback.
"""

import json
import logging
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)


def _get_llm():
    from langchain_openai.chat_models import AzureChatOpenAI
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def get_eta_prediction(claim_id: str, vendor_id: Optional[str] = None) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query = "SELECT * FROM eta_predictions WHERE claim_id = %s"
        params = [claim_id]
        if vendor_id:
            query += " AND vendor_id = %s"
            params.append(vendor_id)
        query += " ORDER BY id DESC"
        cur.execute(query, params)
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


def _get_baseline_eta(vendor_id: str) -> float:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT eta_days FROM vendor_benchmarks WHERE vendor_id = %s", (vendor_id,))
        row = cur.fetchone()
        if row and row["eta_days"] is not None:
            return float(row["eta_days"])

        cur.execute(
            "SELECT v.avg_turnaround_days FROM vendor_master_input m JOIN vendors v ON v.name = m.name WHERE m.vendor_id = %s",
            (vendor_id,),
        )
        row = cur.fetchone()
        if row and row["avg_turnaround_days"] is not None:
            return float(row["avg_turnaround_days"])
        return 5.0
    finally:
        conn.close()


def predict_eta(claim_id: str, vendor_id: str) -> dict:
    claim = _get_claim(claim_id)
    loss_type = claim.get("loss_type") if claim else None
    complexity = claim.get("complexity") if claim else None
    baseline_eta = _get_baseline_eta(vendor_id)

    predicted_eta_days = None
    confidence = None
    factors = None

    try:
        llm = _get_llm()
        prompt = f"""
You are an ETA prediction assistant for vendor work on an insurance claim.

Baseline ETA (days) from vendor benchmarks/history: {baseline_eta}
Claim loss_type: {loss_type}
Claim complexity: {complexity}

Adjust the baseline ETA based on the claim's loss type and complexity.
Respond with ONLY a JSON object:
{{"predicted_eta_days": <number>, "confidence": <number between 0 and 1>, "factors": "<short explanation>"}}
"""
        response = llm.invoke(prompt)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:]
        parsed = json.loads(content)
        predicted_eta_days = float(parsed["predicted_eta_days"])
        confidence = float(parsed["confidence"])
        factors = parsed.get("factors", "")
    except Exception as e:
        log.warning("LLM ETA prediction failed (%s), using heuristic fallback", e)
        multiplier = 1.2 if loss_type in ("Structural", "Fire") else 1.0
        predicted_eta_days = baseline_eta * multiplier
        confidence = 0.6
        factors = "heuristic fallback"

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO eta_predictions (claim_id, vendor_id, predicted_eta_days, confidence, factors)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (claim_id, vendor_id, predicted_eta_days, confidence, factors),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "claim_id": claim_id,
        "vendor_id": vendor_id,
        "baseline_eta_days": baseline_eta,
        "predicted_eta_days": round(predicted_eta_days, 2),
        "confidence": round(confidence, 2),
        "factors": factors,
    }
