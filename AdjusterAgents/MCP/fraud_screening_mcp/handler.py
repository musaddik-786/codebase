# """
# handler.py — Fraud Screening
# ──────────────────────────────
# AI-assisted fraud indicator identification, fraud flag/signal writing, and
# aggregate fraud risk snapshot computation for a claim.
# """

# import json
# import logging
# import os
# import re
# import sys
# from typing import Optional

# sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

# from db import get_db_connection, row_to_dict  # noqa: E402
# from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

# log = logging.getLogger(__name__)


# def _get_llm():
#     return AzureChatOpenAI(
#         api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#         api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
#         azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
#         azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     )


# def get_fraud_flags(claim_id: str) -> list:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM fraud_flags WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
#         return row_to_dict(cur.fetchall())
#     finally:
#         conn.close()


# def write_fraud_flag(claim_id: str, flag_type: str, flag_description: str, risk_score: int, detected_by: str) -> dict:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO fraud_flags (claim_id, flag_type, flag_description, risk_score, detected_by, status)
#             VALUES (%s,%s,%s,%s,%s, 'Active')
#             RETURNING id
#             """,
#             (claim_id, flag_type, flag_description, risk_score, detected_by),
#         )
#         new_id = cur.fetchone()["id"]
#         conn.commit()
#         return {"id": new_id, "claim_id": claim_id, "flag_type": flag_type,
#                 "flag_description": flag_description, "risk_score": risk_score, "detected_by": detected_by}
#     finally:
#         conn.close()


# def get_ai_fraud_signals(claim_id: str) -> list:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM ai_fraud_signals WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
#         return row_to_dict(cur.fetchall())
#     finally:
#         conn.close()


# def write_ai_fraud_signal(claim_id: str, fraud_score: int, indicator: str, value: Optional[str] = None) -> dict:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "INSERT INTO ai_fraud_signals (claim_id, fraud_score, indicator, value) VALUES (%s,%s,%s,%s) RETURNING id",
#             (claim_id, fraud_score, indicator, value),
#         )
#         new_id = cur.fetchone()["id"]
#         conn.commit()
#         return {"id": new_id, "claim_id": claim_id, "fraud_score": fraud_score,
#                 "indicator": indicator, "value": value}
#     finally:
#         conn.close()


# def get_fraud_risk_snapshot(claim_id: str) -> dict:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM fraud_risk_snapshots WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
#             (claim_id,),
#         )
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def write_fraud_risk_snapshot(claim_id: str, fraud_score: int, red_flag_count: int = 0,
#                                prior_claims: str = "Low", vendor_risk: str = "Low") -> dict:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO fraud_risk_snapshots (claim_id, fraud_score, red_flag_count, prior_claims, vendor_risk)
#             VALUES (%s,%s,%s,%s,%s)
#             RETURNING id
#             """,
#             (claim_id, fraud_score, red_flag_count, prior_claims, vendor_risk),
#         )
#         new_id = cur.fetchone()["id"]
#         conn.commit()
#         return {"id": new_id, "claim_id": claim_id, "fraud_score": fraud_score,
#                 "red_flag_count": red_flag_count, "prior_claims": prior_claims, "vendor_risk": vendor_risk}
#     finally:
#         conn.close()


# def _get_claim(claim_id: str) -> Optional[dict]:
#     # Normalize to avoid whitespace/case mismatches
#     claim_id = claim_id.strip().upper()
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_id,))
#         row = cur.fetchone()
#         if row:
#             return row_to_dict(row)
#         # be lenient: try numeric id
#         if claim_id.isdigit():
#             cur.execute("SELECT * FROM claims WHERE id = %s", (int(claim_id),))
#             return row_to_dict(cur.fetchone())
#         return None
#     finally:
#         conn.close()


# def _extract_json(content: str) -> str:
#     """Safely extract the first JSON object from an LLM response."""
#     match = re.search(r'\{.*\}', content, re.DOTALL)
#     return match.group(0) if match else content


# def run_fraud_screening(claim_id: str) -> dict:
#     claim_id = claim_id.strip().upper()
#     claim = _get_claim(claim_id)
#     if not claim:
#         raise ValueError(f"Claim {claim_id} not found")

