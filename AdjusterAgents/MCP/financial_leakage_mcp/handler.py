# # """
# # handler.py — Financial Leakage
# # ────────────────────────────────
# # Detects overpayments and billing anomalies by aggregating cost variance
# # across all vendor line items on a claim and computing a leakage risk score.
# # """

# # import json
# # import logging
# # import os
# # import re
# # import sys

# # sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

# # from db import get_db_connection, row_to_dict  # noqa: E402
# # from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

# # log = logging.getLogger(__name__)


# # def _get_llm():
# #     return AzureChatOpenAI(
# #         api_key=os.getenv("AZURE_OPENAI_API_KEY"),
# #         api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
# #         azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
# #         azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
# #     )


# # def get_cost_variance(vendor_id: str) -> list:
# #     conn = get_db_connection()
# #     try:
# #         cur = conn.cursor()
# #         cur.execute(
# #             "SELECT * FROM cost_variance_output WHERE vendor_id = %s ORDER BY id DESC",
# #             (vendor_id,),
# #         )
# #         return row_to_dict(cur.fetchall())
# #     finally:
# #         conn.close()


# # def _get_vendor_cost_inputs(claim_id: str) -> list:
# #     conn = get_db_connection()
# #     try:
# #         cur = conn.cursor()
# #         cur.execute("SELECT * FROM vendor_cost_input WHERE claim_id = %s", (claim_id,))
# #         return row_to_dict(cur.fetchall())
# #     finally:
# #         conn.close()


# # def _extract_json(content: str) -> str:
# #     """Safely extract the first JSON object from an LLM response."""
# #     match = re.search(r'\{.*\}', content, re.DOTALL)
# #     return match.group(0) if match else content


# # def score_leakage(claim_id: str) -> dict:
# #     """
# #     Aggregates cost variance data for all vendors on a claim, computes an
# #     overall leakage risk score (0-100), and uses an LLM to flag specific
# #     overpayment risks with recommended actions.
# #     """
# #     cost_inputs = _get_vendor_cost_inputs(claim_id)

# #     if not cost_inputs:
# #         log.warning("No vendor cost data found for claim %s", claim_id)
# #         return {
# #             "claim_id": claim_id,
# #             "message": f"No vendor cost data found for claim {claim_id}. Cannot compute leakage score.",
# #             "total_estimated_cost": 0,
# #             "total_actual_cost": 0,
# #             "overall_variance_percent": 0.0,
# #             "leakage_score": 0,
# #             "leakage_risk": "Unknown",
# #             "risk_flags": [],
# #             "recommendation": "Ensure vendor cost records are submitted before running leakage analysis.",
# #             "vendor_variance_records": [],
# #         }

# #     total_estimated = sum(float(c.get("estimated_cost") or 0) for c in cost_inputs)
# #     total_actual = sum(float(c.get("actual_cost") or 0) for c in cost_inputs)

# #     # Normalize vendor_id casing to avoid missed lookups (e.g. "v1" vs "V1")
# #     vendor_ids = list({str(c.get("vendor_id", "")).strip().upper() for c in cost_inputs if c.get("vendor_id")})
# #     variance_records = []
# #     for vid in vendor_ids:
# #         variance_records.extend(get_cost_variance(vid))

# #     overall_variance_pct = round(
# #         (total_actual - total_estimated) / total_estimated * 100, 1
# #     ) if total_estimated > 0 else 0.0

# #     leakage_score = min(int(max(overall_variance_pct, 0) * 2), 100)

# #     log.info("Leakage calc for %s: estimated=%.2f actual=%.2f variance=%.1f%% score=%d",
# #              claim_id, total_estimated, total_actual, overall_variance_pct, leakage_score)

# #     llm = _get_llm()
# #     prompt = f"""
# # You are an insurance financial leakage analyst. Review the cost data below
# # for claim {claim_id} and identify specific overpayment risks.

# #   total_estimated_cost: {total_estimated}
# #   total_actual_cost: {total_actual}
# #   overall_variance_percent: {overall_variance_pct}%
# #   leakage_score: {leakage_score}/100

