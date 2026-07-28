"""
handler.py — Vendor Capacity Management
─────────────────────────────────────────
Evaluates a vendor's active job count against configurable thresholds and
throttles or re-enables assignment eligibility accordingly.
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

_DEFAULT_CAPACITY_THRESHOLD = 10
_THROTTLE_THRESHOLD = 8


def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


def get_vendor_active_jobs(vendor_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM vendor_jobs_input WHERE vendor_id = %s AND active = 'Yes' ORDER BY id DESC",
            (vendor_id,),
        )
        return row_to_dict(cur.fetchall()) or []
    finally:
        conn.close()


def manage_vendor_capacity(vendor_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT * FROM vendor_master_input WHERE vendor_id = %s", (vendor_id,))
        vendor = row_to_dict(cur.fetchone())
        if not vendor:
            return {"error": f"vendor_id {vendor_id} not found in vendor_master_input"}

        cur.execute(
            "SELECT * FROM vendor_jobs_input WHERE vendor_id = %s AND active = 'Yes'",
            (vendor_id,),
        )
        active_jobs = row_to_dict(cur.fetchall()) or []

        capacity_threshold = int(vendor.get("capacity_threshold") or _DEFAULT_CAPACITY_THRESHOLD)
        throttle_at = int(vendor.get("throttle_threshold") or _THROTTLE_THRESHOLD)

        completed_last_30 = 0
        try:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM vendor_jobs_input WHERE vendor_id = %s AND active = 'No' AND completed_at >= NOW() - INTERVAL '30 days'",
                (vendor_id,),
            )
            row = cur.fetchone()
            completed_last_30 = (row[0] if row else 0)
        except Exception:
            pass

    finally:
        conn.close()

    active_count = len(active_jobs)
    utilization_pct = round((active_count / capacity_threshold) * 100) if capacity_threshold else 0

    if active_count >= capacity_threshold:
        capacity_status = "At Capacity"
        new_eligibility = "No"
    elif active_count >= throttle_at:
        capacity_status = "Near Capacity"
        new_eligibility = "Conditional"
    else:
        capacity_status = "Available"
        new_eligibility = "Yes"

    try:
        client = _get_openai_client()
        prompt = (
            "You are a vendor capacity analyst. Based on the workload data below, "
            "recommend whether this vendor can accept new assignments. "
            "Respond with JSON: "
            '{"assignment_eligible": "Yes|No|Conditional", '
            '"capacity_recommendation": "...", '
            '"estimated_availability_days": <number or null>}.\n\n'
            f"Vendor: {vendor.get('vendor_name', vendor_id)}\n"
            f"Active jobs: {active_count} / {capacity_threshold} (threshold)\n"
            f"Utilization: {utilization_pct}%\n"
            f"Capacity status: {capacity_status}\n"
            f"Jobs completed in last 30 days: {completed_last_30}\n"
            f"Job types active: {list({j.get('job_type', 'Unknown') for j in active_jobs[:10]})}"
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        llm_result = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.warning("LLM capacity analysis failed: %s", e)
        llm_result = {
            "assignment_eligible": new_eligibility,
            "capacity_recommendation": f"{capacity_status}: {active_count}/{capacity_threshold} jobs active ({utilization_pct}% utilization)",
            "estimated_availability_days": None,
        }

    final_eligibility = llm_result.get("assignment_eligible", new_eligibility)

    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        cur2.execute(
            "UPDATE vendor_master_input SET assignment_eligible = %s, capacity_status = %s, capacity_checked_at = %s WHERE vendor_id = %s",
            (final_eligibility, capacity_status, datetime.utcnow().isoformat(), vendor_id),
        )
        conn2.commit()
    except Exception as e:
        conn2.rollback()
        log.warning("Could not update vendor capacity status: %s", e)
    finally:
        conn2.close()

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("vendor_name"),
        "active_job_count": active_count,
        "capacity_threshold": capacity_threshold,
        "utilization_pct": utilization_pct,
        "capacity_status": capacity_status,
        "completed_last_30_days": completed_last_30,
        **llm_result,
    }
