# """
# handler.py — Reserve Recommendation
# ──────────────────────────────────────
# Calculates a recommended financial reserve by combining loss_assessments,
# fraud_risk_score, and claim severity. Compares the recommendation against
# the adjuster's manually set adjusted_reserve.
# """

# import json
# import logging
# import os
# import sys
# from typing import Optional

# sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

# from db import get_db_connection, row_to_dict  # noqa: E402
# from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

# log = logging.getLogger(__name__)

# _SEVERITY_BUFFER = {"Critical": 0.30, "High": 0.20, "Medium": 0.10, "Low": 0.05}


# def _get_llm():
#     return AzureChatOpenAI(
#         api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#         api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
#         azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
#         azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     )


# def get_adjuster_findings(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM adjuster_findings WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
#             (claim_id,),
#         )
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def _get_claim(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_id,))
#         row = cur.fetchone()
#         if row:
#             return row_to_dict(row)
#         if claim_id.isdigit():
#             cur.execute("SELECT * FROM claims WHERE id = %s", (int(claim_id),))
#             return row_to_dict(cur.fetchone())
#         return None
#     finally:
#         conn.close()


# def _get_loss_assessment(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM loss_assessments WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
#             (claim_id,),
#         )
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def _get_fraud_risk(claim_id: str) -> Optional[dict]:
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


# def recommend_reserve(claim_id: str) -> dict:
#     """
#     Derives a recommended reserve from loss assessment totals, fraud risk
#     buffer, and severity adjustment. Writes the result to
#     adjuster_findings.system_recommended_reserve — never overwrites
#     adjusted_reserve, which remains the adjuster's manual value.
#     """
#     claim = _get_claim(claim_id)
#     if not claim:
#         raise ValueError(f"Claim {claim_id} not found")

#     loss_assessment = _get_loss_assessment(claim_id)
#     fraud_snapshot = _get_fraud_risk(claim_id)
#     findings = get_adjuster_findings(claim_id)

#     severity = claim.get("severity") or "Medium"
#     estimated_cost = float(claim.get("estimated_cost") or 0)

#     if loss_assessment:
#         base_loss = float(loss_assessment.get("total_parts_cost") or 0) + \
#                     float(loss_assessment.get("total_labor_cost") or 0)
#     else:
#         base_loss = estimated_cost

#     fraud_score = int(fraud_snapshot.get("fraud_score") or 0) if fraud_snapshot else 0
#     fraud_buffer_pct = min(fraud_score / 1000, 0.15)
#     severity_buffer_pct = _SEVERITY_BUFFER.get(severity, 0.10)

#     recommended_reserve = round(base_loss * (1 + severity_buffer_pct + fraud_buffer_pct), 2)

#     adjuster_reserve = float(findings.get("adjusted_reserve") or 0) if findings else 0.0
#     variance_pct = round((recommended_reserve - adjuster_reserve) / adjuster_reserve * 100, 1) if adjuster_reserve > 0 else 0.0

#     llm = _get_llm()
#     prompt = f"""
# You are an insurance reserve specialist. Write a one-sentence rationale
# explaining the recommended reserve calculation.

#   severity: {severity}
#   base_loss_estimate: {base_loss}
#   severity_buffer_percent: {severity_buffer_pct * 100}%
#   fraud_risk_score: {fraud_score}
#   fraud_buffer_percent: {fraud_buffer_pct * 100:.1f}%
#   recommended_reserve: {recommended_reserve}
#   adjuster_set_reserve: {adjuster_reserve if adjuster_reserve else 'not set'}
#   variance_percent: {variance_pct}%

# Respond with ONLY a JSON object: {{"rationale": "..."}}
# """
#     response = llm.invoke(prompt)
#     content = response.content.strip().strip("`")
#     if content.startswith("json"):
#         content = content[4:]
#     try:
#         rationale = json.loads(content).get("rationale", "")
#     except Exception:
#         rationale = f"Reserve based on {severity} severity buffer ({int(severity_buffer_pct * 100)}%) and fraud risk adjustment ({int(fraud_buffer_pct * 100)}%)."

#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         if findings:
#             cur.execute(
#                 "UPDATE adjuster_findings SET system_recommended_reserve = %s WHERE id = %s",
#                 (recommended_reserve, findings["id"]),
#             )
#         else:
#             cur.execute(
#                 "INSERT INTO adjuster_findings (claim_id, adjuster_name, fraud_risk, system_recommended_reserve) VALUES (%s, %s, %s, %s)",
#                 (claim_id, "ReserveRecommendationAgent", rationale[:100], recommended_reserve),
#             )
#         conn.commit()
#     finally:
#         conn.close()

