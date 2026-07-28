"""
handler.py — Vendor Qualification
───────────────────────────────────
Scores a vendor against compliance criteria: license validity, insurance
documentation, certifications, and background check status.  Updates
assignment_eligible in vendor_master_input.
"""

import json
import logging
import os
import sys
from datetime import datetime, date

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

_COMPLIANCE_CHECKS = [
    "license_valid",
    "insurance_verified",
    "certifications_current",
    "background_check_passed",
]


def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


def get_vendor_master(vendor_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM vendor_master_input WHERE vendor_id = %s", (vendor_id,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def score_vendor_qualification(vendor_id: str) -> dict:
    vendor = get_vendor_master(vendor_id)
    if not vendor:
        return {"error": f"vendor_id {vendor_id} not found in vendor_master_input"}

    today_str = date.today().isoformat()

    license_expiry = vendor.get("license_expiry_date") or ""
    license_valid = (
        vendor.get("license_valid", "No") == "Yes"
        and (not license_expiry or license_expiry >= today_str)
    )

    insurance_verified = vendor.get("insurance_verified", "No") == "Yes"
    certifications_current = vendor.get("certifications_current", "No") == "Yes"
    background_check = vendor.get("background_check_passed", "No") == "Yes"

    compliance_status = {
        "license_valid": license_valid,
        "insurance_verified": insurance_verified,
        "certifications_current": certifications_current,
        "background_check_passed": background_check,
    }

    passed_count = sum(1 for v in compliance_status.values() if v)
    qualification_score = round((passed_count / len(_COMPLIANCE_CHECKS)) * 100)
    failed_checks = [k for k, v in compliance_status.items() if not v]

    try:
        client = _get_openai_client()
        prompt = (
            "You are a vendor compliance officer. Based on the compliance data below, "
            "determine if the vendor should be assignment-eligible. "
            "Respond with JSON: "
            '{"assignment_eligible": "Yes|No|Conditional", '
            '"risk_level": "Low|Medium|High", '
            '"disqualification_reasons": ["..."], '
            '"recommendation": "..."}.\n\n'
            f"Vendor: {vendor.get('vendor_name', vendor_id)}\n"
            f"Qualification score: {qualification_score}/100\n"
            f"Compliance status: {json.dumps(compliance_status)}\n"
            f"Failed checks: {failed_checks}\n"
            f"License expiry: {license_expiry}\n"
            f"Vendor status: {vendor.get('status', 'Unknown')}"
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        llm_result = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.warning("LLM qualification scoring failed: %s", e)
        eligibility = "Yes" if qualification_score >= 75 else "No"
        llm_result = {
            "assignment_eligible": eligibility,
            "risk_level": "Low" if qualification_score >= 75 else "High",
            "disqualification_reasons": failed_checks,
            "recommendation": f"Score {qualification_score}/100 — {'qualified' if eligibility == 'Yes' else 'requires remediation'}",
        }

    new_eligibility = llm_result.get("assignment_eligible", "No")

    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        cur2.execute(
            "UPDATE vendor_master_input SET assignment_eligible = %s, qualification_score = %s, qualified_at = %s WHERE vendor_id = %s",
            (new_eligibility, qualification_score, datetime.utcnow().isoformat(), vendor_id),
        )
        if cur2.rowcount == 0:
            log.warning("Could not update vendor_master_input (no row matched vendor_id=%s)", vendor_id)
        conn2.commit()
    except Exception as e:
        conn2.rollback()
        log.warning("Could not update vendor qualification: %s", e)
    finally:
        conn2.close()

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("vendor_name"),
        "qualification_score": qualification_score,
        "compliance_status": compliance_status,
        "failed_checks": failed_checks,
        **llm_result,
    }
