# """
# handler.py — Settlement Recommendation
# ────────────────────────────────────────
# Calculates a recommended settlement amount by combining loss_estimation_outputs,
# repair-vs-replace decisions, and policy limits/deductibles. Persists the
# result to ai_decision_recommendations.
# """

# import json
# import logging
# import os
# import random
# import sys
# from datetime import datetime
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


# def get_ai_decision_recommendation(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM ai_decision_recommendations WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
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


# def _get_loss_estimation(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM loss_estimation_outputs WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
#             (claim_id,),
#         )
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def _get_repair_vs_replace(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         # table name varies — try both conventions
#         for table in ("repair_vs_replacement_decisions", "repair_vs_replacement"):
#             try:
#                 cur.execute(
#                     f"SELECT * FROM {table} WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
#                     (claim_id,),
#                 )
#                 row = cur.fetchone()
#                 if row:
#                     return row_to_dict(row)
#             except Exception:
#                 continue
#         return None
#     finally:
#         conn.close()


# def _get_policy(policy_number: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM policy_details WHERE policy_id = %s", (policy_number,))
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def _get_fraud_snapshot(claim_id: str) -> Optional[dict]:
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


# def _get_adjuster_findings(claim_id: str) -> Optional[dict]:
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


# def recommend_settlement(claim_id: str) -> dict:
#     """
#     Computes the recommended settlement amount by taking the net_payable from
#     loss_estimation, applying the repair/replace decision, and capping against
#     the policy limit. Uses an LLM to produce the settlement recommendation and
#     STP eligibility score.
#     """
#     claim = _get_claim(claim_id)
#     if not claim:
#         raise ValueError(f"Claim {claim_id} not found")

#     estimation = _get_loss_estimation(claim_id)
#     repair_replace = _get_repair_vs_replace(claim_id)
#     policy = _get_policy(claim.get("policy_number") or "")
#     fraud_snapshot = _get_fraud_snapshot(claim_id)
#     adjuster_findings = _get_adjuster_findings(claim_id)

#     net_payable = float(estimation.get("net_payable") or 0) if estimation else float(claim.get("estimated_cost") or 0)
#     deductible = float(estimation.get("deductible") or 0) if estimation else 0.0
#     policy_limit = float(policy.get("limit") or 999999) if policy else 999999
#     repair_recommended = (repair_replace.get("decision") or "Repair") if repair_replace else "Repair"

#     settlement_amount = min(net_payable, policy_limit)

#     llm = _get_llm()
#     prompt = f"""
# You are a senior claims adjuster computing a settlement recommendation.

# Claim context:
#   loss_type: {claim.get('loss_type')}
#   severity: {claim.get('severity')}
#   estimated_cost: {claim.get('estimated_cost')}
#   net_payable_after_deductible: {net_payable}
#   deductible: {deductible}
#   policy_limit: {policy_limit}
#   repair_vs_replace_decision: {repair_recommended}
#   calculated_settlement: {settlement_amount}

# Fraud risk snapshot:
#   fraud_score: {fraud_snapshot.get('fraud_score') if fraud_snapshot else 'N/A'}
#   red_flag_count: {fraud_snapshot.get('red_flag_count') if fraud_snapshot else 'N/A'}
#   prior_claims_risk: {fraud_snapshot.get('prior_claims') if fraud_snapshot else 'N/A'}
#   vendor_risk: {fraud_snapshot.get('vendor_risk') if fraud_snapshot else 'N/A'}

# Adjuster findings:
#   cause_of_loss: {adjuster_findings.get('cause_of_loss') if adjuster_findings else 'N/A'}
#   coverage_confirmed: {adjuster_findings.get('coverage_confirmed') if adjuster_findings else 'N/A'}
#   adjuster_fraud_risk: {adjuster_findings.get('fraud_risk') if adjuster_findings else 'N/A'}
#   adjuster_fraud_risk_score: {adjuster_findings.get('fraud_risk_score') if adjuster_findings else 'N/A'}

# Provide:
# - "recommended_action": concise settlement action text
# - "stp_score": straight-through-processing score 0-100
# - "confidence": decimal 0-1
# - "notes": brief rationale

# Respond with ONLY a JSON object with keys: recommended_action, stp_score, confidence, notes.
# """
#     response = llm.invoke(prompt)
#     content = response.content.strip()
#     if content.startswith("```"):
#         content = content.strip("`")
#         if content.startswith("json"):
#             content = content[4:]
#     try:
#         parsed = json.loads(content)
#     except Exception:
#         parsed = {
#             "recommended_action": f"Approve settlement of ${settlement_amount:,.2f}",
#             "stp_score": 50,
#             "confidence": 0.7,
#             "notes": "Standard settlement based on loss estimation and policy limits.",
#         }

#     recommendation_id = f"REC-{claim_id}-{random.randint(1000, 9999)}"
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "INSERT INTO ai_decision_recommendations (recommendation_id, claim_id, stp_score, recommended_action, confidence) VALUES (%s, %s, %s, %s, %s)",
#             (recommendation_id, claim_id, int(parsed.get("stp_score", 50)),
#              parsed.get("recommended_action", ""), float(parsed.get("confidence", 0.7))),
#         )
#         conn.commit()
#     finally:
#         conn.close()

#     return {
#         "recommendation_id": recommendation_id,
#         "claim_id": claim_id,
#         "settlement_amount": settlement_amount,
#         "deductible": deductible,
#         "policy_limit": policy_limit,
#         "recommended_action": parsed.get("recommended_action", ""),
#         "stp_score": int(parsed.get("stp_score", 50)),
#         "confidence": float(parsed.get("confidence", 0.7)),
#         "notes": parsed.get("notes", ""),
#         "generated_on": datetime.utcnow().isoformat(),
#     }











# """
# handler.py — Settlement Recommendation
# ────────────────────────────────────────
# Calculates a recommended settlement amount by combining loss_estimation_outputs,
# repair-vs-replace decisions, and policy limits/deductibles. Persists the
# result to ai_decision_recommendations.
# """

# import json
# import logging
# import os
# import random
# import sys
# from datetime import datetime
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


# def get_ai_decision_recommendation(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM ai_decision_recommendations WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
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


# def _get_loss_estimation(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM loss_estimation_outputs WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
#             (claim_id,),
#         )
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def _get_repair_vs_replace(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         # table name varies — try both conventions
#         for table in ("repair_vs_replacement_decisions"):
#             try:
#                 cur.execute(
#                     f"SELECT * FROM {table} WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
#                     (claim_id,),
#                 )
#                 row = cur.fetchone()
#                 if row:
#                     return row_to_dict(row)
#             except Exception:
#                 continue
#         return None
#     finally:
#         conn.close()


# def _get_policy(policy_number: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM policy_details WHERE policy_number = %s", (policy_number,))
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def _get_fraud_snapshot(claim_id: str) -> Optional[dict]:
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


# def _get_adjuster_findings(claim_id: str) -> Optional[dict]:
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


# def recommend_settlement(claim_id: str) -> dict:
#     """
#     Computes the recommended settlement amount by taking the net_payable from
#     loss_estimation, applying the repair/replace decision, and capping against
#     the policy limit. Uses an LLM to produce the settlement recommendation and
#     STP eligibility score.
#     """
#     claim = _get_claim(claim_id)
#     if not claim:
#         raise ValueError(f"Claim {claim_id} not found")

#     estimation = _get_loss_estimation(claim_id)
#     repair_replace = _get_repair_vs_replace(claim_id)
#     policy = _get_policy(claim.get("policy_number") or "")
#     if not policy:
#         raise ValueError(
#             f"Policy {claim.get('policy_number')} not found for claim {claim_id}"
#         )
#     fraud_snapshot = _get_fraud_snapshot(claim_id)
#     adjuster_findings = _get_adjuster_findings(claim_id)

#     net_payable = float(estimation.get("net_payable") or 0) if estimation else float(claim.get("estimated_cost") or 0)
#     deductible = float(estimation.get("deductible") or 0) if estimation else 0.0
#     # policy_limit = float(policy.get("limit") or 999999) if policy else 999999


#     remaining_limit = policy.get("remaining_coverage_limit")
#     if remaining_limit is None:
#             raise ValueError(
#                 f"Remaining coverage limit is not available for policy {claim.get('policy_number')}"
#             )
#     policy_limit = float(remaining_limit)    

#     # if policy:
#     #     remaining_limit = policy.get("remaining_coverage_limit")
#     #     coverage_limit = policy.get("coverage_limit")
#     #     if remaining_limit is not None:
#     #         policy_limit = float(remaining_limit)
#     #     elif coverage_limit is not None:
#     #         policy_limit = float(coverage_limit)
#     #     else:
#     #         policy_limit = 999999.0
#     # else:
#     #     policy_limit = 999999.0






#     repair_recommended = (repair_replace.get("decision") or "Repair") if repair_replace else "Repair"

#     settlement_amount = min(net_payable, policy_limit)

#     llm = _get_llm()
#     prompt = f"""
# You are a senior claims adjuster computing a settlement recommendation.

# Claim context:
#   loss_type: {claim.get('loss_type')}
#   severity: {claim.get('severity')}
#   estimated_cost: {claim.get('estimated_cost')}
#   net_payable_after_deductible: {net_payable}
#   deductible: {deductible}
#   policy_limit: {policy_limit}
#   repair_vs_replace_decision: {repair_recommended}
#   calculated_settlement: {settlement_amount}

# Fraud risk snapshot:
#   fraud_score: {fraud_snapshot.get('fraud_score') if fraud_snapshot else 'N/A'}
#   red_flag_count: {fraud_snapshot.get('red_flag_count') if fraud_snapshot else 'N/A'}
#   prior_claims_risk: {fraud_snapshot.get('prior_claims') if fraud_snapshot else 'N/A'}
#   vendor_risk: {fraud_snapshot.get('vendor_risk') if fraud_snapshot else 'N/A'}

# Adjuster findings:
#   cause_of_loss: {adjuster_findings.get('cause_of_loss') if adjuster_findings else 'N/A'}
#   coverage_confirmed: {adjuster_findings.get('coverage_confirmed') if adjuster_findings else 'N/A'}
#   adjuster_fraud_risk: {adjuster_findings.get('fraud_risk') if adjuster_findings else 'N/A'}
#   adjuster_fraud_risk_score: {adjuster_findings.get('fraud_risk_score') if adjuster_findings else 'N/A'}

# Provide:
# - "recommended_action": concise settlement action text
# - "stp_score": straight-through-processing score 0-100
# - "confidence": decimal 0-1
# - "notes": brief rationale

# Respond with ONLY a JSON object with keys: recommended_action, stp_score, confidence, notes.
# """
#     response = llm.invoke(prompt)
#     content = response.content.strip()
#     if content.startswith("```"):
#         content = content.strip("`")
#         if content.startswith("json"):
#             content = content[4:]
#     try:
#         parsed = json.loads(content)
#     except Exception:
#         parsed = {
#             "recommended_action": f"Approve settlement of ${settlement_amount:,.2f}",
#             "stp_score": 50,
#             "confidence": 0.7,
#             "notes": "Standard settlement based on loss estimation and policy limits.",
#         }

#     recommendation_id = f"REC-{claim_id}-{random.randint(1000, 9999)}"
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "INSERT INTO ai_decision_recommendations (recommendation_id, claim_id, stp_score, recommended_action, confidence) VALUES (%s, %s, %s, %s, %s)",
#             (recommendation_id, claim_id, int(parsed.get("stp_score", 50)),
#              parsed.get("recommended_action", ""), float(parsed.get("confidence", 0.7))),
#         )
#         conn.commit()
#     finally:
#         conn.close()

#     return {
#         "recommendation_id": recommendation_id,
#         "claim_id": claim_id,
#         "settlement_amount": settlement_amount,
#         "deductible": deductible,
#         "policy_limit": policy_limit,
#         "recommended_action": parsed.get("recommended_action", ""),
#         "stp_score": int(parsed.get("stp_score", 50)),
#         "confidence": float(parsed.get("confidence", 0.7)),
#         "notes": parsed.get("notes", ""),
#         "generated_on": datetime.utcnow().isoformat(),
#     }











# """
# handler.py — Settlement Recommendation
# ────────────────────────────────────────
# Calculates a recommended settlement amount by combining loss_estimation_outputs,
# repair-vs-replace decisions, and policy limits/deductibles. Persists the
# result to ai_decision_recommendations.
# """

# import json
# import logging
# import os
# import random
# import sys
# from datetime import datetime
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


# def get_ai_decision_recommendation(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM ai_decision_recommendations WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
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


# def _get_loss_estimation(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM loss_estimation_outputs WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
#             (claim_id,),
#         )
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def _get_repair_vs_replace(claim_id: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         # table name varies — try both conventions
#         # for table in ("repair_vs_replacement_decisions", "repair_vs_replacement"):
#         for table in ("repair_vs_replacement_decisions",):
#             try:
#                 cur.execute(
#                     f"SELECT * FROM {table} WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
#                     (claim_id,),
#                 )
#                 row = cur.fetchone()
#                 if row:
#                     return row_to_dict(row)
#             except Exception:
#                 continue
#         return None
#     finally:
#         conn.close()


# def _get_policy(policy_number: str) -> Optional[dict]:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM policy_details WHERE policy_number = %s", (policy_number,))
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# def _get_fraud_snapshot(claim_id: str) -> Optional[dict]:
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


# def _get_adjuster_findings(claim_id: str) -> Optional[dict]:
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




# def calculate_stp_score(
#     settlement_amount: float,
#     remaining_coverage_limit: float,
#     repair_replace: Optional[dict],
#     fraud_snapshot: Optional[dict],
#     adjuster_findings: Optional[dict],
#     claim: Optional[dict],
# ) -> int:
#     """
#     Calculates a deterministic Straight Through Processing (STP) score.
#     Returns an integer between 0 and 100.
#     """
#     score = 0
#     # 1. Coverage confirmed
#     if adjuster_findings and adjuster_findings.get("coverage_confirmed"):
#         score += 25
#     # 2. Fraud Risk
#     if adjuster_findings:
#         fraud_risk = str(adjuster_findings.get("fraud_risk") or "").lower()
#         if fraud_risk == "low":
#             score += 20
#     # 3. Fraud Score
#     if fraud_snapshot:
#         fraud_score = float(fraud_snapshot.get("fraud_score") or 100)
#         if fraud_score <= 20:
#             score += 10
#     # 4. Red Flags
#     if fraud_snapshot:
#         red_flags = int(fraud_snapshot.get("red_flag_count") or 0)
#         if red_flags == 0:
#             score += 10
#     # 5. Vendor Risk
#     if fraud_snapshot:
#         vendor_risk = str(fraud_snapshot.get("vendor_risk") or "").lower()
#         if vendor_risk == "low":
#             score += 5
#     # 6. Prior Claims Risk
#     if fraud_snapshot:
#         prior_claims = str(fraud_snapshot.get("prior_claims") or "").lower()
#         if prior_claims == "low":
#             score += 5
#     # 7. Repair Decision
#     if repair_replace:
#         decision = str(repair_replace.get("decision") or "").lower()
#         if decision == "repair":
#             score += 5
#     # 8. Settlement Successfully Calculated
#     if settlement_amount > 0:
#         score += 10
#     # 9. Remaining Coverage Available
#     if remaining_coverage_limit > 0:
#         score += 10
#     # 10. Severity Adjustment
#     severity = str(claim.get("severity") or "").lower()
#     if severity == "medium":
#         score -= 5
#     elif severity == "high":
#         score -= 10
#     elif severity == "critical":
#         score -= 20
#     # Clamp between 0 and 100
#     return max(0, min(score, 100))






# def calculate_confidence_score(
#    claim: Optional[dict],
#    estimation: Optional[dict],
#    policy: Optional[dict],
#    fraud_snapshot: Optional[dict],
#    adjuster_findings: Optional[dict],
#    repair_replace: Optional[dict],
# ) -> float:
#    """
#    Calculates a deterministic confidence score between 0.0 and 1.0.
#    """
#    score = 0
#    # Claim exists
#    if claim:
#        score += 15
#    # Loss estimation available
#    if estimation:
#        score += 20
#    # Policy available
#    if policy:
#        score += 20
#    # Coverage confirmed
#    if adjuster_findings and str(
#        adjuster_findings.get("coverage_confirmed")
#    ).lower() in ("yes", "true"):
#        score += 15
#    # Fraud snapshot available
#    if fraud_snapshot:
#        score += 10
#    # Fraud risk is Low
#    if fraud_snapshot:
#        if str(fraud_snapshot.get("vendor_risk")).lower() == "low":
#            score += 5
#        if str(fraud_snapshot.get("prior_claims")).lower() == "low":
#            score += 5
#        if int(fraud_snapshot.get("red_flag_count") or 0) == 0:
#            score += 5
#    # Repair vs Replace decision exists
#    if repair_replace:
#        score += 5
#    confidence = min(score / 100.0, 1.0)
#    return round(confidence, 2)




# def recommend_settlement(claim_id: str) -> dict:
#     """
#     Computes the recommended settlement amount by taking the net_payable from
#     loss_estimation, applying the repair/replace decision, and capping against
#     the policy limit. Uses an LLM to produce the settlement recommendation and
#     STP eligibility score.
#     """
#     claim = _get_claim(claim_id)
#     if not claim:
#         raise ValueError(f"Claim {claim_id} not found")

#     estimation = _get_loss_estimation(claim_id)
#     repair_replace = _get_repair_vs_replace(claim_id)
#     print("\n========== DEBUG ==========")
#     print("repair_replace =", repair_replace)
#     print("===========================\n")
#     policy = _get_policy(claim.get("policy_number") or "")
#     if not policy:
#         raise ValueError(
#             f"Policy {claim.get('policy_number')} not found for claim {claim_id}"
#         )
#     fraud_snapshot = _get_fraud_snapshot(claim_id)
#     adjuster_findings = _get_adjuster_findings(claim_id)

#     net_payable = float(estimation.get("net_payable") or 0) if estimation else float(claim.get("estimated_cost") or 0)
#     deductible = float(estimation.get("deductible") or 0) if estimation else 0.0
#     # remaining_coverage_limit = float(policy.get("limit") or 999999) if policy else 999999


#     remaining_limit = policy.get("remaining_coverage_limit")
#     if remaining_limit is None:
#             raise ValueError(
#                 f"Remaining coverage limit is not available for policy {claim.get('policy_number')}"
#             )
#     remaining_coverage_limit = float(remaining_limit)    

#     # if policy:
#     #     remaining_limit = policy.get("remaining_coverage_limit")
#     #     coverage_limit = policy.get("coverage_limit")
#     #     if remaining_limit is not None:
#     #         remaining_coverage_limit = float(remaining_limit)
#     #     elif coverage_limit is not None:
#     #         remaining_coverage_limit = float(coverage_limit)
#     #     else:
#     #         remaining_coverage_limit = 999999.0
#     # else:
#     #     remaining_coverage_limit = 999999.0






#     repair_recommended = (repair_replace.get("decision") or "Repair") if repair_replace else "Repair"
#     print("repair_recommended =", repair_recommended)
#     settlement_amount = min(net_payable, remaining_coverage_limit)
    


#     stp_score = calculate_stp_score(
#         settlement_amount=settlement_amount,
#         remaining_coverage_limit=remaining_coverage_limit,
#         repair_replace=repair_replace,
#         fraud_snapshot=fraud_snapshot,
#         adjuster_findings=adjuster_findings,
#         claim=claim,
#     )



#     confidence = calculate_confidence_score(
#         claim=claim,
#         estimation=estimation,
#         policy=policy,
#         fraud_snapshot=fraud_snapshot,
#         adjuster_findings=adjuster_findings,
#         repair_replace=repair_replace,
#     )


#     llm = _get_llm()
# #     prompt = f"""
# # You are a senior claims adjuster computing a settlement recommendation.

# # Claim context:
# #   loss_type: {claim.get('loss_type')}
# #   severity: {claim.get('severity')}
# #   estimated_cost: {claim.get('estimated_cost')}
# #   net_payable_after_deductible: {net_payable}
# #   deductible: {deductible}
# #   remaining_coverage_limit: {remaining_coverage_limit}
# #   repair_vs_replace_decision: {repair_recommended}
# #   calculated_settlement: {settlement_amount}

# # Fraud risk snapshot:
# #   fraud_score: {fraud_snapshot.get('fraud_score') if fraud_snapshot else 'N/A'}
# #   red_flag_count: {fraud_snapshot.get('red_flag_count') if fraud_snapshot else 'N/A'}
# #   prior_claims_risk: {fraud_snapshot.get('prior_claims') if fraud_snapshot else 'N/A'}
# #   vendor_risk: {fraud_snapshot.get('vendor_risk') if fraud_snapshot else 'N/A'}

# # Adjuster findings:
# #   cause_of_loss: {adjuster_findings.get('cause_of_loss') if adjuster_findings else 'N/A'}
# #   coverage_confirmed: {adjuster_findings.get('coverage_confirmed') if adjuster_findings else 'N/A'}
# #   adjuster_fraud_risk: {adjuster_findings.get('fraud_risk') if adjuster_findings else 'N/A'}
# #   adjuster_fraud_risk_score: {adjuster_findings.get('fraud_risk_score') if adjuster_findings else 'N/A'}

# # Provide:
# # - "recommended_action": concise settlement action text
# # - "confidence": decimal 0-1
# # - "notes": brief rationale

# # STP Score has already been calculated as:
# # {stp_score}
# # Do not generate or modify it.

# # Respond with ONLY a JSON object with keys:
# # recommended_action,
# # confidence,
# # notes
# # """


#     prompt = f"""
# You are an insurance claims assistant.

# The settlement amount has ALREADY been calculated by the business rules.

# DO NOT recalculate any numbers.
# DO NOT change the settlement amount.
# DO NOT change the STP score.
# DO NOT contradict the Repair vs Replace decision.
# Use the values exactly as provided.

# Claim Details

# Loss Type:
# {claim.get("loss_type")}

# Severity:
# {claim.get("severity")}

# Net Payable:
# {net_payable}

# Deductible Applied:
# {deductible}

# Remaining Policy Limit:
# {remaining_coverage_limit}

# Repair vs Replace Decision:
# {repair_recommended}

# Final Settlement Amount:
# {settlement_amount}

# Fraud Snapshot

# Fraud Score:
# {fraud_snapshot.get("fraud_score") if fraud_snapshot else "N/A"}

# Red Flag Count:
# {fraud_snapshot.get("red_flag_count") if fraud_snapshot else "N/A"}

# Vendor Risk:
# {fraud_snapshot.get("vendor_risk") if fraud_snapshot else "N/A"}

# Prior Claims:
# {fraud_snapshot.get("prior_claims") if fraud_snapshot else "N/A"}

# Adjuster Findings

# Coverage Confirmed:
# {adjuster_findings.get("coverage_confirmed") if adjuster_findings else "N/A"}

# Cause of Loss:
# {adjuster_findings.get("cause_of_loss") if adjuster_findings else "N/A"}

# Fraud Risk:
# {adjuster_findings.get("fraud_risk") if adjuster_findings else "N/A"}

# Deterministic STP Score:
# {stp_score}


# Generate ONLY valid JSON.
# recommended_action:
# One sentence only.
# Use ONLY the provided values.
# If Repair vs Replace Decision = Replace,
# the action MUST mention replacement.
# If Repair vs Replace Decision = Repair,
# the action MUST mention repair.
# The action MUST also mention the settlement amount exactly as provided.
# Do not recommend investigations,
# do not change the settlement amount,
# do not mention values that are not supplied.
# notes:
# 2-3 concise sentences explaining why the business rules produced this recommendation.
# Do not invent facts.
# Do not recalculate anything.

# Rules:

# - Never modify the settlement amount.
# - Never modify the STP score.
# - If Repair vs Replace Decision is Replace, mention replacement only.
# - If Repair vs Replace Decision is Repair, mention repair only.
# - Do not invent facts that are not provided.

# """


#     response = llm.invoke(prompt)
#     content = response.content.strip()
#     if content.startswith("```"):
#         content = content.strip("`")
#         if content.startswith("json"):
#             content = content[4:]
#     try:
#         parsed = json.loads(content)
#     except Exception:
#         parsed = {
#             "recommended_action": f"Approve settlement of ${settlement_amount:,.2f}",
#             "notes": "Standard settlement based on loss estimation and policy limits.",
#         }

#     recommendation_id = f"REC-{claim_id}-{random.randint(1000, 9999)}"
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         # cur.execute(
#         #     "INSERT INTO ai_decision_recommendations (recommendation_id, claim_id, stp_score, recommended_action, confidence) VALUES (%s, %s, %s, %s, %s)",
#         #     (recommendation_id, claim_id, stp_score,
#         #      parsed.get("recommended_action", ""), confidence,),)



#         cur.execute(
#         """
#         INSERT INTO ai_decision_recommendations
#         (
#             recommendation_id,
#             claim_id,
#             settlement_amount,
#             net_payable,
#             deductible,
#             remaining_coverage_limit,
#             final_decesion_repair_vs_replacement,
#             stp_score,
#             recommended_action,
#             confidence
#         )
#         VALUES
#         (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#         """,
#         (
#             recommendation_id,
#             claim_id,
#             settlement_amount,
#             net_payable,
#             deductible,
#             remaining_coverage_limit,
#             repair_recommended,
#             stp_score,
#             parsed.get("recommended_action", ""),
#             confidence,
#         ),
#         )

#         conn.commit()
#     finally:
#         conn.close()

#     return {
#         "recommendation_id": recommendation_id,
#         "claim_id": claim_id,
#         "settlement_amount": settlement_amount,
#         "deductible": deductible,
#         "remaining_coverage_limit": remaining_coverage_limit,
#         "recommended_action": parsed.get("recommended_action", ""),
#         "stp_score": stp_score,
#         "confidence": confidence,
#         "notes": parsed.get("notes", ""),
#         "generated_on": datetime.utcnow().isoformat(),
#     }




#rclaude


"""
handler.py — Settlement Recommendation
────────────────────────────────────────
Calculates a recommended settlement amount by combining loss_estimation_outputs,
repair-vs-replace decisions, and policy limits/deductibles. Persists the
result to ai_decision_recommendations.
"""

import json
import logging
import os
import random
import sys
from datetime import datetime
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


def get_ai_decision_recommendation(claim_id: str) -> Optional[dict]:
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


def _get_repair_vs_replace(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # table name varies — try both conventions
        # for table in ("repair_vs_replacement_decisions", "repair_vs_replacement"):
        for table in ("repair_vs_replacement_decisions",):
            try:
                cur.execute(
                    f"SELECT * FROM {table} WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
                    (claim_id,),
                )
                row = cur.fetchone()
                if row:
                    return row_to_dict(row)
            except Exception:
                continue
        return None
    finally:
        conn.close()


def _get_policy(policy_number: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM policy_details WHERE policy_number = %s", (policy_number,))
        return row_to_dict(cur.fetchone())
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





def _get_stp_score(claim_id: str) -> Optional[int]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT stp_score FROM stp_classification WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        row = row_to_dict(cur.fetchone())
        if row and row.get("stp_score") is not None:
            return int(row["stp_score"])
        return None
    finally:
        conn.close()

def recommend_settlement(claim_id: str) -> dict:
    """
    Computes the recommended settlement amount by taking the net_payable from
    loss_estimation, applying the repair/replace decision, and capping against
    the policy limit. Uses an LLM to produce the settlement recommendation and
    STP eligibility score.
    """
    claim = _get_claim(claim_id)
    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    estimation = _get_loss_estimation(claim_id)
    repair_replace = _get_repair_vs_replace(claim_id)
    print("\n========== DEBUG ==========")
    print("repair_replace =", repair_replace)
    print("===========================\n")
    policy = _get_policy(claim.get("policy_number") or "")
    if not policy:
        raise ValueError(
            f"Policy {claim.get('policy_number')} not found for claim {claim_id}"
        )
    fraud_snapshot = _get_fraud_snapshot(claim_id)
    adjuster_findings = _get_adjuster_findings(claim_id)

    net_payable = float(estimation.get("net_payable") or 0) if estimation else float(claim.get("estimated_cost") or 0)
    deductible = float(estimation.get("deductible") or 0) if estimation else 0.0
    # remaining_coverage_limit = float(policy.get("limit") or 999999) if policy else 999999


    remaining_limit = policy.get("remaining_coverage_limit")
    if remaining_limit is None:
            raise ValueError(
                f"Remaining coverage limit is not available for policy {claim.get('policy_number')}"
            )
    remaining_coverage_limit = float(remaining_limit)    

    # if policy:
    #     remaining_limit = policy.get("remaining_coverage_limit")
    #     coverage_limit = policy.get("coverage_limit")
    #     if remaining_limit is not None:
    #         remaining_coverage_limit = float(remaining_limit)
    #     elif coverage_limit is not None:
    #         remaining_coverage_limit = float(coverage_limit)
    #     else:
    #         remaining_coverage_limit = 999999.0
    # else:
    #     remaining_coverage_limit = 999999.0






    repair_recommended = (repair_replace.get("decision") or "Repair") if repair_replace else "Repair"
    print("repair_recommended =", repair_recommended)
    settlement_amount = min(net_payable, remaining_coverage_limit)
    


    stp_score = _get_stp_score(claim_id) or 0


    llm = _get_llm()
#     prompt = f"""
# You are a senior claims adjuster computing a settlement recommendation.

# Claim context:
#   loss_type: {claim.get('loss_type')}
#   severity: {claim.get('severity')}
#   estimated_cost: {claim.get('estimated_cost')}
#   net_payable_after_deductible: {net_payable}
#   deductible: {deductible}
#   remaining_coverage_limit: {remaining_coverage_limit}
#   repair_vs_replace_decision: {repair_recommended}
#   calculated_settlement: {settlement_amount}

# Fraud risk snapshot:
#   fraud_score: {fraud_snapshot.get('fraud_score') if fraud_snapshot else 'N/A'}
#   red_flag_count: {fraud_snapshot.get('red_flag_count') if fraud_snapshot else 'N/A'}
#   prior_claims_risk: {fraud_snapshot.get('prior_claims') if fraud_snapshot else 'N/A'}
#   vendor_risk: {fraud_snapshot.get('vendor_risk') if fraud_snapshot else 'N/A'}

# Adjuster findings:
#   cause_of_loss: {adjuster_findings.get('cause_of_loss') if adjuster_findings else 'N/A'}
#   coverage_confirmed: {adjuster_findings.get('coverage_confirmed') if adjuster_findings else 'N/A'}
#   adjuster_fraud_risk: {adjuster_findings.get('fraud_risk') if adjuster_findings else 'N/A'}
#   adjuster_fraud_risk_score: {adjuster_findings.get('fraud_risk_score') if adjuster_findings else 'N/A'}

# Provide:
# - "recommended_action": concise settlement action text
# - "confidence": decimal 0-1
# - "notes": brief rationale

# STP Score has already been calculated as:
# {stp_score}
# Do not generate or modify it.

# Respond with ONLY a JSON object with keys:
# recommended_action,
# confidence,
# notes
# """


    prompt = f"""
You are an insurance claims assistant.

The settlement amount has ALREADY been calculated by the business rules.

DO NOT recalculate any numbers.
DO NOT change the settlement amount.
DO NOT change the STP score.
DO NOT contradict the Repair vs Replace decision.
Use the values exactly as provided.

Claim Details

Loss Type:
{claim.get("loss_type")}

Severity:
{claim.get("severity")}

Net Payable:
{net_payable}

Deductible Applied:
{deductible}

Remaining Policy Limit:
{remaining_coverage_limit}

Repair vs Replace Decision:
{repair_recommended}

Final Settlement Amount:
{settlement_amount}

Fraud Snapshot

Fraud Score:
{fraud_snapshot.get("fraud_score") if fraud_snapshot else "N/A"}

Red Flag Count:
{fraud_snapshot.get("red_flag_count") if fraud_snapshot else "N/A"}

Vendor Risk:
{fraud_snapshot.get("vendor_risk") if fraud_snapshot else "N/A"}

Prior Claims:
{fraud_snapshot.get("prior_claims") if fraud_snapshot else "N/A"}

Adjuster Findings

Coverage Confirmed:
{adjuster_findings.get("coverage_confirmed") if adjuster_findings else "N/A"}

Cause of Loss:
{adjuster_findings.get("cause_of_loss") if adjuster_findings else "N/A"}

Fraud Risk:
{adjuster_findings.get("fraud_risk") if adjuster_findings else "N/A"}

Deterministic STP Score:
{stp_score}


Generate ONLY valid JSON.
recommended_action:
One sentence only.
Use ONLY the provided values.
If Repair vs Replace Decision = Replace,
the action MUST mention replacement.
If Repair vs Replace Decision = Repair,
the action MUST mention repair.
The action MUST also mention the settlement amount exactly as provided.
Do not recommend investigations,
do not change the settlement amount,
do not mention values that are not supplied.
notes:
2-3 concise sentences explaining why the business rules produced this recommendation.
Do not invent facts.
Do not recalculate anything.

Rules:

- Never modify the settlement amount.
- Never modify the STP score.
- If Repair vs Replace Decision is Replace, mention replacement only.
- If Repair vs Replace Decision is Repair, mention repair only.
- Do not invent facts that are not provided.

"""


    response = llm.invoke(prompt)
    content = response.content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    try:
        parsed = json.loads(content)
    except Exception:
        parsed = {
            "recommended_action": f"Approve settlement of ${settlement_amount:,.2f}",
            "notes": "Standard settlement based on loss estimation and policy limits.",
        }

    recommendation_id = f"REC-{claim_id}-{random.randint(1000, 9999)}"
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # cur.execute(
        #     "INSERT INTO ai_decision_recommendations (recommendation_id, claim_id, stp_score, recommended_action, confidence) VALUES (%s, %s, %s, %s, %s)",
        #     (recommendation_id, claim_id, stp_score,
        #      parsed.get("recommended_action", ""), confidence,),)



        cur.execute(
        """
        INSERT INTO ai_decision_recommendations
        (
            recommendation_id,
            claim_id,
            settlement_amount,
            net_payable,
            deductible,
            remaining_coverage_limit,
            final_decesion_repair_vs_replacement,
            stp_score,
            recommended_action
        )
        VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            recommendation_id,
            claim_id,
            settlement_amount,
            net_payable,
            deductible,
            remaining_coverage_limit,
            repair_recommended,
            stp_score,
            parsed.get("recommended_action", ""),
        ),
        )

        conn.commit()
    finally:
        conn.close()

    return {
        "recommendation_id": recommendation_id,
        "claim_id": claim_id,
        "settlement_amount": settlement_amount,
        "deductible": deductible,
        "remaining_coverage_limit": remaining_coverage_limit,
        "recommended_action": parsed.get("recommended_action", ""),
        "stp_score": stp_score,
        "notes": parsed.get("notes", ""),
        "generated_on": datetime.utcnow().isoformat(),
    }