#     return {
#         "claim_id": claim_id,
#         "system_recommended_reserve": recommended_reserve,
#         "adjuster_set_reserve": adjuster_reserve or None,
#         "variance_percent": variance_pct,
#         "severity_buffer_percent": round(severity_buffer_pct * 100, 1),
#         "fraud_buffer_percent": round(fraud_buffer_pct * 100, 1),
#         "rationale": rationale,
#     }







#the below code is before using rohans claude (17/7/26)

# """
# handler.py — Reserve Recommendation
# ──────────────────────────────────────
# Calculates a recommended financial reserve by combining loss_assessments,
# fraud_risk_score, and claim severity. Compares the recommendation against
# the adjuster's manually set adjusted_reserve.
# """

# import json
# import logging
# import os
# import sys
# from typing import Optional

# sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

# from db import get_db_connection, row_to_dict  # noqa: E402
# from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

# log = logging.getLogger(__name__)

# _SEVERITY_BUFFER = {"Critical": 0.30, "High": 0.20, "Medium": 0.10, "Low": 0.05}


# def _get_llm():
#     return AzureChatOpenAI(
#         api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#         api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
#         azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
#         azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     )


# def get_adjuster_findings(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM adjuster_findings WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
#             (claim_id,),
#         )
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def _get_claim(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_id,))
#         row = cur.fetchone()
#         if row:
#             return row_to_dict(row)
#         if claim_id.isdigit():
#             cur.execute("SELECT * FROM claims WHERE id = %s", (int(claim_id),))
#             return row_to_dict(cur.fetchone())
#         return None
#     finally:
#         conn.close()


# def _get_loss_assessment(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM loss_assessments WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
#             (claim_id,),
#         )
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def _get_fraud_risk(claim_id: str) -> Optional[dict]:
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


# def recommend_reserve(claim_id: str) -> dict:
#     """
#     Derives a recommended reserve from loss assessment totals, fraud risk
#     buffer, and severity adjustment. Writes the result to
#     adjuster_findings.system_recommended_reserve — never overwrites
#     adjusted_reserve, which remains the adjuster's manual value.
#     """
#     claim = _get_claim(claim_id)
#     if not claim:
#         raise ValueError(f"Claim {claim_id} not found")

#     loss_assessment = _get_loss_assessment(claim_id)
#     fraud_snapshot = _get_fraud_risk(claim_id)
#     findings = get_adjuster_findings(claim_id)

#     severity = claim.get("severity") or "Medium"
#     estimated_cost = float(claim.get("estimated_cost") or 0)

#     if loss_assessment:
#         base_loss = float(loss_assessment.get("total_parts_cost") or 0) + \
#                     float(loss_assessment.get("total_labor_cost") or 0)
#     else:
#         base_loss = estimated_cost

#     fraud_score = int(fraud_snapshot.get("fraud_score") or 0) if fraud_snapshot else 0
#     fraud_buffer_pct = min(fraud_score / 1000, 0.15)
#     severity_buffer_pct = _SEVERITY_BUFFER.get(severity, 0.10)

#     recommended_reserve = round(base_loss * (1 + severity_buffer_pct + fraud_buffer_pct), 2)

#     adjuster_reserve = float(findings.get("adjusted_reserve") or 0) if findings else 0.0
#     variance_pct = round((recommended_reserve - adjuster_reserve) / adjuster_reserve * 100, 1) if adjuster_reserve > 0 else 0.0

#     llm = _get_llm()
#     prompt = f"""
# You are an insurance reserve specialist. Write a one-sentence rationale
# explaining the recommended reserve calculation.

#   severity: {severity}
#   base_loss_estimate: {base_loss}
#   severity_buffer_percent: {severity_buffer_pct * 100}%
#   fraud_risk_score: {fraud_score}
#   fraud_buffer_percent: {fraud_buffer_pct * 100:.1f}%
#   recommended_reserve: {recommended_reserve}
#   adjuster_set_reserve: {adjuster_reserve if adjuster_reserve else 'not set'}
#   variance_percent: {variance_pct}%