#     log.info("Running fraud screening for claim %s: %s", claim_id, {
#         k: claim.get(k) for k in ("loss_type", "severity", "estimated_cost", "date_of_loss")
#     })

#     llm = _get_llm()
#     prompt = f"""
# You are a fraud-screening assistant for an insurance claims adjuster.
# Given the claim details below, identify 1-3 potential fraud indicators.
# Always identify at least 1-2 indicators, even if they are weak or low-risk.
# For each indicator provide: "indicator" (short name), "value" (brief
# supporting detail/observation), and "risk_score" (0-100, how suspicious
# this indicator is). Low-risk indicators should have risk_score in the 10-30 range.

# Claim details:
#   loss_type: {claim.get('loss_type')}
#   short_description: {claim.get('short_description')}
#   severity: {claim.get('severity')}
#   estimated_cost: {claim.get('estimated_cost')}
#   date_of_loss: {claim.get('date_of_loss')}

# Respond with ONLY a JSON object: {{"indicators": [{{"indicator": "...", "value": "...", "risk_score": 0}}, ...]}}
# """
#     response = llm.invoke(prompt)
#     content = response.content.strip()
#     content = _extract_json(content)
#     try:
#         parsed = json.loads(content)
#         indicators = parsed.get("indicators", [])
#     except Exception:
#         log.warning("Could not parse LLM JSON response for claim %s — raw: %s", claim_id, content)
#         indicators = []

#     signals = []
#     flags = []
#     for ind in indicators[:3]:
#         indicator = ind.get("indicator", "Unknown")
#         value = ind.get("value")
#         risk_score = int(ind.get("risk_score", 0))
#         signals.append(write_ai_fraud_signal(claim_id, risk_score, indicator, value))
#         # Lower threshold to 40 so moderate-risk signals also create flags
#         if risk_score >= 40:
#             flags.append(write_fraud_flag(
#                 claim_id, indicator, value or indicator, risk_score, "FraudScreeningAgent",
#             ))

#     if signals:
#         # Average score is more representative than max alone
#         fraud_score = int(sum(s["fraud_score"] for s in signals) / len(signals))
#     else:
#         fraud_score = 0

#     snapshot = write_fraud_risk_snapshot(
#         claim_id, fraud_score, red_flag_count=len(flags), prior_claims="Low", vendor_risk="Low",
#     )

#     return {
#         "claim_id": claim_id,
#         "ai_fraud_signals": signals,
#         "fraud_flags": flags,
#         "fraud_risk_snapshot": snapshot,
#         "fraud_score": fraud_score,
#     }



"""
handler.py — Fraud Screening
──────────────────────────────
AI-assisted fraud indicator identification, fraud flag/signal writing, and
aggregate fraud risk snapshot computation for a claim.
"""

import json
import logging
import os
import re
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

log = logging.getLogger(__name__)

#fraud screening new parameters
DOCUMENT_LOSS_TYPES = {
    "fire",
    "fire damage",
    "theft",
    "auto",
    "structural",
    "unknown",
}

DRONE_LOSS_TYPES = {
    "water damage",
    "flood",
    "storm",
    "thunderstorm",
    "hail",
    "wind",
    "lightning",
    "snow",
    "ice",
}