# # Vendor cost inputs:
# # {json.dumps(cost_inputs, default=str, indent=2)}

# # Vendor variance records:
# # {json.dumps(variance_records, default=str, indent=2)}

# # Provide:
# # - "risk_flags": list of specific overpayment concerns (each: vendor_id, issue, severity)
# # - "leakage_risk": "Low" | "Medium" | "High" | "Critical"
# # - "recommendation": one sentence on next steps

# # Respond with ONLY a JSON object with keys: risk_flags, leakage_risk, recommendation. No other text.
# # """
# #     response = llm.invoke(prompt)
# #     content = _extract_json(response.content.strip())
# #     try:
# #         parsed = json.loads(content)
# #     except Exception:
# #         log.warning("Could not parse LLM JSON for claim %s — raw: %s", claim_id, response.content.strip())
# #         risk = "High" if leakage_score >= 60 else "Medium" if leakage_score >= 30 else "Low"
# #         parsed = {"risk_flags": [], "leakage_risk": risk, "recommendation": "Review vendor invoices against estimates."}

# #     leakage_risk = parsed.get("leakage_risk", "Low")
# #     risk_flags = parsed.get("risk_flags", [])
# #     recommendation = parsed.get("recommendation", "")

# #     conn = get_db_connection()
# #     try:
# #         cur = conn.cursor()
# #         cur.execute(
# #             """
# #             INSERT INTO financial_leakage_outputs (
# #                 claim_id, total_estimated_cost, total_actual_cost, overall_variance_percent,
# #                 leakage_score, leakage_risk, risk_flags, recommendation
# #             ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
# #             """,
# #             (
# #                 claim_id,
# #                 total_estimated,
# #                 total_actual,
# #                 overall_variance_pct,
# #                 leakage_score,
# #                 leakage_risk,
# #                 json.dumps(risk_flags),
# #                 recommendation,
# #             ),
# #         )
# #         conn.commit()
# #     except Exception:
# #         conn.rollback()
# #         log.exception("Could not persist financial_leakage_outputs for claim %s", claim_id)
# #     finally:
# #         conn.close()

# #     return {
# #         "claim_id": claim_id,
# #         "total_estimated_cost": total_estimated,
# #         "total_actual_cost": total_actual,
# #         "overall_variance_percent": overall_variance_pct,
# #         "leakage_score": leakage_score,
# #         "leakage_risk": leakage_risk,
# #         "risk_flags": risk_flags,
# #         "recommendation": recommendation,
# #         "vendor_variance_records": variance_records,
# #     }



# # new code with adjuster input also 
# """
# handler.py — Financial Leakage
# ────────────────────────────────
# Detects overpayments and billing anomalies by aggregating cost variance
# across all vendor line items on a claim and computing a leakage risk score.
# """

# import json
# import logging
# import os
# import re
# import sys

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


# def get_cost_variance(vendor_id: str) -> list:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM cost_variance_output WHERE vendor_id = %s ORDER BY id DESC",
#             (vendor_id,),
#         )
#         return row_to_dict(cur.fetchall())
#     finally:
#         conn.close()

# #adding for new code for financial leakage score calculation
# def get_financial_leakage_score(claim_id: str):
#     conn = get_db_connection()

#     try:
#         cur = conn.cursor()

#         cur.execute(
#             """
#             SELECT *
#             FROM Financial_Leakage_Score
#             WHERE claim_id = %s
#             """,
#             (claim_id,),
#         )

#         rows = row_to_dict(cur.fetchall())

#         return rows[0] if rows else None

#     finally:
#         conn.close()

# def update_adjuster_override(
#     claim_id: str,
#     adjuster_override_risk_level: str,
#     adjuster_notes: str,
# ):
#     """
#     Save adjuster's override decision and notes.
#     """

#     conn = get_db_connection()

#     try:
#         cur = conn.cursor()