# Respond with ONLY a JSON object: {{"rationale": "..."}}
# """
#     response = llm.invoke(prompt)
#     content = response.content.strip().strip("`")
#     if content.startswith("json"):
#         content = content[4:]
#     try:
#         rationale = json.loads(content).get("rationale", "")
#     except Exception:
#         rationale = f"Reserve based on {severity} severity buffer ({int(severity_buffer_pct * 100)}%) and fraud risk adjustment ({int(fraud_buffer_pct * 100)}%)."

#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         if findings:
#             cur.execute(
#                 "UPDATE adjuster_findings SET system_recommended_reserve = %s WHERE id = %s",
#                 (recommended_reserve, findings["id"]),
#             )
#         else:
#             cur.execute(
#                 """INSERT INTO adjuster_findings (
#                     claim_id, adjuster_name, cause_of_loss, coverage_confirmed,
#                     fraud_risk, repair_vs_replace, adjusted_reserve,
#                     findings_date, fraud_risk_score, system_recommended_reserve
#                 ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)""",
#                 (
#                     claim_id,
#                     "ReserveRecommendationAgent",
#                     claim.get("loss_type") or "Unknown",
#                     "Pending",
#                     "Medium" if fraud_score < 50 else "High",
#                     "TBD",
#                     0,
#                     fraud_score,
#                     recommended_reserve,
#                 ),
#             )
#         conn.commit()
#     finally:
#         conn.close()

#     return {
#         "claim_id": claim_id,
#         "system_recommended_reserve": recommended_reserve,
#         "adjuster_set_reserve": adjuster_reserve or None,
#         "variance_percent": variance_pct,
#         "severity_buffer_percent": round(severity_buffer_pct * 100, 1),
#         "fraud_buffer_percent": round(fraud_buffer_pct * 100, 1),
#         "rationale": rationale,
#     }











#working code as per RK


# """
# handler.py — Reserve Recommendation
# ──────────────────────────────────────
# Calculates a recommended financial reserve by combining loss_assessments,
# fraud_risk_score, and claim severity. Compares the recommendation against
# the adjuster's manually set adjusted_reserve.
# """

# import json
# import logging
# import os
# import sys
# from typing import Optional

# sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

# from db import get_db_connection, row_to_dict  # noqa: E402
# from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

# log = logging.getLogger(__name__)

# _SEVERITY_BUFFER = {"Critical": 0.20, "High": 0.15, "Medium": 0.10, "Low": 0.05}


# def _get_llm():
#     return AzureChatOpenAI(
#         api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#         api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
#         azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
#         azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     )


# def get_adjuster_findings(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM adjuster_findings WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
#             (claim_id,),
#         )
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def _get_claim(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_id,))
#         row = cur.fetchone()
#         if row:
#             return row_to_dict(row)
#         if claim_id.isdigit():
#             cur.execute("SELECT * FROM claims WHERE id = %s", (int(claim_id),))
#             return row_to_dict(cur.fetchone())
#         return None
#     finally:
#         conn.close()


# def _get_loss_assessment(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM loss_assessments WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
#             (claim_id,),
#         )
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def _get_fraud_risk(claim_id: str) -> Optional[dict]:
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


# def _get_deductible(policy_number: str) -> Optional[float]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT deductible FROM policy_details WHERE policy_number = %s LIMIT 1",
#             (policy_number,),
#         )
#         row = row_to_dict(cur.fetchone())
#         if row and row.get("deductible") is not None:
#             return float(row["deductible"])
#         return None
#     finally:
#         conn.close()


# def _get_remaining_coverage_limit(policy_number: str) -> Optional[float]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT remaining_coverage_limit FROM policy_details WHERE policy_number = %s LIMIT 1",
#             (policy_number,),
#         )
#         row = row_to_dict(cur.fetchone())
#         if row and row.get("remaining_coverage_limit") is not None:
#             return float(row["remaining_coverage_limit"])
#         return None
#     finally:
#         conn.close()


# def recommend_reserve(claim_id: str) -> dict:
#     """
#     Derives a recommended reserve from loss assessment totals, fraud risk
#     buffer, and severity adjustment. Writes the result to
#     adjuster_findings.system_recommended_reserve — never overwrites
#     adjusted_reserve, which remains the adjuster's manual value.
#     """
#     claim = _get_claim(claim_id)
#     if not claim:
#         raise ValueError(f"Claim {claim_id} not found")

