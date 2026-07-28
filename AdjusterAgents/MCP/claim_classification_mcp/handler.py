"""
handler.py — Claim Classification / Triage Routing
──────────────────────────────────────────────────────
Deterministic claim classification aligned with the reference implementation.

Complexity thresholds (from auto_adjudication_threshold_configs):
  estimated_cost <= DEFAULT  (≤$10,000)  → Simple
  estimated_cost <= HIGH_VALUE (≤$25,000) → Moderate
  estimated_cost >  HIGH_VALUE (>$25,000) → Complex

Routing priority:
  1. fraud_score >= 70      → Specialist Review  (SIU equivalent)
  2. complexity == Complex   → Specialist Review
  3. severity in Minor/Low   → Fast Track
  4. otherwise               → Standard

No LLM is used for the classification decision. LLM may be used
downstream only for narrative explanation of the result.
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 10000
_HIGH_VALUE_THRESHOLD = 25000


class FraudScoreUnavailableError(Exception):
    """
    Raised when the fraud score cannot be reliably determined.

    Differentiates two scenarios that must never be treated as equivalent:
      - No fraud screening record exists for the claim (not yet scored).
      - The database query itself failed.

    In both cases, routing MUST NOT proceed using a fabricated score of 0.
    Missing fraud data ≠ fraud score 0.
    """


def _load_thresholds() -> dict:
    """
    Load max_loss_amount from auto_adjudication_threshold_configs.
    Falls back to hardcoded defaults if the table is empty or unavailable.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT config_id, max_loss_amount FROM auto_adjudication_threshold_configs"
        )
        rows = cur.fetchall() or []
        result = {}
        for row in rows:
            d = row_to_dict(row)
            if d:
                result[d["config_id"]] = float(d.get("max_loss_amount") or 0)
        return result
    except Exception:
        conn.rollback()
        return {}
    finally:
        conn.close()