#         cur.execute(
#             """
#             UPDATE Financial_Leakage_Score
#             SET
#                 adjuster_override_risk_level = %s,
#                 adjuster_notes = %s,
#                 final_risk_level = %s,
#                 updated_at = CURRENT_TIMESTAMP
#             WHERE claim_id = %s
#             RETURNING *
#             """,
#             (
#                 adjuster_override_risk_level,
#                 adjuster_notes,
#                 adjuster_override_risk_level,
#                 claim_id,
#             ),
#         )

#         row = cur.fetchone()

#         if not row:
#             raise ValueError(
#                 f"No financial leakage score found for claim {claim_id}"
#             )

#         conn.commit()

#         return row_to_dict([row])[0]

#     except Exception:
#         conn.rollback()
#         raise

#     finally:
#         conn.close()


# def _get_vendor_cost_inputs(claim_id: str) -> list:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM vendor_cost_input WHERE claim_id = %s", (claim_id,))
#         return row_to_dict(cur.fetchall())
#     finally:
#         conn.close()


# def _extract_json(content: str) -> str:
#     """Safely extract the first JSON object from an LLM response."""
#     match = re.search(r'\{.*\}', content, re.DOTALL)
#     return match.group(0) if match else content


# # adding the db table for finanical Leakage score
# def save_financial_leakage_score(result: dict):
#     """
#     Insert or update Financial_Leakage_Score record.
#     """

#     conn = get_db_connection()

#     try:
#         cur = conn.cursor()

#         cur.execute(
#             """
#             INSERT INTO Financial_Leakage_Score (
#                 claim_id,
#                 total_estimated_cost,
#                 total_actual_cost,
#                 overall_variance_percent,
#                 leakage_score,
#                 leakage_risk,
#                 risk_flags,
#                 recommendation,
#                 vendor_variance_records,
#                 adjuster_override_risk_level,
#                 adjuster_notes,
#                 final_risk_level,
#                 updated_at
#             )
#             VALUES (
#                 %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP
#             )
#             ON CONFLICT (claim_id)
#             DO UPDATE SET
#                 total_estimated_cost = EXCLUDED.total_estimated_cost,
#                 total_actual_cost = EXCLUDED.total_actual_cost,
#                 overall_variance_percent = EXCLUDED.overall_variance_percent,
#                 leakage_score = EXCLUDED.leakage_score,
#                 leakage_risk = EXCLUDED.leakage_risk,
#                 risk_flags = EXCLUDED.risk_flags,
#                 recommendation = EXCLUDED.recommendation,
#                 vendor_variance_records = EXCLUDED.vendor_variance_records,
#                 final_risk_level = CASE
#                     WHEN Financial_Leakage_Score.adjuster_override_risk_level IS NOT NULL
#                     THEN Financial_Leakage_Score.adjuster_override_risk_level
#                     ELSE EXCLUDED.leakage_risk
#                 END,
#                 updated_at = CURRENT_TIMESTAMP
#             """,
#             (
#                 result["claim_id"],
#                 result["total_estimated_cost"],
#                 result["total_actual_cost"],
#                 result["overall_variance_percent"],
#                 result["leakage_score"],
#                 result["leakage_risk"],
#                 json.dumps(result["risk_flags"]),
#                 result["recommendation"],
#                 json.dumps(result["vendor_variance_records"]),
#                 result.get("adjuster_override_risk_level"),
#                 result.get("adjuster_notes"),
#                 result["final_risk_level"],
#             ),
#         )

#         conn.commit()

#     except Exception:
#         conn.rollback()
#         raise

#     finally:
#         conn.close()


# def score_leakage(claim_id: str) -> dict:
#     """
#     Aggregates cost variance data for all vendors on a claim, computes an
#     overall leakage risk score (0-100), and uses an LLM to flag specific
#     overpayment risks with recommended actions.
#     """
#     cost_inputs = _get_vendor_cost_inputs(claim_id)