#     loss_assessment = _get_loss_assessment(claim_id)
#     fraud_snapshot = _get_fraud_risk(claim_id)
#     findings = get_adjuster_findings(claim_id)

#     severity = claim.get("severity") or "Medium"
#     estimated_cost = float(claim.get("estimated_cost") or 0)

#     if loss_assessment:
#         base_loss = float(loss_assessment.get("total_parts_cost") or 0) + \
#                     float(loss_assessment.get("total_labor_cost") or 0)
#     else:
#         base_loss = estimated_cost

#     fraud_score = int(fraud_snapshot.get("fraud_score") or 0) if fraud_snapshot else 0
#     fraud_buffer_pct = min(fraud_score / 1000, 0.10)
#     severity_buffer_pct = _SEVERITY_BUFFER.get(severity, 0.10)

#     policy_number = claim.get("policy_number") or ""
#     deductible = _get_deductible(policy_number) if policy_number else None
#     net_loss = max(base_loss - (deductible or 0.0), 0.0)

#     recommended_reserve = round(net_loss * (1 + severity_buffer_pct + fraud_buffer_pct), 2)

#     remaining_coverage_limit = _get_remaining_coverage_limit(policy_number) if policy_number else None
#     if remaining_coverage_limit is not None and recommended_reserve > remaining_coverage_limit:
#         recommended_reserve = remaining_coverage_limit

#     adjuster_reserve = float(findings.get("adjusted_reserve") or 0) if findings else 0.0
#     # variance_pct = round((recommended_reserve - adjuster_reserve) / adjuster_reserve * 100, 1) if adjuster_reserve > 0 else 0.0



#     if adjuster_reserve > 0:
#         variance_pct = round(
#             ((recommended_reserve - adjuster_reserve) / adjuster_reserve) * 100,
#             1,
#         )
#     else:
#         variance_pct = None


#     llm = _get_llm()
#     # prompt = f"""
# # You are an insurance reserve specialist. Write a one-sentence rationale
# # explaining the recommended reserve calculation.

# #   severity: {severity}
# #   base_loss_estimate: {base_loss}
# #   severity_buffer_percent: {severity_buffer_pct * 100}%
# #   fraud_risk_score: {fraud_score}
# #   fraud_buffer_percent: {fraud_buffer_pct * 100:.1f}%
# #   recommended_reserve: {recommended_reserve}
# #   adjuster_set_reserve: {adjuster_reserve if adjuster_reserve else 'not set'}
# #   variance_percent: {variance_pct}%

# # Respond with ONLY a JSON object: {{"rationale": "..."}}
# # """



#     prompt = f"""
# You are an insurance reserve specialist.
# Write a concise one-sentence rationale explaining how the recommended reserve was calculated.
# Use the following information:
# severity: {severity}
# base_loss_estimate: {base_loss}
# policy_deductible: {deductible if deductible is not None else "Not Applicable"}
# net_loss_after_deductible: {net_loss}
# severity_buffer_percent: {severity_buffer_pct * 100:.1f}%
# fraud_risk_score: {fraud_score}
# fraud_buffer_percent: {fraud_buffer_pct * 100:.1f}%
# remaining_coverage_limit: {remaining_coverage_limit if remaining_coverage_limit is not None else "Not Applicable"}
# recommended_reserve: {recommended_reserve}
# adjuster_set_reserve: {adjuster_reserve if adjuster_reserve > 0 else "Not Set"}
# variance_percent: {variance_pct if variance_pct is not None else "Not Applicable"}
# Mention deductible and coverage limit only if they affected the calculation.
# Respond ONLY as JSON.

# Your rationale MUST explicitly include:

# - the base loss estimate,

# - whether a policy deductible was applied (and the deductible amount),

# - the net loss after deductible,

# - the severity buffer,

# - the fraud buffer,

# - the final recommended reserve,

# - the comparison with the adjuster's reserve.

# Mention the remaining coverage limit only if it changed the final reserve.

# Respond ONLY as JSON.
 
# {{"rationale":"..."}}
# """

#     response = llm.invoke(prompt)
#     content = response.content.strip().strip("`")
#     if content.startswith("json"):
#         content = content[4:]
#     try:
#         rationale = json.loads(content).get("rationale", "")
#     except Exception:
#         rationale = f"Reserve based on {severity} severity buffer ({int(severity_buffer_pct * 100)}%) and fraud risk adjustment ({int(fraud_buffer_pct * 100)}%)."