def get_claim_details(claim_number: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_number,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_fraud_score(claim_number: str) -> int:
    """
    Return the latest fraud score from fraud_risk_snapshots.

    Raises FraudScoreUnavailableError in two distinct situations:
      1. No row found — claim has not been fraud-screened yet.
         Run the Fraud Screening agent before classifying this claim.
      2. DB query fails — retrieval error; fraud data is unavailable.

    A return value of 0 means a legitimate low-risk score was stored in the DB.
    Missing data is NEVER substituted with 0.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT fraud_score FROM fraud_risk_snapshots WHERE claim_id = %s "
            "ORDER BY created_at DESC LIMIT 1",
            (claim_number,),
        )
        row = cur.fetchone()
        if row is None:
            raise FraudScoreUnavailableError(
                f"No fraud screening record found for claim {claim_number}. "
                "Complete fraud screening before classification."
            )
        score = row["fraud_score"]
        if score is None:
            raise FraudScoreUnavailableError(
                f"Fraud score is NULL in fraud_risk_snapshots for claim {claim_number}."
            )
        return int(score)
    except FraudScoreUnavailableError:
        raise
    except Exception as exc:
        conn.rollback()
        raise FraudScoreUnavailableError(
            f"Failed to retrieve fraud score for claim {claim_number}: {exc}"
        ) from exc
    finally:
        conn.close()


def get_complexity_from_cost(
    estimated_cost, default_threshold: float, high_value_threshold: float
) -> str:
    try:
        cost = float(estimated_cost or 0)
    except Exception:
        cost = 0.0

    if cost <= default_threshold:
        return "Simple"
    if cost <= high_value_threshold:
        return "Moderate"
    return "Complex"


def determine_routing(fraud_score: int, complexity: str, severity: str) -> str:
    if fraud_score >= 70:
        return "Specialist Review"
    if complexity == "Complex":
        return "Specialist Review"
    if str(severity or "").strip().lower() in ("minor", "low"):
        return "Fast Track"
    return "Standard"


def classify_claim(claim_number: str) -> dict:
    """
    Deterministic classification — no LLM involved.
    Complexity comes from cost thresholds; routing from fraud score priority.
    Does NOT persist — call save_classification to persist.
    """
    claim = get_claim_details(claim_number)
    if not claim:
        raise ValueError(f"Claim {claim_number} not found")

    thresholds = _load_thresholds()
    default_max = thresholds.get("DEFAULT") or _DEFAULT_THRESHOLD
    high_value_max = thresholds.get("HIGH_VALUE") or _HIGH_VALUE_THRESHOLD

    estimated_cost = claim.get("estimated_cost")
    severity = claim.get("severity")

    complexity = get_complexity_from_cost(estimated_cost, default_max, high_value_max)
    # Raises FraudScoreUnavailableError if fraud data is missing or unreadable.
    # Routing is NOT performed on fabricated data — the error propagates to the caller.
    fraud_score = get_fraud_score(claim_number)
    routing = determine_routing(fraud_score, complexity, severity)

    return {
        "claim_number": claim_number,
        "complexity": complexity,
        "routing": routing,
        "damage_severity": severity,
        "fraud_risk_score": fraud_score,
        "thresholds_used": {
            "default_max": default_max,
            "high_value_max": high_value_max,
        },
    }


_VALID_COMPLEXITIES = {"Simple", "Moderate", "Complex"}
_VALID_ROUTES = {"Fast Track", "Standard", "Specialist Review"}


def save_classification(claim_number: str, complexity: str, routing: str) -> dict:
    """
    Persist a classification result — inserts into claim_triage and updates
    claims.complexity. Persists the actual fraud_risk_score (not NULL).
    Validates complexity and routing values before touching the DB.
    """
    if complexity not in _VALID_COMPLEXITIES:
        raise ValueError(
            f"Invalid complexity '{complexity}'. Must be one of: {sorted(_VALID_COMPLEXITIES)}"
        )
    if routing not in _VALID_ROUTES:
        raise ValueError(
            f"Invalid routing '{routing}'. Must be one of: {sorted(_VALID_ROUTES)}"
        )

    claim = get_claim_details(claim_number)
    if not claim:
        raise ValueError(f"Claim {claim_number} not found")

    fraud_score = get_fraud_score(claim_number)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO claim_triage
                (claim_id, damage_severity, complexity, fraud_risk_score, routing)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (claim_number, claim.get("severity"), complexity, fraud_score, routing),
        )
        cur.execute(
            "UPDATE claims SET complexity = %s WHERE claim_number = %s",
            (complexity, claim_number),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "claim_number": claim_number,
        "complexity": complexity,
        "routing": routing,
        "damage_severity": claim.get("severity"),
        "fraud_risk_score": fraud_score,
        "saved": True,
    }


def get_claim_classification(claim_number: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM claim_triage WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# NEW FUNCTIONS: Intake Validation & STP Scoring
# ---------------------------------------------------------------------------

_FNOL_MANDATORY_FIELDS = [
    "policy_number",
    "policyholder_name",
    "loss_type",
    "short_description",
    "location",
    "date_of_loss",
    "severity",
]


def _compute_fnol_completeness(claim: dict) -> float:
    """Computes FNOL completeness score (0-100) from claim record.

    Checks 7 mandatory fields: policy_number, policyholder_name, loss_type,
    short_description, location, date_of_loss, severity.
    Returns float 0-100.
    """
    filled = sum(1 for f in _FNOL_MANDATORY_FIELDS if claim.get(f))
    return (filled / 7) * 100


def _compute_readiness_score(claim: dict) -> float:
    """Computes claim readiness score (0-100):
      coverage confirmed (== 1) → +40 pts
      date_of_loss present      → +25 pts
      severity present          → +20 pts
      estimated_cost > 0        → +15 pts
    Returns float 0-100.
    """
    score = 0.0
    coverage = claim.get("coverage")
    try:
        if int(coverage) == 1:
            score += 40
    except (TypeError, ValueError):
        pass
    if claim.get("date_of_loss"):
        score += 25
    if claim.get("severity"):
        score += 20
    try:
        if float(claim.get("estimated_cost") or 0) > 0:
            score += 15
    except (TypeError, ValueError):
        pass
    return score


def _get_subrogation_risk(claim_number: str) -> tuple:
    """Reads subrogation_likelihood from adjuster_findings table.

    Returns tuple: (risk_str, score_int) where:
      "High"   → ("High",   9)
      "Medium" → ("Medium", 5)
      "Low"    → ("Low",    2)
      Default: ("Low", 2) if no record found.
    """
    _SUBRO_MAP = {
        "High": ("High", 9),
        "Medium": ("Medium", 5),
        "Low": ("Low", 2),
    }
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT subrogation_likelihood FROM adjuster_findings "
            "WHERE claim_id = %s ORDER BY created_at DESC LIMIT 1",
            (claim_number,),
        )
        row = cur.fetchone()
        if row is None:
            return ("Low", 2)
        likelihood = str(row["subrogation_likelihood"] or "").strip()
        return _SUBRO_MAP.get(likelihood, ("Low", 2))
    except Exception:
        conn.rollback()
        return ("Low", 2)
    finally:
        conn.close()


def run_intake_validation(claim_number: str) -> dict:
    """Validates 7 mandatory FNOL fields for a claim.

    Returns completeness_score (0-100), missing_fields list, passed (bool).
    Writes result to intake_validation_result_output table.

    Mandatory fields checked: policy_number, policyholder_name, loss_type,
    short_description, location, date_of_loss, severity (7 fields total).
    completeness_score = (filled_count / 7) * 100 (rounded integer).
    passed = completeness_score >= 85 AND no blocking failure.

    Blocking failures (prevent processing):
      - no short_description (loss description missing)
      - no location
      - coverage == 0 or False

    Writes to intake_validation_result_output:
      claim_id, completeness_score, coverage_status, fraud_risk, passed, blocking_reason
    """
    claim = get_claim_details(claim_number)
    if not claim:
        raise ValueError(f"Claim {claim_number} not found")

    filled_count = sum(1 for f in _FNOL_MANDATORY_FIELDS if claim.get(f))
    completeness_score = round((filled_count / 7) * 100)
    missing_fields = [f for f in _FNOL_MANDATORY_FIELDS if not claim.get(f)]

    # Determine blocking failure (checked in priority order)
    blocking_reason = None
    if not claim.get("policy_number"):
        blocking_reason = "policy number missing"
    elif not claim.get("short_description"):
        blocking_reason = "loss description missing"
    elif not claim.get("location"):
        blocking_reason = "location missing"
    else:
        coverage = claim.get("coverage")
        try:
            coverage_val = int(coverage) if coverage is not None else 0
        except (TypeError, ValueError):
            coverage_val = 0
        if coverage_val == 0:
            blocking_reason = "coverage not confirmed"

    passed = completeness_score >= 85 and blocking_reason is None

    # Coverage status label
    coverage = claim.get("coverage")
    try:
        coverage_confirmed = int(coverage) if coverage is not None else 0
    except (TypeError, ValueError):
        coverage_confirmed = 0
    coverage_status = "Confirmed" if coverage_confirmed == 1 else "Not Confirmed"

    # Fraud risk label (best-effort; does not block validation if unavailable)
    try:
        fraud_score = get_fraud_score(claim_number)
        if fraud_score >= 70:
            fraud_risk = "High"
        elif fraud_score >= 40:
            fraud_risk = "Medium"
        else:
            fraud_risk = "Low"
    except FraudScoreUnavailableError:
        fraud_risk = "Unknown"

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO intake_validation_result_output
                (claim_id, completeness_score, coverage_status, fraud_risk, passed, blocking_reason)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                claim_number,
                completeness_score,
                coverage_status,
                fraud_risk,
                passed,
                blocking_reason,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "claim_number": claim_number,
        "completeness_score": completeness_score,
        "missing_fields": missing_fields,
        "coverage_status": coverage_status,
        "fraud_risk": fraud_risk,
        "passed": passed,
        "blocking_reason": blocking_reason,
    }


def compute_stp_score(claim_number: str) -> dict:
    """Computes 8-factor weighted STP score from the reference bundle formula.

    raw = fnolCompleteness * 0.20
        + readinessScore * 0.15
        + coverageLevel * 10 * 0.15      # coverageLevel: confirmed=10, not confirmed=4
        + (10 - severityLevel) * 10 * 0.10  # inverted: Low=2, Medium=5, High=8, Critical=10
        + (10 - fraudLevel) * 10 * 0.10    # inverted: Low=2 (<40), Medium=5 (40-69), High=9 (>=70)
        + (10 - subroLevel) * 10 * 0.10    # inverted: Low=2, Medium=5, High=9
        + vis * 0.15                        # default 50 if no vendor data
        + similarityIndex * 100 * 0.05      # claims.ai_confidence / 100, default 0.7

    stp_score = min(100, max(0, round(raw)))

    STP Category rules:
      High or Critical severity → always "Manual" (hard override)
      score >= 85 AND fraudAmbiguity="Low" AND subrogationRisk != "High" → "Full STP"
      score >= 70 → "Vendor STP"
      score >= 50 → "Fast Track"
      else → "Manual"

    Routing mapping (to existing routing values used in save_classification):
      "Full STP"   → "Fast Track"
      "Vendor STP" → "Standard"
      "Fast Track" → "Standard"
      "Manual"     → "Specialist Review"

    Saves inputs to stp_score_input_factors and result to stp_calculation_result
    and segmentation_result_output.

    Returns dict with:
      claim_number, stp_score, stp_category, routing, fraud_ambiguity,
      subrogation_risk, inputs (all 8 factor values), complexity.

    Raises FraudScoreUnavailableError if fraud score cannot be retrieved.
    """
    claim = get_claim_details(claim_number)
    if not claim:
        raise ValueError(f"Claim {claim_number} not found")

    # --- Factor 1 & 2: FNOL completeness and readiness ---
    fnol_completeness = _compute_fnol_completeness(claim)
    readiness_score = _compute_readiness_score(claim)

    # --- Factor 3: Coverage level ---
    coverage = claim.get("coverage")
    try:
        coverage_val = int(coverage) if coverage is not None else 0
    except (TypeError, ValueError):
        coverage_val = 0
    coverage_level = 10 if coverage_val == 1 else 4

    # --- Factor 4: Severity level (inverted scale) ---
    severity_str = str(claim.get("severity") or "").strip().lower()
    _SEV_MAP = {
        "low": 2,
        "minor": 2,
        "medium": 5,
        "moderate": 5,
        "high": 8,
        "critical": 10,
    }
    severity_level = _SEV_MAP.get(severity_str, 5)

    # --- Factor 5: Fraud level — raises FraudScoreUnavailableError if missing ---
    fraud_score = get_fraud_score(claim_number)
    if fraud_score >= 70:
        fraud_level = 9
        fraud_ambiguity = "High"
    elif fraud_score >= 40:
        fraud_level = 5
        fraud_ambiguity = "Medium"
    else:
        fraud_level = 2
        fraud_ambiguity = "Low"

    # --- Factor 6: Subrogation risk ---
    subro_risk_str, subro_level = _get_subrogation_risk(claim_number)

    # --- Factor 7: Vendor impact score (vis) — 0 when no vendor data (reference default) ---
    vis = 0.0

    # --- Factor 8: Similarity index from claims.ai_confidence / 100 — 0 when absent ---
    try:
        ai_confidence = float(claim.get("ai_confidence") or 0)
        similarity_index = ai_confidence / 100 if ai_confidence > 0 else 0.0
    except (TypeError, ValueError):
        similarity_index = 0.0

    # --- Raw score ---
    raw = (
        fnol_completeness * 0.20
        + readiness_score * 0.15
        + coverage_level * 10 * 0.15
        + (10 - severity_level) * 10 * 0.10
        + (10 - fraud_level) * 10 * 0.10
        + (10 - subro_level) * 10 * 0.10
        + vis * 0.15
        + similarity_index * 100 * 0.05
    )
    stp_score = min(100, max(0, round(raw)))

    # --- Complexity from cost thresholds ---
    thresholds = _load_thresholds()
    default_max = thresholds.get("DEFAULT") or _DEFAULT_THRESHOLD
    high_value_max = thresholds.get("HIGH_VALUE") or _HIGH_VALUE_THRESHOLD
    complexity = get_complexity_from_cost(claim.get("estimated_cost"), default_max, high_value_max)

    # --- STP Category (Hard override first) ---
    if severity_str in ("high", "critical"):
        stp_category = "Manual"
    elif stp_score >= 85 and fraud_ambiguity == "Low" and subro_risk_str != "High":
        stp_category = "Full STP"
    elif stp_score >= 70:
        stp_category = "Vendor-STP"
    elif stp_score >= 50:
        stp_category = "Fast Track"
    else:
        stp_category = "Manual"

    # --- Routing mapping ---
    _ROUTING_MAP = {
        "Full STP": "Fast Track",
        "Vendor-STP": "Standard",
        "Fast Track": "Standard",
        "Manual": "Specialist Review",
    }
    routing = _ROUTING_MAP[stp_category]

    inputs = {
        "fnol_completeness": fnol_completeness,
        "readiness_score": readiness_score,
        "coverage_score": coverage_level,
        "severity_score": severity_level,
        "fraud_ambiguity_score": fraud_level,
        "subrogation_risk_score": subro_level,
        "vis": vis,
        "similarity_index": similarity_index,
    }

    # --- Persist results ---
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO stp_score_input_factors
                (claim_id, fnol_completeness, readiness_score, coverage_score,
                 severity_score, fraud_ambiguity_score, subrogation_risk_score,
                 vis, similarity_index, fraud_ambiguity, subrogation_risk)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                claim_number,
                fnol_completeness,
                readiness_score,
                coverage_level,
                severity_level,
                fraud_level,
                subro_level,
                vis,
                similarity_index,
                fraud_ambiguity,
                subro_risk_str,
            ),
        )
        cur.execute(
            """
            INSERT INTO stp_calculation_result
                (claim_id, weighted_score, stp_category, fraud_ambiguity, subrogation_risk)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (claim_number, stp_score, stp_category, fraud_ambiguity, subro_risk_str),
        )
        cur.execute(
            """
            INSERT INTO segmentation_result_output
                (claim_id, severity, complexity, stp_score, recommended_path)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (claim_number, claim.get("severity"), complexity, stp_score, routing),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "claim_number": claim_number,
        "weighted_score": stp_score,
        "stp_category": stp_category,
        "recommended_path": routing,
        "fraud_ambiguity": fraud_ambiguity,
        "subrogation_risk": subro_risk_str,
        "inputs": inputs,
        "complexity": complexity,
    }


def get_stp_result(claim_number: str) -> dict:
    """Retrieves most recent STP calculation result for a claim.

    Returns the stp_calculation_result row or None.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM stp_calculation_result WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_intake_validation_result(claim_number: str) -> dict:
    """Retrieves most recent intake validation result for a claim.

    Returns the intake_validation_result_output row or None.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM intake_validation_result_output WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()