def _get_llm():
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def get_fraud_flags(claim_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM fraud_flags WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def write_fraud_flag(claim_id: str, flag_type: str, flag_description: str, risk_score: int, detected_by: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO fraud_flags (claim_id, flag_type, flag_description, risk_score, detected_by, status)
            VALUES (%s,%s,%s,%s,%s, 'Active')
            RETURNING id
            """,
            (claim_id, flag_type, flag_description, risk_score, detected_by),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return {"id": new_id, "claim_id": claim_id, "flag_type": flag_type,
                "flag_description": flag_description, "risk_score": risk_score, "detected_by": detected_by}
    finally:
        conn.close()


def get_ai_fraud_signals(claim_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ai_fraud_signals WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def write_ai_fraud_signal(claim_id: str, fraud_score: int, indicator: str, value: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ai_fraud_signals (claim_id, fraud_score, indicator, value) VALUES (%s,%s,%s,%s) RETURNING id",
            (claim_id, fraud_score, indicator, value),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return {"id": new_id, "claim_id": claim_id, "fraud_score": fraud_score,
                "indicator": indicator, "value": value}
    finally:
        conn.close()


def get_fraud_risk_snapshot(claim_id: str) -> dict:
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


def write_fraud_risk_snapshot(claim_id: str, fraud_score: int, red_flag_count: int = 0,
                               prior_claims: str = "Low", vendor_risk: str = "Low") -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO fraud_risk_snapshots (claim_id, fraud_score, red_flag_count, prior_claims, vendor_risk)
            VALUES (%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (claim_id, fraud_score, red_flag_count, prior_claims, vendor_risk),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return {"id": new_id, "claim_id": claim_id, "fraud_score": fraud_score,
                "red_flag_count": red_flag_count, "prior_claims": prior_claims, "vendor_risk": vendor_risk}
    finally:
        conn.close()


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
        # be lenient: try numeric id
        if claim_id.isdigit():
            cur.execute("SELECT * FROM claims WHERE id = %s", (int(claim_id),))
            return row_to_dict(cur.fetchone())
        return None
    finally:
        conn.close()

def _extract_json(content: str) -> str:
    """Safely extract the first JSON object from an LLM response."""
    match = re.search(r'\{.*\}', content, re.DOTALL)
    return match.group(0) if match else content

#fraud screening new parameters
def _get_latest_document_insights(claim_id: str):

    conn = get_db_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT insights
            FROM documents
            WHERE claim_number = %s
              AND insights IS NOT NULL
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            (claim_id,)
        )

        row = cur.fetchone()

        if not row:
            return None

        insights = row["insights"]

        if isinstance(insights, str):
            try:
                insights = json.loads(insights)
            except Exception:
                return None

        return insights

    finally:
        conn.close()

def _get_latest_drone_summary(claim_id: str):

    conn = get_db_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM drone_evidence_summary
            WHERE claim_id = %s
            ORDER BY drone_capture_time DESC
            LIMIT 1
            """,
            (claim_id,)
        )

        return row_to_dict(cur.fetchone())

    finally:
        conn.close()

def _get_latest_weather_alignment(claim_id: str):

    conn = get_db_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM weather_location_alignment
            WHERE claim_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (claim_id,)
        )

        return row_to_dict(cur.fetchone())

    finally:
        conn.close()

def _calculate_document_risk(insights):

    if not insights:
        return 0

    score = 0

    authenticity = str(
        insights.get("authenticity_verdict", "")
    ).lower()

    if authenticity == "suspicious":
        score += 30

    ai_indicators = insights.get(
        "ai_generation_indicators",
        []
    )

    score += min(len(ai_indicators) * 10, 25)

    tampering = insights.get(
        "tampering_indicators",
        []
    )

    score += min(len(tampering) * 10, 25)

    consistency = str(
        insights.get(
            "damage_claim_consistency",
            ""
        )
    ).lower()

    if consistency == "inconsistent":
        score += 25

    staging = str(
        insights.get(
            "staging_risk",
            ""
        )
    ).lower()

    if staging == "medium":
        score += 10

    elif staging == "high":
        score += 20

    overall = str(
        insights.get(
            "overall_risk_level",
            ""
        )
    ).lower()

    if overall == "medium":
        score += 10

    elif overall == "high":
        score += 20

    elif overall == "critical":
        score += 30

    return min(score, 100)

def _calculate_drone_risk(drone):

    if not drone:
        return 0

    score = 0

    manipulation = str(
        drone.get(
            "manipulation_flags",
            ""
        )
    ).lower()

    if (
        "detected" in manipulation
        and "none" not in manipulation
    ):
        score += 40

    damage_match = int(
        drone.get(
            "damage_match_percent",
            0
        ) or 0
    )

    if damage_match < 70:
        score += 25

    elif damage_match < 80:
        score += 15

    notes = str(
        drone.get(
            "drone_notes",
            ""
        )
    ).lower()

    suspicious_patterns = [
        "does not align",
        "inconsistent",
        "discrepancy",
        "claim inflation",
        "limited exterior damage",
        "not support"
    ]

    if any(
        pattern in notes
        for pattern in suspicious_patterns
    ):
        score += 20

    return min(score, 100)