#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         if findings:
#             cur.execute(
#                 "UPDATE adjuster_findings SET system_recommended_reserve = %s, reason_system_recommendation = %s WHERE id = %s",
#                 (recommended_reserve, rationale, findings["id"]),
#             )
#         else:
#             cur.execute(
#                 """INSERT INTO adjuster_findings (
#                     claim_id, adjuster_name, cause_of_loss, coverage_confirmed,
#                     fraud_risk, repair_vs_replace, adjusted_reserve,
#                     findings_date, fraud_risk_score, system_recommended_reserve,
#                     reason_system_recommendation
#                 ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s)""",
#                 (
#                     claim_id,
#                     "ReserveRecommendationAgent",
#                     claim.get("loss_type") or "Unknown",
#                     "Pending",
#                     "Medium" if fraud_score < 50 else "High",
#                     "TBD",
#                     0,
#                     fraud_score,
#                     recommended_reserve,
#                     rationale,
#                 ),
#             )
#         conn.commit()
#     finally:
#         conn.close()

#     return {
#         "claim_id": claim_id,
#         "system_recommended_reserve": recommended_reserve,
#         "adjuster_set_reserve": adjuster_reserve or None,
#         # "variance_percent": variance_pct,
#         "variance_percent": variance_pct if variance_pct is not None else "Not Applicable",
#         "severity_buffer_percent": round(severity_buffer_pct * 100, 1),
#         "fraud_buffer_percent": round(fraud_buffer_pct * 100, 1),
#         "rationale": rationale,
#     }







"""
handler.py — Reserve Recommendation
──────────────────────────────────────
Calculates a recommended financial reserve by combining loss_assessments,
fraud_risk_score, and claim severity. Compares the recommendation against
the adjuster's manually set adjusted_reserve.
"""

import json
import logging
import os
import sys
from datetime import date, datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

log = logging.getLogger(__name__)

_SEVERITY_BUFFER = {"Critical": 0.20, "High": 0.15, "Medium": 0.10, "Low": 0.05}


def _get_llm():
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def get_adjuster_findings(claim_id: str) -> Optional[dict]:
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


def _get_deductible(policy_number: str) -> Optional[float]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT deductible FROM policy_details WHERE policy_number = %s LIMIT 1",
            (policy_number,),
        )
        row = row_to_dict(cur.fetchone())
        if row and row.get("deductible") is not None:
            return float(row["deductible"])
        return None
    finally:
        conn.close()


def _get_remaining_coverage_limit(policy_number: str) -> Optional[float]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT remaining_coverage_limit FROM policy_details WHERE policy_number = %s LIMIT 1",
            (policy_number,),
        )
        row = row_to_dict(cur.fetchone())
        if row and row.get("remaining_coverage_limit") is not None:
            return float(row["remaining_coverage_limit"])
        return None
    finally:
        conn.close()


