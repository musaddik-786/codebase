"""
handler.py — Verification
─────────────────────────────
Comprehensive cross-check engine for the Adjuster Verification Agent.

Four verification pillars:
  1. Policy        — status, date coverage, loss-type vs coverage-type
  2. Loss Facts    — cause, date/time, occupancy, area, sudden-vs-gradual (from fnol_submissions)
  3. Documents     — completeness check against required docs for the loss type
  4. External Data — weather alignment, drone assessment, STP cross-check (reads ExternalDataAgent output)
"""

import json
import logging
import os
import random
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

log = logging.getLogger(__name__)

# Required document types by loss category — used in pillar 3
_REQUIRED_DOCS = {
    "fire":        ["fire_report", "police_report", "photos"],
    "theft":       ["police_report", "inventory_list"],
    "flood":       ["photos", "contractor_estimate"],
    "storm":       ["photos", "contractor_estimate"],
    "water damage":["photos", "plumber_report"],
    "hail":        ["photos", "contractor_estimate"],
    "wind":        ["photos", "contractor_estimate"],
    "earthquake":  ["photos", "structural_report"],
    "vandalism":   ["police_report", "photos"],
    "accident":    ["police_report", "photos"],
}
_DEFAULT_REQUIRED_DOCS = ["photos"]


