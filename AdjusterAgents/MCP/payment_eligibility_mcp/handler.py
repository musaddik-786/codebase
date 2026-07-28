"""
handler.py — Payment Eligibility
──────────────────────────────────
Determines whether a claim meets conditions for automated payment by
comparing 8 gates against auto_adjudication_threshold_configs.

Gates:
  1. loss_amount            — ai_estimated_loss <= max_loss_amount
  2. severity               — claim severity <= max_severity_level
  3. complexity             — claim complexity <= max_complexity_level
  4. fraud_score            — fraud_score < max_fraud_score
  5. fraud_ambiguity        — derived from fraud_score (< 30 = Low → pass)
  6. coverage_confirmed     — adjuster_findings.coverage_confirmed = "Yes"
  7. subrogation_likelihood — loss_assessments.subrogation_likelihood != "High"
  8. stp_score              — ai_decision_recommendations.stp_score >= min_stp_score (skip if no record)

Write-back (when eligible = True):
  - INSERT auto_adjudication_records
  - UPDATE claims.status = 'Approved'

Always writes:
  - INSERT audit_trace_logs (one row per gate)
"""

import json
import logging
import os
import sys
import uuid
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

log = logging.getLogger(__name__)

_SEVERITY_ORDER = ["Low", "Medium", "High", "Critical"]
_COMPLEXITY_ORDER = ["Simple", "Moderate", "Complex"]


def _get_llm():
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def get_auto_adjudication_thresholds() -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM auto_adjudication_threshold_configs ORDER BY id")
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


def _get_loss_estimation(claim_id: str) -> Optional[dict]:
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