#     # if not cost_inputs:
#     #     log.warning("No vendor cost data found for claim %s", claim_id)
#     #     return {
#     #         "claim_id": claim_id,
#     #         "message": f"No vendor cost data found for claim {claim_id}. Cannot compute leakage score.",
#     #         "total_estimated_cost": 0,
#     #         "total_actual_cost": 0,
#     #         "overall_variance_percent": 0.0,
#     #         "leakage_score": 0,
#     #         "leakage_risk": "Unknown",
#     #         "risk_flags": [],
#     #         "recommendation": "Ensure vendor cost records are submitted before running leakage analysis.",
#     #         "vendor_variance_records": [],
#     #     }

#     #Adding codes for financial leakage score calculation
#     if not cost_inputs:
#         log.warning("No vendor cost data found for claim %s", claim_id)

#         result = {
#             "claim_id": claim_id,
#             "message": f"No vendor cost data found for claim {claim_id}. Cannot compute leakage score.",
#             "total_estimated_cost": 0,
#             "total_actual_cost": 0,
#             "overall_variance_percent": 0.0,
#             "leakage_score": 0,
#             "leakage_risk": "Unknown",
#             "risk_flags": [],
#             "recommendation": "Ensure vendor cost records are submitted before running leakage analysis.",
#             "vendor_variance_records": [],
#             "adjuster_override_risk_level": None,
#             "adjuster_notes": None,
#             "final_risk_level": "Unknown",
#         }
#         save_financial_leakage_score(result)
#         return result


#     total_estimated = sum(float(c.get("estimated_cost") or 0) for c in cost_inputs)
#     total_actual = sum(float(c.get("actual_cost") or 0) for c in cost_inputs)

#     # Normalize vendor_id casing to avoid missed lookups (e.g. "v1" vs "V1")
#     vendor_ids = list({str(c.get("vendor_id", "")).strip().upper() for c in cost_inputs if c.get("vendor_id")})
#     variance_records = []
#     for vid in vendor_ids:
#         variance_records.extend(get_cost_variance(vid))

#     overall_variance_pct = round(
#         (total_actual - total_estimated) / total_estimated * 100, 1
#     ) if total_estimated > 0 else 0.0

#     leakage_score = min(int(max(overall_variance_pct, 0) * 2), 100)

#     log.info("Leakage calc for %s: estimated=%.2f actual=%.2f variance=%.1f%% score=%d",
#              claim_id, total_estimated, total_actual, overall_variance_pct, leakage_score)

#     llm = _get_llm()
#     prompt = f"""
# You are an insurance financial leakage analyst. Review the cost data below
# for claim {claim_id} and identify specific overpayment risks.

#   total_estimated_cost: {total_estimated}
#   total_actual_cost: {total_actual}
#   overall_variance_percent: {overall_variance_pct}%
#   leakage_score: {leakage_score}/100

# Vendor cost inputs:
# {json.dumps(cost_inputs, default=str, indent=2)}

# Vendor variance records:
# {json.dumps(variance_records, default=str, indent=2)}

# Provide:
# - "risk_flags": list of specific overpayment concerns (each: vendor_id, issue, severity)
# - "leakage_risk": "Low" | "Medium" | "High" | "Critical"
# - "recommendation": one sentence on next steps

# Respond with ONLY a JSON object with keys: risk_flags, leakage_risk, recommendation. No other text.
# """
#     response = llm.invoke(prompt)
#     content = _extract_json(response.content.strip())
#     try:
#         parsed = json.loads(content)
#     except Exception:
#         log.warning("Could not parse LLM JSON for claim %s — raw: %s", claim_id, response.content.strip())
#         risk = "High" if leakage_score >= 60 else "Medium" if leakage_score >= 30 else "Low"
#         parsed = {"risk_flags": [], "leakage_risk": risk, "recommendation": "Review vendor invoices against estimates."}

#     # return {
#     #     "claim_id": claim_id,
#     #     "total_estimated_cost": total_estimated,
#     #     "total_actual_cost": total_actual,
#     #     "overall_variance_percent": overall_variance_pct,
#     #     "leakage_score": leakage_score,
#     #     "leakage_risk": parsed.get("leakage_risk", "Low"),
#     #     "risk_flags": parsed.get("risk_flags", []),
#     #     "recommendation": parsed.get("recommendation", ""),
#     #     "vendor_variance_records": variance_records,
#     # }