def _get_policy_details(policy_number: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT status, coverage_type, expiration_date, remaining_coverage_limit
               FROM policy_details WHERE policy_number = %s LIMIT 1""",
            (policy_number,),
        )
        row = row_to_dict(cur.fetchone())
        return row if row else {}
    finally:
        conn.close()


def _determine_coverage_confirmed(
    claim: dict,
    policy: dict,
    fraud_snapshot: Optional[dict],
    llm,
) -> str:
    """
    Returns 'Yes' only when ALL five conditions pass, otherwise 'No'.

    Condition 1 — policy_details.status == 'Active'
    Condition 2 — LLM validates loss_type is covered under coverage_type
    Condition 3 — policy_details.expiration_date >= today (not expired)
    Condition 4 — policy_details.remaining_coverage_limit > 0
    Condition 5 — fraud_risk_snapshots.fraud_score < 70
    """
    # Condition 1: policy must be Active
    if str(policy.get("status") or "").strip().lower() != "active":
        log.info("coverage_confirmed=No: policy status is not Active")
        return "No"

    # Condition 3: policy must not be expired
    expiration_date = policy.get("expiration_date")
    if expiration_date is not None:
        if isinstance(expiration_date, datetime):
            expiration_date = expiration_date.date()
        elif isinstance(expiration_date, str):
            try:
                expiration_date = date.fromisoformat(str(expiration_date)[:10])
            except Exception:
                expiration_date = None
        if expiration_date is not None and expiration_date < date.today():
            log.info("coverage_confirmed=No: policy has expired")
            return "No"

    # Condition 4: remaining coverage limit must be > 0
    remaining = policy.get("remaining_coverage_limit")
    if remaining is None or float(remaining) <= 0:
        log.info("coverage_confirmed=No: remaining_coverage_limit is 0 or missing")
        return "No"

    # Condition 5: fraud score must be < 70
    fraud_score = int(fraud_snapshot.get("fraud_score") or 0) if fraud_snapshot else 0
    if fraud_score >= 70:
        log.info("coverage_confirmed=No: fraud_score %s >= 70", fraud_score)
        return "No"

    # Condition 2: LLM validates that loss_type is covered by coverage_type
    loss_type = claim.get("loss_type") or "Unknown"
    coverage_type = policy.get("coverage_type") or "Unknown"
    coverage_prompt = f"""You are an insurance coverage specialist.
Determine whether the reported loss type is covered under the given policy coverage type.

Loss Type reported by claimant: {loss_type}
Policy Coverage Type: {coverage_type}

Coverage rules:
- Homeowners policy covers: fire, smoke, theft, vandalism, wind, hail, water damage (non-flood), falling objects, and similar residential property perils.
- Auto / Motor policy covers: vehicle collision, vehicle theft, vehicle vandalism, fire damage to a vehicle, weather damage to a vehicle.
- Commercial Property policy covers: business property losses from fire, theft, vandalism, wind, and similar perils.
- Flood policy covers: flood and water intrusion losses ONLY.
- Liability policy covers: third-party bodily injury and third-party property damage claims.
- If the loss type has NO plausible relationship to the coverage type (e.g. vehicle collision filed under Homeowners, flood filed under Auto), answer false.
- If there is a clear and direct relationship between the loss type and the coverage type, answer true.
- When genuinely uncertain, lean toward true.

Respond with ONLY valid JSON containing a single boolean key.
Example: {{"covered": true}}
"""
    try:
        response = llm.invoke(coverage_prompt)
        content = response.content.strip().strip("`")
        if content.startswith("json"):
            content = content[4:]
        covered = json.loads(content).get("covered", True)
        if not covered:
            log.info("coverage_confirmed=No: LLM says loss_type '%s' not covered by '%s'", loss_type, coverage_type)
            return "No"
    except Exception as exc:
        log.warning("coverage LLM check failed (%s) — defaulting to covered", exc)

    return "Yes"


def recommend_reserve(claim_id: str) -> dict:
    """
    Derives a recommended reserve from loss assessment totals, fraud risk
    buffer, and severity adjustment. Writes the result to
    adjuster_findings.system_recommended_reserve — never overwrites
    adjusted_reserve, which remains the adjuster's manual value.
    """
    claim = _get_claim(claim_id)
    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    loss_assessment = _get_loss_assessment(claim_id)
    fraud_snapshot = _get_fraud_risk(claim_id)
    findings = get_adjuster_findings(claim_id)

    severity = claim.get("severity") or "Medium"
    estimated_cost = float(claim.get("estimated_cost") or 0)

    if loss_assessment:
        base_loss = float(loss_assessment.get("total_parts_cost") or 0) + \
                    float(loss_assessment.get("total_labor_cost") or 0)
    else:
        base_loss = estimated_cost

    fraud_score = int(fraud_snapshot.get("fraud_score") or 0) if fraud_snapshot else 0
    fraud_buffer_pct = min(fraud_score / 1000, 0.10)
    severity_buffer_pct = _SEVERITY_BUFFER.get(severity, 0.10)

    policy_number = claim.get("policy_number") or ""
    policy_details = _get_policy_details(policy_number) if policy_number else {}
    deductible = _get_deductible(policy_number) if policy_number else None
    net_loss = max(base_loss - (deductible or 0.0), 0.0)

    recommended_reserve = round(net_loss * (1 + severity_buffer_pct + fraud_buffer_pct), 2)

    remaining_coverage_limit = _get_remaining_coverage_limit(policy_number) if policy_number else None
    if remaining_coverage_limit is not None and recommended_reserve > remaining_coverage_limit:
        recommended_reserve = remaining_coverage_limit

    adjuster_reserve = float(findings.get("adjusted_reserve") or 0) if findings else 0.0
    # variance_pct = round((recommended_reserve - adjuster_reserve) / adjuster_reserve * 100, 1) if adjuster_reserve > 0 else 0.0



    if adjuster_reserve > 0:
        variance_pct = round(
            ((recommended_reserve - adjuster_reserve) / adjuster_reserve) * 100,
            1,
        )
    else:
        variance_pct = None


    llm = _get_llm()
    coverage_confirmed = _determine_coverage_confirmed(claim, policy_details, fraud_snapshot, llm)

    # prompt = f"""
# You are an insurance reserve specialist. Write a one-sentence rationale
# explaining the recommended reserve calculation.

#   severity: {severity}
#   base_loss_estimate: {base_loss}
#   severity_buffer_percent: {severity_buffer_pct * 100}%
#   fraud_risk_score: {fraud_score}
#   fraud_buffer_percent: {fraud_buffer_pct * 100:.1f}%
#   recommended_reserve: {recommended_reserve}
#   adjuster_set_reserve: {adjuster_reserve if adjuster_reserve else 'not set'}
#   variance_percent: {variance_pct}%

# Respond with ONLY a JSON object: {{"rationale": "..."}}
# """



    prompt = f"""
You are an insurance reserve specialist.
Write a concise one-sentence rationale explaining how the recommended reserve was calculated.
Use the following information:
severity: {severity}
base_loss_estimate: {base_loss}
policy_deductible: {deductible if deductible is not None else "Not Applicable"}
net_loss_after_deductible: {net_loss}
severity_buffer_percent: {severity_buffer_pct * 100:.1f}%
fraud_risk_score: {fraud_score}
fraud_buffer_percent: {fraud_buffer_pct * 100:.1f}%
remaining_coverage_limit: {remaining_coverage_limit if remaining_coverage_limit is not None else "Not Applicable"}
recommended_reserve: {recommended_reserve}
adjuster_set_reserve: {adjuster_reserve if adjuster_reserve > 0 else "Not Set"}
variance_percent: {variance_pct if variance_pct is not None else "Not Applicable"}
Mention deductible and coverage limit only if they affected the calculation.
Respond ONLY as JSON.

Your rationale MUST explicitly include:

- the base loss estimate,

- whether a policy deductible was applied (and the deductible amount),

- the net loss after deductible,

- the severity buffer,

- the fraud buffer,

- the final recommended reserve,

- the comparison with the adjuster's reserve.

Mention the remaining coverage limit only if it changed the final reserve.

Respond ONLY as JSON.
 
{{"rationale":"..."}}
"""

    response = llm.invoke(prompt)
    content = response.content.strip().strip("`")
    if content.startswith("json"):
        content = content[4:]
    try:
        rationale = json.loads(content).get("rationale", "")
    except Exception:
        rationale = f"Reserve based on {severity} severity buffer ({int(severity_buffer_pct * 100)}%) and fraud risk adjustment ({int(fraud_buffer_pct * 100)}%)."

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if findings:
            cur.execute(
                """UPDATE adjuster_findings
                   SET system_recommended_reserve = %s,
                       reason_system_recommendation = %s,
                       coverage_confirmed = %s
                   WHERE id = %s""",
                (recommended_reserve, rationale, coverage_confirmed, findings["id"]),
            )
        else:
            cur.execute(
                """INSERT INTO adjuster_findings (
                    claim_id, adjuster_name, cause_of_loss, coverage_confirmed,
                    fraud_risk, repair_vs_replace, adjusted_reserve,
                    findings_date, fraud_risk_score, system_recommended_reserve,
                    reason_system_recommendation
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s)""",
                (
                    claim_id,
                    "ReserveRecommendationAgent",
                    claim.get("loss_type") or "Unknown",
                    coverage_confirmed,
                    "Medium" if fraud_score < 50 else "High",
                    "TBD",
                    0,
                    fraud_score,
                    recommended_reserve,
                    rationale,
                ),
            )
        conn.commit()
    finally:
        conn.close()

    return {
        "claim_id": claim_id,
        "coverage_confirmed": coverage_confirmed,
        "system_recommended_reserve": recommended_reserve,
        "adjuster_set_reserve": adjuster_reserve or None,
        "variance_percent": variance_pct if variance_pct is not None else "Not Applicable",
        "severity_buffer_percent": round(severity_buffer_pct * 100, 1),
        "fraud_buffer_percent": round(fraud_buffer_pct * 100, 1),
        "rationale": rationale,
    }