def _get_adjuster_findings(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM adjuster_findings WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def _get_loss_assessment(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM loss_assessments WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def _get_stp_recommendation(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM ai_decision_recommendations WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()



def _write_auto_adjudication_record(
    claim_id: str,
    eligible: bool,
    decision: str,
    stp_category: str,
    gates_passed: int,
    gates_failed: int,
    failed_gate_list: list,
    threshold_config_id: str,
    recommendation: str,
) -> None:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        record_id = f"AAR-{uuid.uuid4().hex[:8].upper()}"
        cur.execute(
            """
            INSERT INTO auto_adjudication_records (
                record_id, claim_id, eligible_for_auto_adjudication,
                decision, stp_category, gates_passed, gates_failed,
                failed_gate_list, threshold_config_id, recommendation
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record_id, claim_id, eligible, decision, stp_category,
                gates_passed, gates_failed,
                json.dumps(failed_gate_list), threshold_config_id, recommendation,
            ),
        )
        conn.commit()
        log.info("auto_adjudication_records written: %s for claim %s", record_id, claim_id)
    except Exception as exc:
        log.error("_write_auto_adjudication_record failed: %s", exc)
        conn.rollback()
    finally:
        conn.close()


def _write_audit_trace_logs(claim_id: str, gates: dict) -> None:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        for gate_name, gate_data in gates.items():
            if gate_data.get("skip"):
                result = "SKIP"
            elif gate_data.get("pass"):
                result = "PASS"
            else:
                result = "FAIL"
            cur.execute(
                """
                INSERT INTO audit_trace_logs (
                    claim_id, gate_name, gate_result, value_evaluated, threshold_used
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    claim_id,
                    gate_name,
                    result,
                    str(gate_data.get("value", "")),
                    str(gate_data.get("threshold", "")),
                ),
            )
        conn.commit()
    except Exception as exc:
        log.error("_write_audit_trace_logs failed: %s", exc)
        conn.rollback()
    finally:
        conn.close()


def _update_claim_status(claim_id: str, status: str) -> None:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE claims SET status = %s WHERE claim_number = %s",
            (status, claim_id),
        )
        conn.commit()
    except Exception as exc:
        log.error("_update_claim_status failed: %s", exc)
        conn.rollback()
    finally:
        conn.close()


def confirm_payment_approval(claim_id: str) -> dict:
    """
    Explicit commit tool for the adjuster's own final payment decision — never
    called by check_eligibility() itself (which is a pure recommendation, like
    recommend_reserve/recommend_settlement/score_leakage). Called only from
    AdjusterOrchestrator's deterministic /payment-decision endpoint, once a
    human has actually approved payment for this claim.
    """
    _update_claim_status(claim_id, "Approved")
    return {"claim_id": claim_id, "status": "Approved"}


def _idx(value: str, order: list) -> int:
    return order.index(value) if value in order else 1


def get_auto_adjudication_record(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM auto_adjudication_records WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def check_eligibility(claim_id: str) -> dict:
    """
    Gates payment eligibility across 8 checks. On full pass, writes
    auto_adjudication_records and updates claims.status = 'Approved'.
    Always writes one audit_trace_logs row per gate.
    """
    claim = _get_claim(claim_id)
    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    thresholds = get_auto_adjudication_thresholds()
    if not thresholds:
        return {
            "claim_id": claim_id,
            "eligible_for_auto_adjudication": False,
            "reason": "No threshold configs found",
        }

    threshold = thresholds[0]
    estimation = _get_loss_estimation(claim_id)
    fraud_snapshot = _get_fraud_risk(claim_id)
    adjuster_findings = _get_adjuster_findings(claim_id)
    loss_assessment = _get_loss_assessment(claim_id)
    stp_rec = _get_stp_recommendation(claim_id)

    # --- Raw values ---
    loss_amount = (
        float(estimation.get("ai_estimated_loss") or 0)
        if estimation
        else float(claim.get("estimated_cost") or 0)
    )
    severity = claim.get("severity") or "Medium"
    complexity = claim.get("complexity") or "Moderate"
    fraud_score = int(fraud_snapshot.get("fraud_score") or 0) if fraud_snapshot else 0
    coverage_confirmed = (
        (adjuster_findings.get("coverage_confirmed") or "").strip()
        if adjuster_findings
        else ""
    )
    subrogation = (
        (loss_assessment.get("subrogation_likelihood") or "Low")
        if loss_assessment
        else "Low"
    )
    stp_score = int(stp_rec.get("stp_score") or 0) if stp_rec else None

    # --- Thresholds ---
    max_loss = float(threshold.get("max_loss_amount") or 10000)
    max_severity = threshold.get("max_severity_level") or "Medium"
    max_complexity = threshold.get("max_complexity_level") or "Simple"
    max_fraud_score = int(threshold.get("max_fraud_score") or 50)
    min_stp_score = int(threshold.get("min_stp_score") or 50)

    # --- Derived ---
    fraud_ambiguity = (
        "Low" if fraud_score < 30
        else ("Medium" if fraud_score < 60 else "High")
    )
    stp_category = (
        "Full STP" if (stp_score is not None and stp_score >= 85)
        else ("Partial STP" if (stp_score is not None and stp_score >= 50) else "Manual")
    )

    # --- 8 Gates ---
    gates = {
        "loss_amount": {
            "pass": loss_amount <= max_loss,
            "value": loss_amount,
            "threshold": max_loss,
        },
        "severity": {
            "pass": _idx(severity, _SEVERITY_ORDER) <= _idx(max_severity, _SEVERITY_ORDER),
            "value": severity,
            "threshold": max_severity,
        },
        "complexity": {
            "pass": _idx(complexity, _COMPLEXITY_ORDER) <= _idx(max_complexity, _COMPLEXITY_ORDER),
            "value": complexity,
            "threshold": max_complexity,
        },
        "fraud_score": {
            "pass": fraud_score < max_fraud_score,
            "value": fraud_score,
            "threshold": max_fraud_score,
        },
        "fraud_ambiguity": {
            "pass": fraud_ambiguity == "Low",
            "value": fraud_ambiguity,
            "threshold": "Low",
        },
        "coverage_confirmed": {
            "pass": coverage_confirmed == "Yes",
            "value": coverage_confirmed or "Not found",
            "threshold": "Yes",
        },
        "subrogation_likelihood": {
            "pass": subrogation != "High",
            "value": subrogation,
            "threshold": "Not High",
        },
        "stp_score": {
            # Skip (counts as pass) when no STP record exists — upstream step may not have run
            "pass": True if stp_score is None else stp_score >= min_stp_score,
            "skip": stp_score is None,
            "value": stp_score if stp_score is not None else "No record",
            "threshold": min_stp_score,
        },
    }

    failed_gates = [k for k, v in gates.items() if not v["pass"]]
    eligible = len(failed_gates) == 0
    decision = "FULL_STP" if eligible else "MANUAL_REVIEW"

    llm = _get_llm()
    prompt = f"""
You are a payment eligibility specialist. A claim has {"PASSED" if eligible else "FAILED"} eligibility gating.

Claim context:
  claim_id: {claim_id}
  loss_amount: {loss_amount}
  severity: {severity}
  complexity: {complexity}
  fraud_score: {fraud_score}
  fraud_ambiguity: {fraud_ambiguity}
  coverage_confirmed: {coverage_confirmed or "Not found"}
  subrogation_likelihood: {subrogation}
  stp_score: {stp_score}
  stp_category: {stp_category}
  gates_failed: {failed_gates}
  config_used: {threshold.get('config_id', 'DEFAULT')}

Provide a "recommendation": one sentence on what the adjuster should do next.

Respond with ONLY a JSON object: {{"recommendation": "..."}}
"""
    response = llm.invoke(prompt)
    content = response.content.strip().strip("`")
    if content.startswith("json"):
        content = content[4:]
    try:
        recommendation = json.loads(content).get("recommendation", "")
    except Exception:
        recommendation = (
            "Proceed to manual adjudication review."
            if not eligible
            else "Claim is eligible for automated payment processing."
        )

    # Always write audit trace — one row per gate
    _write_audit_trace_logs(claim_id, gates)

    # Write-back only on full pass. NOTE 2026-07-20: this used to also call
    # _update_claim_status(claim_id, "Approved") right here — i.e. simply
    # running this check could silently move a claim to Approved status with
    # no adjuster involved at all. That's been removed: this function is now
    # a pure recommendation (like recommend_reserve/recommend_settlement/
    # score_leakage), and committing claims.status only happens when the
    # adjuster makes their final payment decision — see AdjusterOrchestrator's
    # /payment-decision endpoint.
    if eligible:
        gates_passed = sum(1 for v in gates.values() if v.get("pass"))
        _write_auto_adjudication_record(
            claim_id=claim_id,
            eligible=True,
            decision=decision,
            stp_category=stp_category,
            gates_passed=gates_passed,
            gates_failed=0,
            failed_gate_list=[],
            threshold_config_id=threshold.get("config_id", "DEFAULT"),
            recommendation=recommendation,
        )

    return {
        "claim_id": claim_id,
        "eligible_for_auto_adjudication": eligible,
        "decision": decision,
        "stp_category": stp_category,
        "gates": gates,
        "failed_gates": failed_gates,
        "threshold_config": threshold.get("config_id", "DEFAULT"),
        "recommendation": recommendation,
    }