#     ai_risk = parsed.get("leakage_risk", "Low")

#     result = {
#         "claim_id": claim_id,
#         "total_estimated_cost": total_estimated,
#         "total_actual_cost": total_actual,
#         "overall_variance_percent": overall_variance_pct,
#         "leakage_score": leakage_score,
#         "leakage_risk": ai_risk,
#         "risk_flags": parsed.get("risk_flags", []),
#         "recommendation": parsed.get("recommendation", ""),
#         "vendor_variance_records": variance_records,
#         "adjuster_override_risk_level": None,
#         "adjuster_notes": None,
#         "final_risk_level": ai_risk,
#     }
#     save_financial_leakage_score(result)
#     return result



"""
handler.py — Financial Leakage
────────────────────────────────
Detects overpayments and billing anomalies by aggregating cost variance
across all vendor line items on a claim and computing a leakage risk score.
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


def _get_llm():
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def get_cost_variance(vendor_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM cost_variance_output WHERE vendor_id = %s ORDER BY id DESC",
            (vendor_id,),
        )
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()

#adding for new code for financial leakage score calculation
def get_financial_leakage_score(claim_id: str):
    conn = get_db_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM Financial_Leakage_Score
            WHERE claim_id = %s
            """,
            (claim_id,),
        )

        rows = row_to_dict(cur.fetchall())

        return rows[0] if rows else None

    finally:
        conn.close()

def get_claim_estimated_cost(claim_id: str):
    conn = get_db_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT estimated_cost
            FROM claims
            WHERE claim_number = %s
            """,
            (claim_id,),
        )

        row = row_to_dict(cur.fetchone())

        if not row:
            return 0.0

        return float(row.get("estimated_cost") or 0)

    finally:
        conn.close()



def update_adjuster_override(
    claim_id: str,
    adjuster_override_risk_level: str,
    adjuster_notes: str,
):
    """
    Save adjuster's override decision and notes.
    """

    conn = get_db_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE Financial_Leakage_Score
            SET
                adjuster_override_risk_level = %s,
                adjuster_notes = %s,
                final_risk_level = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE claim_id = %s
            RETURNING *
            """,
            (
                adjuster_override_risk_level,
                adjuster_notes,
                adjuster_override_risk_level,
                claim_id,
            ),
        )

        row = cur.fetchone()

        if not row:
            raise ValueError(
                f"No financial leakage score found for claim {claim_id}"
            )

        conn.commit()

        return row_to_dict([row])[0]

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def _get_claim_id(claim_number: str) -> Optional[int]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM claims WHERE claim_number = %s", (claim_number,))
        row = row_to_dict(cur.fetchone())
        return row.get("id") if row else None
    finally:
        conn.close()


