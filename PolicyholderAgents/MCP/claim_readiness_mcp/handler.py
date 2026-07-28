"""
handler.py — Claim Readiness
─────────────────────────────
Validates that all mandatory FNOL fields AND required documents are present
for a claim, runs an initial fraud pre-screen, and writes the result to
intake_validation_result_output.
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

_REQUIRED_FNOL_FIELDS = [
    "policy_number", "date_of_loss", "loss_type", "cause_of_loss",
    "short_description", "claimant_name", "contact_phone",
]

# Mandatory field_name values whose data lives under a differently-named
# column in the source table (policy_details.policy_address stores the
# fnol_mandatory_fields "policyholder_address" entry).
_MANDATORY_FIELD_ALIASES = {
    "policyholder_address": "policy_address",
}


def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


def acknowledge_missing_docs(claim_number: str, notes: str = None) -> dict:
    """
    Record that the policyholder acknowledged they have no documents to upload
    right now. Sets docs_status = 'Acknowledged - Not Available' so downstream
    agents (adjuster workflow) know to request evidence before processing.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO intake_validation_result_output
              (claim_number, docs_status, missing_docs, validated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (claim_number) DO UPDATE SET
              docs_status  = 'Acknowledged - Not Available',
              missing_docs = COALESCE(
                  intake_validation_result_output.missing_docs,
                  EXCLUDED.missing_docs
              ),
              validated_at = EXCLUDED.validated_at
            """,
            (
                claim_number,
                "Acknowledged - Not Available",
                json.dumps(["No documents submitted — policyholder acknowledged"
                            + (f": {notes}" if notes else "")]),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        log.info("acknowledge_missing_docs: claim_number=%s noted", claim_number)
        return {
            "claim_number": claim_number,
            "docs_status": "Acknowledged - Not Available",
            "message": (
                "Recorded. Your FNOL and Claim ID are saved. "
                "The adjuster may request documents before the claim can be processed further."
            ),
        }
    except Exception as e:
        conn.rollback()
        log.error("acknowledge_missing_docs error: %s", e)
        return {"error": str(e)}
    finally:
        conn.close()


def get_intake_validation_result(claim_number: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM intake_validation_result_output WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def score_claim_readiness(claim_number: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # ── Fetch claim ───────────────────────────────────────────────────────
        cur.execute(
            "SELECT * FROM claims WHERE claim_number = %s OR id::text = %s LIMIT 1",
            (claim_number, claim_number),
        )
        claim = row_to_dict(cur.fetchone())
        if not claim:
            return {"error": f"claim_number {claim_number} not found"}

        # ── Fetch latest FNOL submission ──────────────────────────────────────
        cur.execute(
            "SELECT * FROM fnol_submissions WHERE policy_number = %s ORDER BY submitted_at DESC LIMIT 1",
            (claim.get("policy_number"),),
        )
        fnol = row_to_dict(cur.fetchone()) or {}

        # ── Fetch policy details ────────────────────────────────────────────────
        # Some mandatory fields (e.g. policyholder_address) are sourced from the
        # policy record rather than the claim/FNOL data — without this, those
        # fields can never resolve and are permanently reported as missing.
        cur.execute(
            "SELECT * FROM policy_details WHERE policy_number = %s LIMIT 1",
            (claim.get("policy_number"),),
        )
        policy = row_to_dict(cur.fetchone()) or {}

        # ── Fetch mandatory fields from DB (fix: fetchall returns a list) ────
        try:
            cur.execute("SELECT * FROM fnol_mandatory_fields ORDER BY display_order")
            rows = cur.fetchall()
            mandatory_fields = [row_to_dict(r)["field_name"] for r in rows if row_to_dict(r).get("field_name")]
        except Exception:
            conn.rollback()
            mandatory_fields = _REQUIRED_FNOL_FIELDS

        # ── Fetch uploaded documents for this claim ───────────────────────────
        cur.execute(
            "SELECT document_type, file_name, status FROM documents WHERE claim_number = %s",
            (claim_number,),
        )
        doc_rows = [row_to_dict(r) for r in cur.fetchall()]

    finally:
        conn.close()

    # ── Field completeness ────────────────────────────────────────────────────
    merged = {**claim, **fnol, **policy}
    missing_fields = [
        f for f in mandatory_fields
        if not merged.get(_MANDATORY_FIELD_ALIASES.get(f, f))
    ]
    present_count = len(mandatory_fields) - len(missing_fields)
    completeness_score = round((present_count / len(mandatory_fields)) * 100) if mandatory_fields else 0

    # ── Document completeness ─────────────────────────────────────────────────
    # Count any document that isn't in a terminal failure state — Uploaded,
    # Processing, and Validated all mean the file is present.
    validated_docs = [d for d in doc_rows if (d or {}).get("status") not in (None, "Failed")]
    has_image    = any(d["document_type"] == "Image"    for d in validated_docs)
    has_document = any(d["document_type"] == "Document" for d in validated_docs)

    missing_docs = []
    if not validated_docs:
        missing_docs.append("No documents uploaded")
    elif not has_image:
        missing_docs.append("At least one photo/image of damage required")
    # NOTE: supporting-document (PDF/DOCX) requirement temporarily disabled — image only for now.

    docs_status = "Complete" if not missing_docs else "Incomplete"

    # ── Coverage status (quick indicator only — full check is PolicyCoverageAgent) ──
    coverage_status = "Unknown"
    if claim.get("policy_number") and claim.get("loss_type"):
        coverage_status = "Needs Verification"
    if completeness_score >= 80:
        coverage_status = "Sufficient for Processing"

    # ── LLM fraud pre-screen ──────────────────────────────────────────────────
    try:
        client = _get_openai_client()
        prompt = (
            "You are an insurance fraud pre-screener. Based on the FNOL data below, "
            "respond with JSON: "
            '{"fraud_risk": "Low|Medium|High", "fraud_risk_score": 0-100, '
            '"fraud_flags": ["..."], "recommendation": "..."}.\n\n'
            f"FNOL/Claim data:\n{json.dumps(merged, default=str)}\n\n"
            f"Missing mandatory fields: {missing_fields}\n"
            f"Completeness score: {completeness_score}%\n"
            f"Documents uploaded: {len(doc_rows)}, validated: {len(validated_docs)}"
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        llm_result = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.warning("LLM fraud pre-screen failed: %s", e)
        llm_result = {
            "fraud_risk": "Unknown",
            "fraud_risk_score": 0,
            "fraud_flags": [],
            "recommendation": "Manual review required",
        }

    # ── Overall verdict ───────────────────────────────────────────────────────
    fraud_risk = llm_result.get("fraud_risk", "Unknown")
    if completeness_score < 80 or docs_status == "Incomplete":
        overall_result = "Incomplete"
    elif fraud_risk in ("Medium", "High"):
        overall_result = "Flagged for Review"
    else:
        overall_result = "Ready"

    # ── Persist ───────────────────────────────────────────────────────────────
    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        cur2.execute(
            """
            INSERT INTO intake_validation_result_output
              (claim_number, completeness_score, missing_fields, coverage_status,
               docs_status, missing_docs,
               fraud_risk, fraud_risk_score, fraud_flags, recommendation,
               overall_result, validated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (claim_number) DO UPDATE SET
              completeness_score = EXCLUDED.completeness_score,
              missing_fields     = EXCLUDED.missing_fields,
              coverage_status    = EXCLUDED.coverage_status,
              docs_status        = EXCLUDED.docs_status,
              missing_docs       = EXCLUDED.missing_docs,
              fraud_risk         = EXCLUDED.fraud_risk,
              fraud_risk_score   = EXCLUDED.fraud_risk_score,
              fraud_flags        = EXCLUDED.fraud_flags,
              recommendation     = EXCLUDED.recommendation,
              overall_result     = EXCLUDED.overall_result,
              validated_at       = EXCLUDED.validated_at
            """,
            (
                claim_number,
                completeness_score,
                json.dumps(missing_fields),
                coverage_status,
                docs_status,
                json.dumps(missing_docs),
                fraud_risk,
                llm_result.get("fraud_risk_score"),
                json.dumps(llm_result.get("fraud_flags", [])),
                llm_result.get("recommendation"),
                overall_result,
                datetime.utcnow().isoformat(),
            ),
        )
        conn2.commit()
    except Exception as e:
        conn2.rollback()
        log.warning("Could not write intake_validation_result_output: %s", e)
    finally:
        conn2.close()

    return {
        "claim_number": claim_number,
        "completeness_score": completeness_score,
        "missing_fields": missing_fields,
        "docs_status": docs_status,
        "missing_docs": missing_docs,
        "coverage_status": coverage_status,
        "fraud_risk": fraud_risk,
        "fraud_risk_score": llm_result.get("fraud_risk_score"),
        "fraud_flags": llm_result.get("fraud_flags", []),
        "recommendation": llm_result.get("recommendation"),
        "overall_result": overall_result,
    }