def _calculate_weather_risk(weather):

    if not weather:
        return 0

    alignment = str(
        weather.get(
            "drone_weather_alignment",
            ""
        )
    ).lower()

    if alignment == "aligned":
        return 0

    if alignment == "partial":
        return 50

    if alignment == "not aligned":
        return 100

    return 0


# def run_fraud_screening(claim_id: str) -> dict:
#     claim_id = claim_id.strip().upper()
#     claim = _get_claim(claim_id)
#     if not claim:
#         raise ValueError(f"Claim {claim_id} not found")

#     log.info("Running fraud screening for claim %s: %s", claim_id, {
#         k: claim.get(k) for k in ("loss_type", "severity", "estimated_cost", "date_of_loss")
#     })

#     llm = _get_llm()
#     prompt = f"""
# You are a fraud-screening assistant for an insurance claims adjuster.
# Given the claim details below, identify 1-3 potential fraud indicators.
# Always identify at least 1-2 indicators, even if they are weak or low-risk.
# For each indicator provide: "indicator" (short name), "value" (brief
# supporting detail/observation), and "risk_score" (0-100, how suspicious
# this indicator is). Low-risk indicators should have risk_score in the 10-30 range.

# Claim details:
#   loss_type: {claim.get('loss_type')}
#   short_description: {claim.get('short_description')}
#   severity: {claim.get('severity')}
#   estimated_cost: {claim.get('estimated_cost')}
#   date_of_loss: {claim.get('date_of_loss')}

# Respond with ONLY a JSON object: {{"indicators": [{{"indicator": "...", "value": "...", "risk_score": 0}}, ...]}}
# """
#     response = llm.invoke(prompt)
#     content = response.content.strip()
#     content = _extract_json(content)
#     try:
#         parsed = json.loads(content)
#         indicators = parsed.get("indicators", [])
#     except Exception:
#         log.warning("Could not parse LLM JSON response for claim %s — raw: %s", claim_id, content)
#         indicators = []

#     signals = []
#     flags = []
#     for ind in indicators[:3]:
#         indicator = ind.get("indicator", "Unknown")
#         value = ind.get("value")
#         risk_score = int(ind.get("risk_score", 0))
#         signals.append(write_ai_fraud_signal(claim_id, risk_score, indicator, value))
#         # Lower threshold to 40 so moderate-risk signals also create flags
#         if risk_score >= 40:
#             flags.append(write_fraud_flag(
#                 claim_id, indicator, value or indicator, risk_score, "FraudScreeningAgent",
#             ))

#     if signals:
#         # Average score is more representative than max alone
#         fraud_score = int(sum(s["fraud_score"] for s in signals) / len(signals))
#     else:
#         fraud_score = 0

#     snapshot = write_fraud_risk_snapshot(
#         claim_id, fraud_score, red_flag_count=len(flags), prior_claims="Low", vendor_risk="Low",
#     )

#     return {
#         "claim_id": claim_id,
#         "ai_fraud_signals": signals,
#         "fraud_flags": flags,
#         "fraud_risk_snapshot": snapshot,
#         "fraud_score": fraud_score,
#     }