def _get_repair_vs_replace_decision(claim_number: str) -> Optional[str]:
    """
    Effective Repair/Replace call for this claim: prefers the adjuster's own
    finalized `decision`, falling back to the AI's `recommended_action` if the
    adjuster hasn't finalized one yet (decision is still the "Adjuster
    review" placeholder written at analysis time) — same precedence
    adjuster.ts's effectiveRepairVsReplace() uses for this same table.
    Returns None if no repair-vs-replace analysis has run for this claim yet.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT decision, recommended_action FROM repair_vs_replacement_decisions "
            "WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        row = row_to_dict(cur.fetchone())
    finally:
        conn.close()
    if not row:
        return None
    for candidate in (row.get("decision"), row.get("recommended_action")):
        normalized = str(candidate or "").strip().capitalize()
        if normalized in ("Repair", "Replace"):
            return normalized
    return None


def _get_damaged_item_costs(claim_number: str, effective_decision: str) -> list:
    """
    Per-item cost detail from whichever table matches the claim's effective
    Repair vs Replace decision — repair_costs.total_repair_estimate for
    "Repair", replacement_costs.total_replacement_estimate for "Replace".
    Both tables are populated by RepairVsReplacementAgent (compare_repair_vs_replace
    → write_repair_cost/write_replacement_cost), keyed by the numeric claims.id
    (not the claim_number text used everywhere else in this file).
    """
    claim_id = _get_claim_id(claim_number)
    if claim_id is None:
        return []

    table, cost_column = (
        ("repair_costs", "total_repair_estimate") if effective_decision == "Repair"
        else ("replacement_costs", "total_replacement_estimate")
    )
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT item_type, {cost_column} AS cost FROM {table} WHERE claim_id = %s", (claim_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def _extract_json(content: str) -> str:
    """Safely extract the first JSON object from an LLM response."""
    match = re.search(r'\{.*\}', content, re.DOTALL)
    return match.group(0) if match else content


# adding the db table for finanical Leakage score
def save_financial_leakage_score(result: dict):
    """
    Insert or update Financial_Leakage_Score record.
    """

    conn = get_db_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO Financial_Leakage_Score (
                claim_id,
                total_estimated_cost,
                total_actual_cost,
                overall_variance_percent,
                leakage_score,
                leakage_risk,
                risk_flags,
                recommendation,
                vendor_variance_records,
                adjuster_override_risk_level,
                adjuster_notes,
                final_risk_level,
                updated_at
            )
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP
            )
            ON CONFLICT (claim_id)
            DO UPDATE SET
                total_estimated_cost = EXCLUDED.total_estimated_cost,
                total_actual_cost = EXCLUDED.total_actual_cost,
                overall_variance_percent = EXCLUDED.overall_variance_percent,
                leakage_score = EXCLUDED.leakage_score,
                leakage_risk = EXCLUDED.leakage_risk,
                risk_flags = EXCLUDED.risk_flags,
                recommendation = EXCLUDED.recommendation,
                vendor_variance_records = EXCLUDED.vendor_variance_records,
                final_risk_level = CASE
                    WHEN Financial_Leakage_Score.adjuster_override_risk_level IS NOT NULL
                    THEN Financial_Leakage_Score.adjuster_override_risk_level
                    ELSE EXCLUDED.leakage_risk
                END,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                result["claim_id"],
                result["total_estimated_cost"],
                result["total_actual_cost"],
                result["overall_variance_percent"],
                result["leakage_score"],
                result["leakage_risk"],
                json.dumps(result["risk_flags"]),
                result["recommendation"],
                json.dumps(result["vendor_variance_records"]),
                result.get("adjuster_override_risk_level"),
                result.get("adjuster_notes"),
                result["final_risk_level"],
            ),
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def score_leakage(claim_id: str) -> dict:
    """
    Computes an overall leakage risk score (0-100) by comparing the FNOL
    estimated cost (claims.estimated_cost) against the real aggregate cost of
    the damaged items — repair_costs.total_repair_estimate or
    replacement_costs.total_replacement_estimate, whichever table matches the
    claim's effective Repair vs Replace decision (the adjuster's own
    finalized decision, or the AI's recommendation if the adjuster hasn't
    decided yet). Uses an LLM to flag specific overpayment risks.

    2026-07-23: replaced the earlier vendor_cost_input-based calculation —
    that table is only ever populated by a one-off seed script for a handful
    of old test claims (CLM-2026-1001/1002/1003/1159), with no real pipeline
    feeding it for live claims, so it produced "Unknown"/$0 for every other
    claim. repair_costs/replacement_costs are populated by
    RepairVsReplacementAgent, which now reliably runs for every real claim
    (see the AdjusterOrchestrator Phase B halt-timing fix the same day).
    """
    effective_decision = _get_repair_vs_replace_decision(claim_id)
    if not effective_decision:
        log.warning("No Repair vs Replace decision found for claim %s", claim_id)
        result = {
            "claim_id": claim_id,
            "message": f"No Repair vs Replace analysis found for claim {claim_id} yet — run that before financial leakage.",
            "total_estimated_cost": 0,
            "total_actual_cost": 0,
            "overall_variance_percent": 0.0,
            "leakage_score": 0,
            "leakage_risk": "Unknown",
            "risk_flags": [],
            "recommendation": "Run the Repair vs Replace analysis for this claim before running financial leakage.",
            "vendor_variance_records": [],
            "adjuster_override_risk_level": None,
            "adjuster_notes": None,
            "final_risk_level": "Unknown",
        }
        save_financial_leakage_score(result)
        return result

    item_costs = _get_damaged_item_costs(claim_id, effective_decision)
    if not item_costs:
        log.warning("No %s cost detail found for claim %s", effective_decision.lower(), claim_id)
        result = {
            "claim_id": claim_id,
            "message": (
                f"Repair vs Replace decided '{effective_decision}' for claim {claim_id}, "
                f"but no {effective_decision.lower()} cost detail has been computed yet."
            ),
            "total_estimated_cost": 0,
            "total_actual_cost": 0,
            "overall_variance_percent": 0.0,
            "leakage_score": 0,
            "leakage_risk": "Unknown",
            "risk_flags": [],
            "recommendation": f"Ensure {effective_decision.lower()} cost detail is computed before running leakage analysis.",
            "vendor_variance_records": [],
            "adjuster_override_risk_level": None,
            "adjuster_notes": None,
            "final_risk_level": "Unknown",
        }
        save_financial_leakage_score(result)
        return result

    total_actual = sum(float(item.get("cost") or 0) for item in item_costs)

    total_estimated = get_claim_estimated_cost(claim_id)
    if total_estimated <= 0:
        log.warning(
            "No estimated cost found in claims table for claim %s",
            claim_id,
        )

    overall_variance_pct = round(
        (total_actual - total_estimated) / total_estimated * 100, 1
    ) if total_estimated > 0 else 0.0

    leakage_score = min(int(max(overall_variance_pct, 0) * 2), 100)

    log.info(
        "Leakage calc for %s: decision=%s estimated=%.2f actual=%.2f variance=%.1f%% score=%d",
        claim_id, effective_decision, total_estimated, total_actual, overall_variance_pct, leakage_score,
    )

    llm = _get_llm()
    prompt = f"""