def _get_llm():
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_external_verifications(claim_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM external_verifications WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def create_verification(claim_id: str, type: str, status: str = "Pending", result: Optional[str] = None) -> dict:
    verification_id = f"VER-{claim_id}-{random.randint(1000, 9999)}"
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO external_verifications (verification_id, claim_id, type, status, result) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (verification_id, claim_id, type, status, result),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return {"id": new_id, "verification_id": verification_id, "claim_id": claim_id,
                "type": type, "status": status, "result": result}
    finally:
        conn.close()


def get_verification_details(verification_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM verification_details WHERE verification_id = %s ORDER BY id", (verification_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def write_verification_detail(verification_id: str, field: str, expected: Optional[str], actual: Optional[str], flag: str, severity: str = "Advisory") -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO verification_details (verification_id, field, expected, actual, flag, severity) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (verification_id, field, expected, actual, flag, severity),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return {"id": new_id, "verification_id": verification_id, "field": field,
                "expected": expected, "actual": actual, "flag": flag, "severity": severity}
    finally:
        conn.close()


def _write_detail(verification_id: str, field: str, expected: Optional[str], actual: Optional[str], flag: str, severity: str = "Advisory") -> dict:
    """Internal shorthand — same as write_verification_detail but returns the dict directly.

    severity="Critical" marks a hard, deterministic coverage fact (policy_exists,
    policy_status, date_of_loss_in_policy_window) — any non-Match on one of these
    drives run_verification()'s coverage_verdict to "Flagged". Everything else
    stays the default "Advisory": logged and shown, but never blocks the claim.
    """
    return write_verification_detail(verification_id, field, expected, actual, flag, severity)


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


def _get_policy(policy_number: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # policy_details.policy_number is the real, consistently-populated join
        # key — policy_id is NULL on all but 4 legacy test rows (POL-1001/1002),
        # so querying policy_id here was silently reporting "no policy found" for
        # the overwhelming majority of claims that have a perfectly valid one.
        cur.execute(
            "SELECT * FROM policy_details WHERE policy_number = %s",
            (policy_number,),
        )
        row = cur.fetchone()
        if not row:
            cur.execute("SELECT * FROM policy_details WHERE policy_number ILIKE %s LIMIT 1", (policy_number,))
            row = cur.fetchone()
        return row_to_dict(row) if row else None
    finally:
        conn.close()


def _get_fnol(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM fnol_submissions WHERE policy_number = (SELECT policy_number FROM claims WHERE claim_number = %s LIMIT 1) ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        row = cur.fetchone()
        return row_to_dict(row) if row else None
    finally:
        conn.close()


def _get_documents(claim_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT document_type, status, flagged FROM documents WHERE claim_number = %s", (claim_id,))
        rows = cur.fetchall()
        return row_to_dict(rows) if rows else []
    finally:
        conn.close()


def _get_weather_alignment(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM weather_location_alignment WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        row = cur.fetchone()
        return row_to_dict(row) if row else None
    finally:
        conn.close()


def _get_drone_authenticity(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM drone_authenticity_data WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        row = cur.fetchone()
        return row_to_dict(row) if row else None
    finally:
        conn.close()


def _get_stp_result(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM stp_calculation_result WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        row = cur.fetchone()
        return row_to_dict(row) if row else None
    finally:
        conn.close()


def _get_fraud_snapshot(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM fraud_risk_snapshots WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        row = cur.fetchone()
        return row_to_dict(row) if row else None
    finally:
        conn.close()


# ── Pillar 1: Policy verification ─────────────────────────────────────────────

def _verify_policy(verification_id: str, claim: dict, policy: Optional[dict]) -> list:
    details = []

    if not policy:
        details.append(_write_detail(verification_id, "policy_exists", "Found", "Not found", "Unable to Verify", severity="Critical"))
        return details

    # 1a. Policy status
    policy_status = policy.get("status") or "Unknown"
    flag = "Match" if policy_status == "Active" else "Mismatch"
    details.append(_write_detail(verification_id, "policy_status", "Active", policy_status, flag, severity="Critical"))

    # 1b. Date of loss within policy effective/expiration window
    # policy_details.effective_date/expiration_date come back as real
    # datetime objects from Postgres (timestamp column), not strings like
    # claims.date_of_loss (TEXT) — str(...) first so slicing works either way.
    date_of_loss = (claim.get("date_of_loss") or "")[:10]
    effective = str(policy.get("effective_date") or "")[:10]
    expiration = str(policy.get("expiration_date") or "")[:10]
    if date_of_loss and effective and expiration:
        in_window = effective <= date_of_loss <= expiration
        flag = "Match" if in_window else "Mismatch"
        details.append(_write_detail(
            verification_id, "date_of_loss_in_policy_window",
            f"{effective} to {expiration}", date_of_loss, flag, severity="Critical",
        ))
    else:
        details.append(_write_detail(
            verification_id, "date_of_loss_in_policy_window",
            "Policy effective/expiry dates available", "Dates missing or incomplete", "Unable to Verify", severity="Critical",
        ))

    # 1c. Loss type vs coverage type — LLM semantic check
    loss_type = claim.get("loss_type") or ""
    coverage_type = policy.get("coverage_type") or ""
    if loss_type and coverage_type:
        llm = _get_llm()
        prompt = (
            f'A claim has loss_type "{loss_type}" and the policy has coverage_type "{coverage_type}". '
            f'Is this loss plausibly covered under this coverage type? '
            f'Respond ONLY with a JSON object: {{"flag": "Match" | "Mismatch", "reason": "..."}}'
        )
        try:
            response = llm.invoke(prompt)
            content = response.content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            parsed = json.loads(content)
            coverage_flag = parsed.get("flag", "Unable to Verify")
        except Exception as exc:
            log.warning("LLM coverage check failed: %s", exc)
            coverage_flag = "Unable to Verify"
        details.append(_write_detail(
            verification_id, "loss_type_vs_coverage_type", coverage_type, loss_type, coverage_flag,
        ))
    else:
        details.append(_write_detail(
            verification_id, "loss_type_vs_coverage_type", coverage_type or "N/A", loss_type or "N/A", "Unable to Verify",
        ))

    # 1d. Deductible present
    deductible = policy.get("deductible")
    flag = "Match" if deductible is not None else "Unable to Verify"
    details.append(_write_detail(
        verification_id, "policy_deductible_on_record",
        "Deductible value present", str(deductible) if deductible is not None else "Missing", flag,
    ))

    return details


# ── Pillar 2: Loss facts (FNOL cross-check) ────────────────────────────────────

def _verify_loss_facts(verification_id: str, claim: dict, fnol: Optional[dict]) -> list:
    details = []

    if not fnol:
        details.append(_write_detail(
            verification_id, "fnol_submission",
            "FNOL submission found", "No FNOL record linked to this claim", "Unable to Verify",
        ))
        return details

    # 2a. FNOL submission status
    fnol_status = fnol.get("status") or "unknown"
    flag = "Match" if fnol_status == "submitted" else "Mismatch"
    details.append(_write_detail(verification_id, "fnol_status", "submitted", fnol_status, flag))

    # 2b. Cause of loss — FNOL vs claim
    fnol_cause = (fnol.get("cause_of_loss") or "").lower().strip()
    claim_loss_type = (claim.get("loss_type") or "").lower().strip()
    if fnol_cause and claim_loss_type:
        flag = "Match" if (fnol_cause in claim_loss_type or claim_loss_type in fnol_cause) else "Mismatch"
        details.append(_write_detail(
            verification_id, "cause_of_loss_consistency",
            claim_loss_type, fnol_cause, flag,
        ))
    else:
        details.append(_write_detail(
            verification_id, "cause_of_loss_consistency",
            claim_loss_type or "N/A", fnol_cause or "Missing", "Unable to Verify",
        ))

    # 2c. Date of loss — FNOL vs claim
    fnol_date = (fnol.get("date_of_loss") or "")[:10]
    claim_date = (claim.get("date_of_loss") or "")[:10]
    if fnol_date and claim_date:
        flag = "Match" if fnol_date == claim_date else "Mismatch"
        details.append(_write_detail(verification_id, "date_of_loss_consistency", claim_date, fnol_date, flag))
    else:
        details.append(_write_detail(
            verification_id, "date_of_loss_consistency",
            claim_date or "N/A", fnol_date or "Missing", "Unable to Verify",
        ))

    # 2d. Time of loss recorded
    time_of_loss = fnol.get("time_of_loss") or ""
    flag = "Match" if time_of_loss else "Mismatch"
    details.append(_write_detail(
        verification_id, "time_of_loss_recorded",
        "Time of loss present", time_of_loss if time_of_loss else "Missing", flag,
    ))

    # 2e. Occupancy at time of loss
    occupancy = fnol.get("occupancy_at_loss")
    flag = "Match" if occupancy is not None else "Unable to Verify"
    details.append(_write_detail(
        verification_id, "occupancy_at_loss_recorded",
        "Occupancy status present",
        "Occupied" if occupancy == 1 else ("Unoccupied" if occupancy == 0 else "Missing"),
        flag,
    ))

    # 2f. Sudden vs gradual — important for coverage decisions
    sudden_vs_gradual = fnol.get("sudden_vs_gradual") or ""
    flag = "Match" if sudden_vs_gradual else "Unable to Verify"
    details.append(_write_detail(
        verification_id, "sudden_vs_gradual_recorded",
        "Onset type present", sudden_vs_gradual if sudden_vs_gradual else "Missing", flag,
    ))

    # 2g. Area affected
    area_affected = fnol.get("area_affected") or ""
    flag = "Match" if area_affected else "Unable to Verify"
    details.append(_write_detail(
        verification_id, "area_affected_recorded",
        "Area affected present", area_affected if area_affected else "Missing", flag,
    ))

    return details


# ── Pillar 3: Document completeness ────────────────────────────────────────────

def _verify_documents(verification_id: str, claim: dict, documents: list) -> list:
    details = []

    if not documents:
        details.append(_write_detail(
            verification_id, "documents_uploaded",
            "At least one document uploaded", "No documents found for this claim", "Mismatch",
        ))
        return details

    # 3a. At least one document uploaded
    details.append(_write_detail(
        verification_id, "documents_uploaded",
        "At least one document uploaded", f"{len(documents)} document(s) found", "Match",
    ))

    # 3b. Required document types for this loss type
    loss_type = (claim.get("loss_type") or "").lower()
    required = _DEFAULT_REQUIRED_DOCS
    for key, docs in _REQUIRED_DOCS.items():
        if key in loss_type:
            required = docs
            break

    uploaded_types = {(d.get("document_type") or "").lower() for d in documents}
    missing = [r for r in required if r not in uploaded_types]
    if missing:
        details.append(_write_detail(
            verification_id, "required_document_types",
            ", ".join(required), f"Missing: {', '.join(missing)}", "Mismatch",
        ))
    else:
        details.append(_write_detail(
            verification_id, "required_document_types",
            ", ".join(required), "All required types present", "Match",
        ))

    # 3c. Any flagged/suspicious documents
    flagged_count = sum(1 for d in documents if d.get("flagged") == 1)
    if flagged_count > 0:
        details.append(_write_detail(
            verification_id, "document_integrity",
            "No flagged documents", f"{flagged_count} document(s) flagged as suspicious", "Mismatch",
        ))
    else:
        details.append(_write_detail(
            verification_id, "document_integrity",
            "No flagged documents", "None flagged", "Match",
        ))

    return details


# ── Pillar 4: External data cross-checks ───────────────────────────────────────

def _verify_external_data(verification_id: str, claim: dict,
                           weather: Optional[dict], drone: Optional[dict],
                           stp: Optional[dict], fraud: Optional[dict]) -> list:
    details = []

    # 4a. Weather alignment vs claim cause
    if weather:
        alignment = weather.get("drone_weather_alignment") or "Unknown"
        storm_event = weather.get("storm_event") or "Unknown"
        loss_type = claim.get("loss_type") or ""
        if alignment == "Aligned":
            flag = "Match"
        elif alignment == "Partial":
            flag = "Match"  # partial is not a hard mismatch
        else:
            flag = "Mismatch"
        details.append(_write_detail(
            verification_id, "claim_cause_vs_weather_data",
            f"Weather aligned with loss type '{loss_type}'",
            f"Storm: {storm_event} | Alignment: {alignment}",
            flag,
        ))

        # 4b. Weather severity vs claim severity
        zip_severity = weather.get("zip_code_severity_index") or "Low"
        claim_severity = (claim.get("severity") or "").lower()
        severity_map = {"low": ["Low", "Moderate"], "medium": ["Moderate", "High"], "high": ["High", "Severe"], "critical": ["Severe"]}
        expected_range = severity_map.get(claim_severity, ["Low", "Moderate", "High", "Severe"])
        flag = "Match" if zip_severity in expected_range else "Mismatch"
        details.append(_write_detail(
            verification_id, "claim_severity_vs_weather_severity",
            f"Weather severity consistent with '{claim_severity}' claim",
            f"Weather severity index: {zip_severity}",
            flag,
        ))
    else:
        details.append(_write_detail(
            verification_id, "claim_cause_vs_weather_data",
            "Weather data available", "No weather data — run ExternalDataAgent first", "Unable to Verify",
        ))
        details.append(_write_detail(
            verification_id, "claim_severity_vs_weather_severity",
            "Weather severity available", "No weather data", "Unable to Verify",
        ))

    # 4c. Claim severity vs drone assessment
    if drone:
        drone_match = drone.get("drone_match_percent") or 0
        damage_inflation = drone.get("damage_inflation_index") or "Low"
        tamper = drone.get("tamper_indicator") or "None"
        claim_severity = (claim.get("severity") or "low").lower()

        # drone_match_percent < 50 on a high/critical severity claim is suspicious
        if claim_severity in ("high", "critical") and int(drone_match) < 50:
            severity_drone_flag = "Mismatch"
        elif damage_inflation == "High":
            severity_drone_flag = "Mismatch"
        else:
            severity_drone_flag = "Match"
        details.append(_write_detail(
            verification_id, "claim_severity_vs_drone_assessment",
            f"Drone match consistent with '{claim_severity}' severity",
            f"Drone match: {drone_match}% | Damage inflation: {damage_inflation}",
            severity_drone_flag,
        ))

        # 4d. Tamper indicator
        if tamper == "None":
            details.append(_write_detail(
                verification_id, "drone_tamper_check",
                "No tampering indicators", "None detected", "Match",
            ))
        elif tamper == "Possible":
            details.append(_write_detail(
                verification_id, "drone_tamper_check",
                "No tampering indicators", "Possible tampering anomalies detected", "Mismatch",
            ))
        else:
            details.append(_write_detail(
                verification_id, "drone_tamper_check",
                "No tampering indicators", "Likely tampering — strong anomaly evidence", "Mismatch",
            ))

        # 4e. Geo match
        geo_match = drone.get("geo_match") or "Full"
        flag = "Match" if geo_match == "Full" else ("Mismatch" if geo_match == "None" else "Match")
        details.append(_write_detail(
            verification_id, "drone_geo_match",
            "Full geo match", f"Geo match: {geo_match}", flag,
        ))
    else:
        details.append(_write_detail(
            verification_id, "claim_severity_vs_drone_assessment",
            "Drone data available", "No drone data — run ExternalDataAgent first", "Unable to Verify",
        ))

    # 4f. STP classification vs fraud risk
    if stp and fraud:
        stp_category = stp.get("stp_category") or "Unknown"
        fraud_score = fraud.get("fraud_score") or 0
        # If STP category is "Auto-Approve" but fraud score is high — flag it
        if stp_category == "Auto-Approve" and int(fraud_score) >= 60:
            details.append(_write_detail(
                verification_id, "risk_score_vs_stp_classification",
                "STP category consistent with fraud risk",
                f"STP: {stp_category} but Fraud score: {fraud_score} — contradictory",
                "Mismatch",
            ))
        else:
            details.append(_write_detail(
                verification_id, "risk_score_vs_stp_classification",
                "STP category consistent with fraud risk",
                f"STP: {stp_category} | Fraud score: {fraud_score}",
                "Match",
            ))
    elif stp:
        details.append(_write_detail(
            verification_id, "risk_score_vs_stp_classification",
            "STP data available", f"STP: {stp.get('stp_category')} | No fraud snapshot available", "Unable to Verify",
        ))
    else:
        details.append(_write_detail(
            verification_id, "risk_score_vs_stp_classification",
            "STP data available", "No STP classification found — run ClaimClassificationAgent first", "Unable to Verify",
        ))

    return details


# ── Main entry point ───────────────────────────────────────────────────────────

def run_verification(claim_id: str) -> dict:
    claim = _get_claim(claim_id)
    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    policy = _get_policy(claim.get("policy_number") or "")
    fnol = _get_fnol(claim_id)
    documents = _get_documents(claim_id)
    weather = _get_weather_alignment(claim_id)
    drone = _get_drone_authenticity(claim_id)
    stp = _get_stp_result(claim_id)
    fraud = _get_fraud_snapshot(claim_id)

    verification_id = f"VER-{claim_id}-{random.randint(1000, 9999)}"

    all_details = []

    # Run all four pillars
    all_details += _verify_policy(verification_id, claim, policy)
    all_details += _verify_loss_facts(verification_id, claim, fnol)
    all_details += _verify_documents(verification_id, claim, documents)
    all_details += _verify_external_data(verification_id, claim, weather, drone, stp, fraud)

    # Compute overall result
    flags = [d["flag"] for d in all_details]
    mismatch_fields = [d["field"] for d in all_details if d["flag"] == "Mismatch"]
    unable_fields = [d["field"] for d in all_details if d["flag"] == "Unable to Verify"]

    if mismatch_fields:
        overall_status = "Completed"
        overall_result = "Discrepancies found: " + ", ".join(mismatch_fields)
    elif unable_fields:
        overall_status = "Completed"
        overall_result = "Some checks could not be verified (data pending): " + ", ".join(unable_fields)
    else:
        overall_status = "Completed"
        overall_result = "All checks matched"

    # Coverage verdict — deterministic, based only on the 3 hard/Critical policy
    # facts (policy_exists, policy_status, date_of_loss_in_policy_window). Any
    # non-Match there (Mismatch OR Unable to Verify — missing data is treated the
    # same as a confirmed problem, since neither gives enough confidence to keep
    # recommending dollar amounts) flags the claim for a human coverage review
    # before Reserve/Settlement can run. Every other check stays Advisory-only
    # and never affects this verdict.
    critical_issues = [d for d in all_details if d.get("severity") == "Critical" and d["flag"] != "Match"]
    coverage_verdict = "Flagged" if critical_issues else "Confirmed"

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO external_verifications (verification_id, claim_id, type, status, result) VALUES (%s,%s,%s,%s,%s)",
            (verification_id, claim_id, "Comprehensive Cross-Check", overall_status, overall_result),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # Summary counts per pillar for the adjuster
    pillar_summary = {
        "policy":        {d["field"]: d["flag"] for d in all_details if d["field"] in ("policy_status", "date_of_loss_in_policy_window", "loss_type_vs_coverage_type", "policy_deductible_on_record", "policy_exists")},
        "loss_facts":    {d["field"]: d["flag"] for d in all_details if d["field"] in ("fnol_status", "cause_of_loss_consistency", "date_of_loss_consistency", "time_of_loss_recorded", "occupancy_at_loss_recorded", "sudden_vs_gradual_recorded", "area_affected_recorded")},
        "documents":     {d["field"]: d["flag"] for d in all_details if d["field"] in ("documents_uploaded", "required_document_types", "document_integrity")},
        "external_data": {d["field"]: d["flag"] for d in all_details if d["field"] in ("claim_cause_vs_weather_data", "claim_severity_vs_weather_severity", "claim_severity_vs_drone_assessment", "drone_tamper_check", "drone_geo_match", "risk_score_vs_stp_classification")},
    }

    return {
        "claim_id": claim_id,
        "verification_id": verification_id,
        "status": overall_status,
        "result": overall_result,
        "total_checks": len(all_details),
        "match_count": flags.count("Match"),
        "mismatch_count": flags.count("Mismatch"),
        "unable_to_verify_count": flags.count("Unable to Verify"),
        "pillar_summary": pillar_summary,
        "coverage_verdict": coverage_verdict,
        "critical_issues": critical_issues,
        "details": all_details,
    }