def run_fraud_screening(claim_id: str) -> dict:

    claim_id = claim_id.strip().upper()

    claim = _get_claim(claim_id)

    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    log.info(
        "Running fraud screening for claim %s: %s",
        claim_id,
        {
            k: claim.get(k)
            for k in (
                "loss_type",
                "severity",
                "estimated_cost",
                "date_of_loss",
            )
        },
    )

    llm = _get_llm()

    prompt = f"""
You are a fraud-screening assistant for an insurance claims adjuster.

Given the claim details below, identify 1-3 potential fraud indicators.

Always identify at least 1-2 indicators, even if they are weak or low-risk.

For each indicator provide:

- indicator
- value
- risk_score (0-100)

Claim details:

loss_type: {claim.get('loss_type')}
short_description: {claim.get('short_description')}
severity: {claim.get('severity')}
estimated_cost: {claim.get('estimated_cost')}
date_of_loss: {claim.get('date_of_loss')}

Respond ONLY with JSON:

{{
  "indicators": [
    {{
      "indicator": "...",
      "value": "...",
      "risk_score": 0
    }}
  ]
}}
"""

    response = llm.invoke(prompt)

    content = response.content.strip()

    content = _extract_json(content)

    try:

        parsed = json.loads(content)

        indicators = parsed.get(
            "indicators",
            []
        )

    except Exception:

        log.warning(
            "Could not parse LLM JSON response for claim %s — raw: %s",
            claim_id,
            content,
        )

        indicators = []

    signals = []
    flags = []

    #
    # STORE AI FRAUD SIGNALS
    #
    for ind in indicators[:3]:

        indicator = ind.get(
            "indicator",
            "Unknown"
        )

        value = ind.get("value")

        risk_score = int(
            ind.get(
                "risk_score",
                0
            )
        )

        signals.append(
            write_ai_fraud_signal(
                claim_id,
                risk_score,
                indicator,
                value,
            )
        )

        if risk_score >= 40:

            flags.append(
                write_fraud_flag(
                    claim_id,
                    indicator,
                    value or indicator,
                    risk_score,
                    "FraudScreeningAgent",
                )
            )

    #
    # AI SCORE
    #
    ai_score = (
        int(
            sum(
                s["fraud_score"]
                for s in signals
            )
            / len(signals)
        )
        if signals
        else 0
    )

    document_score = 0
    drone_score = 0
    weather_score = 0

    contributors = []

    loss_type = str(
        claim.get(
            "loss_type",
            ""
        )
    ).strip().lower()

    #
    # DOCUMENT-BASED CLAIMS
    #
    if loss_type in DOCUMENT_LOSS_TYPES:

        insights = _get_latest_document_insights(
            claim_id
        )

        document_score = (
            _calculate_document_risk(
                insights
            )
        )

        if document_score >= 50:

            contributors.append(
                "Document authenticity concerns"
            )

        if document_score >= 70:

            flags.append(
                write_fraud_flag(
                    claim_id,
                    "Document Fraud Risk",
                    "Suspicious or inconsistent evidence detected",
                    document_score,
                    "FraudScreeningAgent",
                )
            )

    #
    # DRONE / WEATHER CLAIMS
    #
    if loss_type in DRONE_LOSS_TYPES:

        drone = _get_latest_drone_summary(
            claim_id
        )

        weather = _get_latest_weather_alignment(
            claim_id
        )

        drone_score = (
            _calculate_drone_risk(
                drone
            )
        )

        weather_score = (
            _calculate_weather_risk(
                weather
            )
        )

        if drone_score >= 50:

            contributors.append(
                "Drone evidence discrepancy"
            )

            flags.append(
                write_fraud_flag(
                    claim_id,
                    "Drone Evidence Mismatch",
                    "Drone assessment indicates discrepancy with claim",
                    drone_score,
                    "FraudScreeningAgent",
                )
            )

        if weather_score >= 50:

            contributors.append(
                "Weather alignment mismatch"
            )

            flags.append(
                write_fraud_flag(
                    claim_id,
                    "Weather Mismatch",
                    "Weather conditions do not align with reported loss",
                    weather_score,
                    "FraudScreeningAgent",
                )
            )

    #
    # FINAL WEIGHTED FRAUD SCORE
    #
    fraud_score = round(
        (
            ai_score * 0.30
            + document_score * 0.40
            + drone_score * 0.20
            + weather_score * 0.10
        )
    )

    fraud_score = min(
        100,
        fraud_score
    )

    #
    # SNAPSHOT
    #
    snapshot = write_fraud_risk_snapshot(
        claim_id,
        fraud_score,
        red_flag_count=len(flags),
        prior_claims="Low",
        vendor_risk="Low",
    )

    return {
        "claim_id": claim_id,
        "ai_fraud_signals": signals,
        "fraud_flags": flags,
        "fraud_risk_snapshot": snapshot,
        "fraud_score": fraud_score,
        "ai_score": ai_score,
        "document_score": document_score,
        "drone_score": drone_score,
        "weather_score": weather_score,
        "contributors": contributors,
    }