You are an insurance financial leakage analyst. Review the cost data below
for claim {claim_id} and identify specific overpayment risks.

  repair_vs_replace_decision: {effective_decision}
  total_estimated_cost (FNOL): {total_estimated}
  total_actual_cost ({effective_decision.lower()} estimate total): {total_actual}
  overall_variance_percent: {overall_variance_pct}%
  leakage_score: {leakage_score}/100

Per-item {effective_decision.lower()} cost detail:
{json.dumps(item_costs, default=str, indent=2)}

Provide:
- "risk_flags": list of specific overpayment concerns (each: item_type, issue, severity)
- "leakage_risk": "Low" | "Medium" | "High" | "Critical"
- "recommendation": one sentence on next steps

Respond with ONLY a JSON object with keys: risk_flags, leakage_risk, recommendation. No other text.
"""
    response = llm.invoke(prompt)
    content = _extract_json(response.content.strip())
    try:
        parsed = json.loads(content)
    except Exception:
        log.warning("Could not parse LLM JSON for claim %s — raw: %s", claim_id, response.content.strip())
        risk = "High" if leakage_score >= 60 else "Medium" if leakage_score >= 30 else "Low"
        parsed = {"risk_flags": [], "leakage_risk": risk, "recommendation": "Review repair/replacement cost detail against the FNOL estimate."}

    ai_risk = parsed.get("leakage_risk", "Low")

    result = {
        "claim_id": claim_id,
        "total_estimated_cost": total_estimated,
        "total_actual_cost": total_actual,
        "overall_variance_percent": overall_variance_pct,
        "leakage_score": leakage_score,
        "leakage_risk": ai_risk,
        "risk_flags": parsed.get("risk_flags", []),
        "recommendation": parsed.get("recommendation", ""),
        "vendor_variance_records": item_costs,
        "adjuster_override_risk_level": None,
        "adjuster_notes": None,
        "final_risk_level": ai_risk,
    }
    save_financial_leakage_score(result)
    return result
