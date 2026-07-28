# """
# handler.py — Repair vs Replacement
# ───────────────────────────────────────
# Compares repair vs. replacement costs for a damaged item and recommends a
# course of action based on a cost-ratio / useful-life rule.
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


# def _get_llm():
#     return AzureChatOpenAI(
#         api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#         api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
#         azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
#         azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     )


# def get_estimates(claim_id: str) -> list:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM estimates WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
#         return row_to_dict(cur.fetchall())
#     finally:
#         conn.close()


# def write_estimate(claim_id: str, item_type: str, item_age: int, useful_life_remaining: int,
#                     repair_cost: float, replacement_cost: float, labor_cost: float, material_cost: float,
#                     recommendation: str, confidence_score: float) -> dict:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO estimates (
#                 claim_id, item_type, item_age, useful_life_remaining, repair_cost, replacement_cost,
#                 labor_cost, material_cost, recommendation, confidence_score
#             ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#             """,
#             (claim_id, item_type, item_age, useful_life_remaining, repair_cost, replacement_cost,
#              labor_cost, material_cost, recommendation, confidence_score),
#         )
#         conn.commit()
#         return {
#             "id": cur.lastrowid, "claim_id": claim_id, "item_type": item_type, "item_age": item_age,
#             "useful_life_remaining": useful_life_remaining, "repair_cost": repair_cost,
#             "replacement_cost": replacement_cost, "labor_cost": labor_cost, "material_cost": material_cost,
#             "recommendation": recommendation, "confidence_score": confidence_score,
#         }
#     finally:
#         conn.close()


# def get_repair_cost_detail(claim_id: str) -> list:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM repair_costs WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
#         return row_to_dict(cur.fetchall())
#     finally:
#         conn.close()


# def write_repair_cost(item_id: str, claim_id: str, item_type: str, material_cost: float, labor_hours: float,
#                        labor_rate: float, diagnostic_fee: float, urgency_factor: float, notes: Optional[str] = None) -> dict:
#     total_repair_estimate = round((material_cost + labor_hours * labor_rate + diagnostic_fee) * (urgency_factor or 1.0), 2)
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO repair_costs (
#                 item_id, claim_id, item_type, material_cost, labor_hours, labor_rate,
#                 diagnostic_fee, urgency_factor, total_repair_estimate, notes
#             ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#             """,
#             (item_id, claim_id, item_type, material_cost, labor_hours, labor_rate,
#              diagnostic_fee, urgency_factor, total_repair_estimate, notes),
#         )
#         conn.commit()
#         return {
#             "id": cur.lastrowid, "item_id": item_id, "claim_id": claim_id, "item_type": item_type,
#             "material_cost": material_cost, "labor_hours": labor_hours, "labor_rate": labor_rate,
#             "diagnostic_fee": diagnostic_fee, "urgency_factor": urgency_factor,
#             "total_repair_estimate": total_repair_estimate, "notes": notes,
#         }
#     finally:
#         conn.close()


# def get_replacement_cost_detail(claim_id: str) -> list:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM replacement_costs WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
#         return row_to_dict(cur.fetchall())
#     finally:
#         conn.close()


# def write_replacement_cost(item_id: str, claim_id: str, item_type: str, replacement_material_cost: float,
#                             installation_hours: float, labor_rate: float, delivery_fee: float, disposal_fee: float,
#                             notes: Optional[str] = None) -> dict:
#     total_replacement_estimate = round(
#         replacement_material_cost + installation_hours * labor_rate + delivery_fee + disposal_fee, 2
#     )
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO replacement_costs (
#                 item_id, claim_id, item_type, replacement_material_cost, installation_hours, labor_rate,
#                 delivery_fee, disposal_fee, total_replacement_estimate, notes
#             ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#             """,
#             (item_id, claim_id, item_type, replacement_material_cost, installation_hours, labor_rate,
#              delivery_fee, disposal_fee, total_replacement_estimate, notes),
#         )
#         conn.commit()
#         return {
#             "id": cur.lastrowid, "item_id": item_id, "claim_id": claim_id, "item_type": item_type,
#             "replacement_material_cost": replacement_material_cost, "installation_hours": installation_hours,
#             "labor_rate": labor_rate, "delivery_fee": delivery_fee, "disposal_fee": disposal_fee,
#             "total_replacement_estimate": total_replacement_estimate, "notes": notes,
#         }
#     finally:
#         conn.close()


# def _llm_estimate_costs(item_type: str, item_age: int) -> dict:
#     llm = _get_llm()
#     prompt = f"""
# You are a claims adjuster's assistant. Estimate plausible repair and
# replacement costs in USD for a "{item_type}" that is {item_age} years old.
# Respond with ONLY a JSON object:
# {{"repair_cost": 0, "replacement_cost": 0, "labor_cost": 0, "material_cost": 0}}
# """
#     response = llm.invoke(prompt)
#     content = response.content.strip()
#     if content.startswith("```"):
#         content = content.strip("`")
#         if content.startswith("json"):
#             content = content[4:]
#     try:
#         return json.loads(content)
#     except Exception:
#         log.warning("Could not parse LLM JSON, defaulting: %s", content)
#         return {"repair_cost": 500, "replacement_cost": 1000, "labor_cost": 200, "material_cost": 300}


# def compare_repair_vs_replace(claim_id: str, item_type: str, item_age: int, useful_life_remaining: int) -> dict:
#     # Look up existing repair_costs/replacement_costs for this claim+item_type, if present
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM repair_costs WHERE claim_id = %s AND item_type = %s ORDER BY id DESC LIMIT 1",
#             (claim_id, item_type),
#         )
#         repair_row = row_to_dict(cur.fetchone())
#         cur.execute(
#             "SELECT * FROM replacement_costs WHERE claim_id = %s AND item_type = %s ORDER BY id DESC LIMIT 1",
#             (claim_id, item_type),
#         )
#         replacement_row = row_to_dict(cur.fetchone())
#     finally:
#         conn.close()

#     if repair_row and replacement_row:
#         repair_cost = float(repair_row["total_repair_estimate"])
#         replacement_cost = float(replacement_row["total_replacement_estimate"])
#         labor_cost = float(repair_row.get("labor_hours") or 0) * float(repair_row.get("labor_rate") or 0)
#         material_cost = float(repair_row.get("material_cost") or 0)
#     else:
#         ai_costs = _llm_estimate_costs(item_type, item_age)
#         repair_cost = float(ai_costs.get("repair_cost", 500))
#         replacement_cost = float(ai_costs.get("replacement_cost", 1000))
#         labor_cost = float(ai_costs.get("labor_cost", 200))
#         material_cost = float(ai_costs.get("material_cost", 300))

#     if repair_cost > 0.6 * replacement_cost or item_age >= useful_life_remaining:
#         recommendation = "Replace"
#     else:
#         recommendation = "Repair"

#     # Confidence heuristic: bigger gap between costs => more confident
#     if replacement_cost > 0:
#         ratio_gap = abs(repair_cost - replacement_cost) / replacement_cost
#     else:
#         ratio_gap = 0
#     confidence_score = round(min(1.0, 0.5 + ratio_gap), 2)

#     estimate = write_estimate(
#         claim_id, item_type, item_age, useful_life_remaining, repair_cost, replacement_cost,
#         labor_cost, material_cost, recommendation, confidence_score,
#     )

#     return {
#         "claim_id": claim_id,
#         "item_type": item_type,
#         "item_age": item_age,
#         "useful_life_remaining": useful_life_remaining,
#         "repair_cost": repair_cost,
#         "replacement_cost": replacement_cost,
#         "recommendation": recommendation,
#         "confidence_score": confidence_score,
#         "estimate": estimate,
#     }



#Working code as per RK

# """
# handler.py — Repair vs Replacement
# ───────────────────────────────────────
# Compares repair vs. replacement costs for a damaged item and recommends a
# course of action based on a cost-ratio / useful-life rule.
# """

# import json
# import logging
# import os
# import sys
# from typing import Optional

# sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

# from db import get_db_connection, row_to_dict  # noqa: E402
# from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402


# from datetime import datetime
# import pytz


# log = logging.getLogger(__name__)


# def get_claim_id(claim_number: str) -> int:
# #    claim_id = get_claim_id(claim_number)
#    conn = get_db_connection()
#    try:
#        cur = conn.cursor()
#        cur.execute(
#            """
#            SELECT id
#            FROM claims
#            WHERE claim_number = %s
#            """,
#            (claim_number,),
#        )
#        row = row_to_dict(cur.fetchone())
#        if not row:
#            raise ValueError(f"Claim '{claim_number}' not found")
#        return row["id"]
#    finally:
#        conn.close()


# def get_damage_item(claim_number: str) -> dict:
#    conn = get_db_connection()
#    try:
#        cur = conn.cursor()
#        cur.execute(
#            """
#            SELECT *
#            FROM damage_items
#            WHERE claim_number = %s
#            LIMIT 1
#            """,
#            (claim_number,),
#        )
#        row = row_to_dict(cur.fetchone())
#     #    if not row:
#     #        raise ValueError(
#     #            f"No damage item found for claim '{claim_number}'"
#     #        )
#        if not row:
#           raise ValueError(
#             f"Damage assessment has not been completed for claim {claim_number}. "
#             "Repair vs Replacement cannot be performed until damage items are available."
#            )
#        return row
#    finally:
#        conn.close()

# def _get_llm():
#     return AzureChatOpenAI(
#         api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#         api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
#         azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
#         azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     )


# def get_estimates(claim_number: str) -> list:
#     claim_id = get_claim_id(claim_number)
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM estimates WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
#         return row_to_dict(cur.fetchall())
#     finally:
#         conn.close()


# def write_estimate(claim_number: str, item_type: str, item_age: int, useful_life_remaining: int,
#                     repair_cost: float, replacement_cost: float, labor_cost: float, material_cost: float,
#                     recommendation: str, confidence_score: float) -> dict:
#     claim_id = get_claim_id(claim_number)
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO estimates (
#                 claim_id, item_type, item_age, useful_life_remaining, repair_cost, replacement_cost,
#                 labor_cost, material_cost, recommendation, confidence_score
#             ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#             """,
#             (claim_id, item_type, item_age, useful_life_remaining, repair_cost, replacement_cost,
#              labor_cost, material_cost, recommendation, confidence_score),
#         )
#         conn.commit()
#         return {
#             "id": cur.lastrowid, "claim_id": claim_id, "item_type": item_type, "item_age": item_age,
#             "useful_life_remaining": useful_life_remaining, "repair_cost": repair_cost,
#             "replacement_cost": replacement_cost, "labor_cost": labor_cost, "material_cost": material_cost,
#             "recommendation": recommendation, "confidence_score": confidence_score,
#         }
#     finally:
#         conn.close()


# def get_repair_cost_detail(claim_number: str) -> list:
#     claim_id = get_claim_id(claim_number)
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM repair_costs WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
#         return row_to_dict(cur.fetchall())
#     finally:
#         conn.close()


# def write_repair_cost(item_id: str, claim_number: str, item_type: str, material_cost: float, labor_hours: float,
#                        labor_rate: float, diagnostic_fee: float, urgency_factor: float, notes: Optional[str] = None) -> dict:
#     total_repair_estimate = round((material_cost + labor_hours * labor_rate + diagnostic_fee) * (urgency_factor or 1.0), 2)
#     claim_id = get_claim_id(claim_number)
#     conn = get_db_connection()
    
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO repair_costs (
#                 item_id, claim_id, item_type, material_cost, labor_hours, labor_rate,
#                 diagnostic_fee, urgency_factor, total_repair_estimate, notes
#             ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#             """,
#             (item_id, claim_id, item_type, material_cost, labor_hours, labor_rate,
#              diagnostic_fee, urgency_factor, total_repair_estimate, notes),
#         )
#         conn.commit()
#         return {
#             "id": cur.lastrowid, "item_id": item_id, "claim_id": claim_id, "item_type": item_type,
#             "material_cost": material_cost, "labor_hours": labor_hours, "labor_rate": labor_rate,
#             "diagnostic_fee": diagnostic_fee, "urgency_factor": urgency_factor,
#             "total_repair_estimate": total_repair_estimate, "notes": notes,
#         }
#     finally:
#         conn.close()


# def get_replacement_cost_detail(claim_number: str) -> list:
#     claim_id = get_claim_id(claim_number)
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM replacement_costs WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
#         return row_to_dict(cur.fetchall())
#     finally:
#         conn.close()


# def write_replacement_cost(item_id: str, claim_number: str, item_type: str, replacement_material_cost: float,
#                             installation_hours: float, labor_rate: float, delivery_fee: float, disposal_fee: float,
#                             notes: Optional[str] = None) -> dict:
#     total_replacement_estimate = round(
#         replacement_material_cost + installation_hours * labor_rate + delivery_fee + disposal_fee, 2
#     )
#     claim_id = get_claim_id(claim_number)
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO replacement_costs (
#                 item_id, claim_id, item_type, replacement_material_cost, installation_hours, labor_rate,
#                 delivery_fee, disposal_fee, total_replacement_estimate, notes
#             ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#             """,
#             (item_id, claim_id, item_type, replacement_material_cost, installation_hours, labor_rate,
#              delivery_fee, disposal_fee, total_replacement_estimate, notes),
#         )
#         conn.commit()
#         return {
#             "id": cur.lastrowid, "item_id": item_id, "claim_id": claim_id, "item_type": item_type,
#             "replacement_material_cost": replacement_material_cost, "installation_hours": installation_hours,
#             "labor_rate": labor_rate, "delivery_fee": delivery_fee, "disposal_fee": disposal_fee,
#             "total_replacement_estimate": total_replacement_estimate, "notes": notes,
#         }
#     finally:
#         conn.close()






# # def update_repair_vs_replacement_decision(
# #     claim_number: str,
# #     decision: str,
# # ) -> dict:
# #     if decision not in ["Repair", "Replace"]:
# #         raise ValueError(
# #             "Decision must be either 'Repair' or 'Replace'."
# #         )
# #     conn = get_db_connection()
# #     try:
# #         cur = conn.cursor()
# #         # Verify recommendation row exists
# #         cur.execute(
# #             """
# #             SELECT *
# #             FROM repair_vs_replacement_decisions
# #             WHERE claim_id = %s
# #             """,
# #             (claim_number,),
# #         )
# #         row = row_to_dict(cur.fetchone())
# #         if not row:
# #             raise ValueError(
# #                 f"No Repair vs Replacement recommendation exists for claim '{claim_number}'."
# #             )
# #         cur.execute(
# #             """
# #             UPDATE repair_vs_replacement_decisions
# #             SET decision = %s
# #             WHERE claim_id = %s
# #             """,
# #             (
# #                 decision,
# #                 claim_number,
# #             ),
# #         )
# #         conn.commit()
# #         return {
# #             "claim_number": claim_number,
# #             "decision": decision,
# #             "message": "Adjuster decision recorded successfully."
# #         }
# #     finally:
# #         conn.close()






# def update_repair_vs_replacement_decision(
#     claim_number: str,
#     decision: str,
# ) -> dict:
#     decision = decision.strip().capitalize()
#     if decision not in ["Repair", "Replace"]:
#         raise ValueError(
#             "Decision must be either 'Repair' or 'Replace'."
#         )
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             SELECT id
#             FROM repair_vs_replacement_decisions
#             WHERE claim_id=%s
#             """,
#             (claim_number,),
#         )
#         row = row_to_dict(cur.fetchone())
#         if not row:
#             raise ValueError(
#                 f"No recommendation exists for claim '{claim_number}'."
#             )
#         ist = pytz.timezone("Asia/Kolkata")
#         current_time = datetime.now(ist)
#         cur.execute(
#             """
#             UPDATE repair_vs_replacement_decisions
#             SET
#                 decision=%s,
#                 timestamp=%s
#             WHERE claim_id=%s
#             """,
#             (
#                 decision,
#                 current_time,
#                 claim_number,
#             ),
#         )
#         conn.commit()
#         return {
#             "claim_number": claim_number,
#             "decision": decision,
#             "message": "Adjuster decision recorded successfully."
#         }
#     finally:
#         conn.close()







# def write_repair_vs_replacement_decision(
#     claim_number: str,
#     recommended_action: str,
#     ai_generated_message: str,
# ) -> dict:
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         # Verify claim exists and fetch policyholder
#         cur.execute(
#             """
#             SELECT
#                 claim_number,
#                 policyholder_name
#             FROM claims
#             WHERE claim_number = %s
#             """,
#             (claim_number,),
#         )
#         row = row_to_dict(cur.fetchone())
#         if not row:
#             raise ValueError(f"Claim '{claim_number}' not found")
#         ist = pytz.timezone("Asia/Kolkata")
#         current_time = datetime.now(ist)
        
        





#         cur.execute(
#             """
#             SELECT id
#             FROM repair_vs_replacement_decisions
#             WHERE claim_id=%s
#             """,
#             (claim_number,),
#         )
#         existing = row_to_dict(cur.fetchone())
#         if existing:
#             return {
#                 "status" : "already_exists",
#                 "claim_number": claim_number,
#                 "message": "Recommendation already recorded."
#             }




#         cur.execute(
#             """
#             INSERT INTO repair_vs_replacement_decisions
#             (
#                 claim_id,
#                 customer_name,
#                 communication_type,
#                 ai_generated_message,
#                 recommended_action,
#                 sent_method,
#                 timestamp,
#                 decision
#             )
#             VALUES
#             (
#                 %s,%s,%s,%s,%s,%s,%s,%s
#             )
#             """,
#             (
#                 row["claim_number"],
#                 row["policyholder_name"],
#                 "email",
#                 ai_generated_message,
#                 recommended_action,
#                 "email",
#                 current_time,
#                 "Adjuster review",
#             ),
#         )
#         conn.commit()
#         return {
#             "claim_number": row["claim_number"],
#             "customer_name": row["policyholder_name"],
#             "recommended_action": recommended_action,
#         }
#     finally:
#         conn.close()



# # def _llm_estimate_costs(item_type: str, item_age: int) -> dict:
# def _llm_estimate_costs(
#    item_type: str,
#    item_age: int,
#    severity: str,
#    estimated_cost: float,
#    adjuster_notes: str,
# ) -> dict:
#     llm = _get_llm()
# #     prompt = f"""
# # You are a claims adjuster's assistant. Estimate plausible repair and
# # replacement costs in USD for a "{item_type}" that is {item_age} years old.
# # Respond with ONLY a JSON object:
# # {{"repair_cost": 0, "replacement_cost": 0, "labor_cost": 0, "material_cost": 0}}
# # """


# # prompt = f"""
# # You are an insurance claims cost estimator.
# # Estimate realistic repair and replacement costs for a damaged "{item_type}"
# # that is {item_age} years old.
# # Return ONLY valid JSON.
# # {{
# #    "repair_cost": 0,
# #    "replacement_cost": 0,
# #    "material_cost": 0,
# #    "labor_hours": 0,
# #    "labor_rate": 0,
# #    "diagnostic_fee": 0,
# #    "urgency_factor": 1.0,
# #    "replacement_material_cost": 0,
# #    "installation_hours": 0,
# #    "delivery_fee": 0,
# #    "disposal_fee": 0
# # }}
# # """


#     prompt = f"""
#     You are an insurance claims cost estimator.
#     Estimate realistic repair and replacement costs for the damaged item using the following information.
#     Item Type: {item_type}
#     Item Age: {item_age} years
#     Damage Severity: {severity}
#     Adjuster's Notes: {adjuster_notes}
#     Initial Damage Estimate: ${estimated_cost}
#     Return ONLY valid JSON.
#     {{
#     "repair_cost": 0,
#     "replacement_cost": 0,
#     "material_cost": 0,
#     "labor_hours": 0,
#     "labor_rate": 0,
#     "diagnostic_fee": 0,
#     "urgency_factor": 1.0,
#     "replacement_material_cost": 0,
#     "installation_hours": 0,
#     "delivery_fee": 0,
#     "disposal_fee": 0
#     }}
#     """


#     response = llm.invoke(prompt)
#     content = response.content.strip()
#     if content.startswith("```"):
#         content = content.strip("`")
#         if content.startswith("json"):
#             content = content[4:]
#     try:
#         return json.loads(content)
#     except Exception:
#         log.warning("Could not parse LLM JSON, defaulting: %s", content)
#         # return {"repair_cost": 500, "replacement_cost": 1000, "labor_cost": 200, "material_cost": 300}
#         return {
#         "repair_cost": 500,
#         "replacement_cost": 1000,
#         "material_cost": 300,
#         "labor_hours": 2,
#         "labor_rate": 100,
#         "diagnostic_fee": 50,
#         "urgency_factor": 1.0,
#         "replacement_material_cost": 700,
#         "installation_hours": 3,
#         "delivery_fee": 50,
#         "disposal_fee": 25,
#         }

# def compare_repair_vs_replace(claim_number: str, item_age: int, useful_life_remaining: int) -> dict:
#     # Look up existing repair_costs/replacement_costs for this claim+item_type, if present
#     claim_id = get_claim_id(claim_number)
#     damage = get_damage_item(claim_number)
#     damage_id = damage["damage_id"]
#     item_type = damage["category"]
#     severity = damage["severity"]
#     estimated_cost = damage["estimated_cost"]
#     adjuster_notes = damage["adjuster_notes"]
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM repair_costs WHERE claim_id = %s AND item_type = %s ORDER BY id DESC LIMIT 1",
#             (claim_id, item_type),
#         )
#         repair_row = row_to_dict(cur.fetchone())
#         cur.execute(
#             "SELECT * FROM replacement_costs WHERE claim_id = %s AND item_type = %s ORDER BY id DESC LIMIT 1",
#             (claim_id, item_type),
#         )
#         replacement_row = row_to_dict(cur.fetchone())
#     finally:
#         conn.close()

#     if repair_row and replacement_row:
#         repair_cost = float(repair_row["total_repair_estimate"])
#         replacement_cost = float(replacement_row["total_replacement_estimate"])
#         labor_cost = float(repair_row.get("labor_hours") or 0) * float(repair_row.get("labor_rate") or 0)
#         material_cost = float(repair_row.get("material_cost") or 0)
#     else:
#         # ai_costs = _llm_estimate_costs(item_type, item_age)
#         ai_costs = _llm_estimate_costs(
#         item_type,
#         item_age,
#         severity,
#         estimated_cost,
#         adjuster_notes,
#         )
#         repair_cost = float(ai_costs.get("repair_cost", 500))
#         replacement_cost = float(ai_costs.get("replacement_cost", 1000))
#         # labor_cost = float(ai_costs.get("labor_cost", 200))
#         labor_cost = (
#         float(ai_costs["labor_hours"]) *
#         float(ai_costs["labor_rate"])
#         )
#         material_cost = float(ai_costs.get("material_cost", 300))




#         repair_result = write_repair_cost(

#             item_id=damage_id,

#             claim_number=claim_number,

#             item_type=item_type,

#             material_cost=ai_costs["material_cost"],

#             labor_hours=ai_costs["labor_hours"],

#             labor_rate=ai_costs["labor_rate"],

#             diagnostic_fee=ai_costs["diagnostic_fee"],

#             urgency_factor=ai_costs["urgency_factor"],

#         )
        
#         repair_cost = repair_result["total_repair_estimate"]


#         replacement_result = write_replacement_cost(

#             item_id=damage_id,

#             claim_number=claim_number,

#             item_type=item_type,

#             replacement_material_cost=ai_costs["replacement_material_cost"],

#             installation_hours=ai_costs["installation_hours"],

#             labor_rate=ai_costs["labor_rate"],

#             delivery_fee=ai_costs["delivery_fee"],

#             disposal_fee=ai_costs["disposal_fee"],

#         )
#         replacement_cost = replacement_result["total_replacement_estimate"]
 


#     if repair_cost > 0.6 * replacement_cost or item_age >= useful_life_remaining:
#         recommendation = "Replace"
#     else:
#         recommendation = "Repair"

#     # Confidence heuristic: bigger gap between costs => more confident
#     if replacement_cost > 0:
#         ratio_gap = abs(repair_cost - replacement_cost) / replacement_cost
#     else:
#         ratio_gap = 0
#     confidence_score = round(min(1.0, 0.5 + ratio_gap), 2)

#     estimate = write_estimate(
#         claim_number, item_type, item_age, useful_life_remaining, repair_cost, replacement_cost,
#         labor_cost, material_cost, recommendation, confidence_score,
#     )




#     ai_message = (
#         f"For claim {claim_number}, the recommendation is to "
#         f"{recommendation} the damaged item of type {item_type}. "
#         f"The item age is {item_age} years with "
#         f"{useful_life_remaining} years of useful life remaining. "
#         f"The estimated repair cost is ${repair_cost:,.2f} while "
#         f"the replacement cost is ${replacement_cost:,.2f}. "
#         f"The confidence score is {confidence_score}. "
#         f"The recommendation is based on the insurer's repair-vs-replacement business rule."
#     )
#     # write_repair_vs_replacement_decision(
#     #     claim_number=claim_number,
#     #     recommended_action=recommendation,
#     #     ai_generated_message=ai_message,
#     # )


#     return {
#         "claim_id": claim_id,
#         "item_type": item_type,
#         "item_age": item_age,
#         "useful_life_remaining": useful_life_remaining,
#         "repair_cost": repair_cost,
#         "replacement_cost": replacement_cost,
#         "recommendation": recommendation,
#         "confidence_score": confidence_score,
#         "estimate": estimate,
#         "ai_generated_message":ai_message,
#     }













"""
handler.py — Repair vs Replacement
───────────────────────────────────────
Compares repair vs. replacement costs for a damaged item and recommends a
course of action based on a cost-ratio / useful-life rule.
"""

import json
import logging
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402


from datetime import datetime
import pytz


log = logging.getLogger(__name__)


def get_claim_id(claim_number: str) -> int:
#    claim_id = get_claim_id(claim_number)
   conn = get_db_connection()
   try:
       cur = conn.cursor()
       cur.execute(
           """
           SELECT id
           FROM claims
           WHERE claim_number = %s
           """,
           (claim_number,),
       )
       row = row_to_dict(cur.fetchone())
       if not row:
           raise ValueError(f"Claim '{claim_number}' not found")
       return row["id"]
   finally:
       conn.close()


def get_damage_items(claim_number: str) -> list:
   conn = get_db_connection()
   try:
       cur = conn.cursor()
       cur.execute(
           """
           SELECT *
           FROM damage_items
           WHERE claim_number = %s
           ORDER BY damage_id
           """,
           (claim_number,),
       )
       rows = row_to_dict(cur.fetchall())
    #    if not row:
    #        raise ValueError(
    #            f"No damage item found for claim '{claim_number}'"
    #        )
       if not rows:
          raise ValueError(
            f"Damage assessment has not been completed for claim {claim_number}. "
            "Repair vs Replacement cannot be performed until damage items are available."
           )
       return rows
   finally:
       conn.close()

def _get_llm():
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def get_estimates(claim_number: str) -> list:
    claim_id = get_claim_id(claim_number)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM estimates WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def write_estimate(claim_number: str, item_type: str, item_age: int, useful_life_remaining: int,
                    repair_cost: float, replacement_cost: float, labor_cost: float, material_cost: float,
                    recommendation: str, confidence_score: float) -> dict:
    claim_id = get_claim_id(claim_number)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO estimates (
                claim_id, item_type, item_age, useful_life_remaining, repair_cost, replacement_cost,
                labor_cost, material_cost, recommendation, confidence_score
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (claim_id, item_type, item_age, useful_life_remaining, repair_cost, replacement_cost,
             labor_cost, material_cost, recommendation, confidence_score),
        )
        conn.commit()
        return {
            "id": cur.lastrowid, "claim_id": claim_id, "item_type": item_type, "item_age": item_age,
            "useful_life_remaining": useful_life_remaining, "repair_cost": repair_cost,
            "replacement_cost": replacement_cost, "labor_cost": labor_cost, "material_cost": material_cost,
            "recommendation": recommendation, "confidence_score": confidence_score,
        }
    finally:
        conn.close()


def get_repair_cost_detail(claim_number: str) -> list:
    claim_id = get_claim_id(claim_number)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM repair_costs WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def write_repair_cost(item_id: str, claim_number: str, item_type: str, material_cost: float, labor_hours: float,
                       labor_rate: float, diagnostic_fee: float, urgency_factor: float, notes: Optional[str] = None) -> dict:
    total_repair_estimate = round((material_cost + labor_hours * labor_rate + diagnostic_fee) * (urgency_factor or 1.0), 2)
    claim_id = get_claim_id(claim_number)
    conn = get_db_connection()
    
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO repair_costs (
                item_id, claim_id, item_type, material_cost, labor_hours, labor_rate,
                diagnostic_fee, urgency_factor, total_repair_estimate, notes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (item_id, claim_id, item_type, material_cost, labor_hours, labor_rate,
             diagnostic_fee, urgency_factor, total_repair_estimate, notes),
        )
        conn.commit()
        return {
            "id": cur.lastrowid, "item_id": item_id, "claim_id": claim_id, "item_type": item_type,
            "material_cost": material_cost, "labor_hours": labor_hours, "labor_rate": labor_rate,
            "diagnostic_fee": diagnostic_fee, "urgency_factor": urgency_factor,
            "total_repair_estimate": total_repair_estimate, "notes": notes,
        }
    finally:
        conn.close()


def get_replacement_cost_detail(claim_number: str) -> list:
    claim_id = get_claim_id(claim_number)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM replacement_costs WHERE claim_id = %s ORDER BY id DESC", (claim_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def write_replacement_cost(item_id: str, claim_number: str, item_type: str, replacement_material_cost: float,
                            installation_hours: float, labor_rate: float, delivery_fee: float, disposal_fee: float,
                            notes: Optional[str] = None) -> dict:
    total_replacement_estimate = round(
        replacement_material_cost + installation_hours * labor_rate + delivery_fee + disposal_fee, 2
    )
    claim_id = get_claim_id(claim_number)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO replacement_costs (
                item_id, claim_id, item_type, replacement_material_cost, installation_hours, labor_rate,
                delivery_fee, disposal_fee, total_replacement_estimate, notes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (item_id, claim_id, item_type, replacement_material_cost, installation_hours, labor_rate,
             delivery_fee, disposal_fee, total_replacement_estimate, notes),
        )
        conn.commit()
        return {
            "id": cur.lastrowid, "item_id": item_id, "claim_id": claim_id, "item_type": item_type,
            "replacement_material_cost": replacement_material_cost, "installation_hours": installation_hours,
            "labor_rate": labor_rate, "delivery_fee": delivery_fee, "disposal_fee": disposal_fee,
            "total_replacement_estimate": total_replacement_estimate, "notes": notes,
        }
    finally:
        conn.close()






# def update_repair_vs_replacement_decision(
#     claim_number: str,
#     decision: str,
# ) -> dict:
#     if decision not in ["Repair", "Replace"]:
#         raise ValueError(
#             "Decision must be either 'Repair' or 'Replace'."
#         )
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         # Verify recommendation row exists
#         cur.execute(
#             """
#             SELECT *
#             FROM repair_vs_replacement_decisions
#             WHERE claim_id = %s
#             """,
#             (claim_number,),
#         )
#         row = row_to_dict(cur.fetchone())
#         if not row:
#             raise ValueError(
#                 f"No Repair vs Replacement recommendation exists for claim '{claim_number}'."
#             )
#         cur.execute(
#             """
#             UPDATE repair_vs_replacement_decisions
#             SET decision = %s
#             WHERE claim_id = %s
#             """,
#             (
#                 decision,
#                 claim_number,
#             ),
#         )
#         conn.commit()
#         return {
#             "claim_number": claim_number,
#             "decision": decision,
#             "message": "Adjuster decision recorded successfully."
#         }
#     finally:
#         conn.close()






def update_repair_vs_replacement_decision(
    claim_number: str,
    decision: str,
) -> dict:
    decision = decision.strip().capitalize()
    if decision not in ["Repair", "Replace"]:
        raise ValueError(
            "Decision must be either 'Repair' or 'Replace'."
        )
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id
            FROM repair_vs_replacement_decisions
            WHERE claim_id=%s
            """,
            (claim_number,),
        )
        row = row_to_dict(cur.fetchone())
        if not row:
            raise ValueError(
                f"No recommendation exists for claim '{claim_number}'."
            )
        ist = pytz.timezone("Asia/Kolkata")
        current_time = datetime.now(ist)
        cur.execute(
            """
            UPDATE repair_vs_replacement_decisions
            SET
                decision=%s,
                timestamp=%s
            WHERE claim_id=%s
            """,
            (
                decision,
                current_time,
                claim_number,
            ),
        )
        conn.commit()
        return {
            "claim_number": claim_number,
            "decision": decision,
            "message": "Adjuster decision recorded successfully."
        }
    finally:
        conn.close()







def write_repair_vs_replacement_decision(
    claim_number: str,
    recommended_action: str,
    ai_generated_message: str,
) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Verify claim exists and fetch policyholder
        cur.execute(
            """
            SELECT
                claim_number,
                policyholder_name
            FROM claims
            WHERE claim_number = %s
            """,
            (claim_number,),
        )
        row = row_to_dict(cur.fetchone())
        if not row:
            raise ValueError(f"Claim '{claim_number}' not found")
        ist = pytz.timezone("Asia/Kolkata")
        current_time = datetime.now(ist)
        
        





        cur.execute(
            """
            SELECT id
            FROM repair_vs_replacement_decisions
            WHERE claim_id=%s
            """,
            (claim_number,),
        )
        existing = row_to_dict(cur.fetchone())
        if existing:
            return {
                "status" : "already_exists",
                "claim_number": claim_number,
                "message": "Recommendation already recorded."
            }




        cur.execute(
            """
            INSERT INTO repair_vs_replacement_decisions
            (
                claim_id,
                customer_name,
                communication_type,
                ai_generated_message,
                recommended_action,
                sent_method,
                timestamp,
                decision
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s,%s,%s
            )
            """,
            (
                row["claim_number"],
                row["policyholder_name"],
                "email",
                ai_generated_message,
                recommended_action,
                "email",
                current_time,
                "Adjuster review",
            ),
        )
        conn.commit()
        return {
            "claim_number": row["claim_number"],
            "customer_name": row["policyholder_name"],
            "recommended_action": recommended_action,
        }
    finally:
        conn.close()



# def _llm_estimate_costs(item_type: str, item_age: int) -> dict:
def _llm_estimate_costs(
   item_type: str,
   item_age: int,
   severity: str,
   estimated_cost: float,
   adjuster_notes: str,
) -> dict:
    llm = _get_llm()
#     prompt = f"""
# You are a claims adjuster's assistant. Estimate plausible repair and
# replacement costs in USD for a "{item_type}" that is {item_age} years old.
# Respond with ONLY a JSON object:
# {{"repair_cost": 0, "replacement_cost": 0, "labor_cost": 0, "material_cost": 0}}
# """


# prompt = f"""
# You are an insurance claims cost estimator.
# Estimate realistic repair and replacement costs for a damaged "{item_type}"
# that is {item_age} years old.
# Return ONLY valid JSON.
# {{
#    "repair_cost": 0,
#    "replacement_cost": 0,
#    "material_cost": 0,
#    "labor_hours": 0,
#    "labor_rate": 0,
#    "diagnostic_fee": 0,
#    "urgency_factor": 1.0,
#    "replacement_material_cost": 0,
#    "installation_hours": 0,
#    "delivery_fee": 0,
#    "disposal_fee": 0
# }}
# """


    prompt = f"""
    You are an insurance claims cost estimator.
    Estimate realistic repair and replacement costs for the damaged item using the following information.
    Item Type: {item_type}
    Item Age: {item_age} years
    Damage Severity: {severity}
    Adjuster's Notes: {adjuster_notes}
    Initial Damage Estimate: ${estimated_cost}
    Return ONLY valid JSON.
    {{
    "repair_cost": 0,
    "replacement_cost": 0,
    "material_cost": 0,
    "labor_hours": 0,
    "labor_rate": 0,
    "diagnostic_fee": 0,
    "urgency_factor": 1.0,
    "replacement_material_cost": 0,
    "installation_hours": 0,
    "delivery_fee": 0,
    "disposal_fee": 0
    }}
    """


    response = llm.invoke(prompt)
    content = response.content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content)
    except Exception:
        log.warning("Could not parse LLM JSON, defaulting: %s", content)
        # return {"repair_cost": 500, "replacement_cost": 1000, "labor_cost": 200, "material_cost": 300}
        return {
        "repair_cost": 500,
        "replacement_cost": 1000,
        "material_cost": 300,
        "labor_hours": 2,
        "labor_rate": 100,
        "diagnostic_fee": 50,
        "urgency_factor": 1.0,
        "replacement_material_cost": 700,
        "installation_hours": 3,
        "delivery_fee": 50,
        "disposal_fee": 25,
        }

def compare_repair_vs_replace(claim_number: str, item_age: int, useful_life_remaining: int) -> dict:
    # Look up existing repair_costs/replacement_costs for this claim+item_type, if present
    claim_id = get_claim_id(claim_number)
    damage_items = get_damage_items(claim_number)
    # damage_id = damage["damage_id"]
    # item_type = damage["category"]
    # severity = damage["severity"]
    # estimated_cost = damage["estimated_cost"]
    # adjuster_notes = damage["adjuster_notes"]
    total_repair_cost = 0
    total_replacement_cost = 0
    total_material_cost = 0
    total_labor_cost = 0
    item_types = []

    # conn = get_db_connection()
    # try:
    #     cur = conn.cursor()
    #     cur.execute(
    #         "SELECT * FROM repair_costs WHERE claim_id = %s AND item_type = %s ORDER BY id DESC LIMIT 1",
    #         (claim_id, item_type),
    #     )
    #     repair_row = row_to_dict(cur.fetchone())
    #     cur.execute(
    #         "SELECT * FROM replacement_costs WHERE claim_id = %s AND item_type = %s ORDER BY id DESC LIMIT 1",
    #         (claim_id, item_type),
    #     )
    #     replacement_row = row_to_dict(cur.fetchone())
    # finally:
    #     conn.close()


    for damage in damage_items:
        damage_id = damage["damage_id"]
        item_type = damage["category"]


        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM repair_costs
                WHERE claim_id=%s
                AND item_type=%s
                ORDER BY id DESC
                LIMIT 1
                """,
                (claim_id, item_type),
            )
            repair_row = row_to_dict(cur.fetchone())
            cur.execute(
                """
                SELECT *
                FROM replacement_costs
                WHERE claim_id=%s
                AND item_type=%s
                ORDER BY id DESC
                LIMIT 1
                """,
                (claim_id, item_type),
            )
            replacement_row = row_to_dict(cur.fetchone())
        finally:
            conn.close()



        severity = damage["severity"]
        estimated_cost = damage["estimated_cost"]
        adjuster_notes = damage["adjuster_notes"]
        item_type = damage["category"]
        item_types.append(item_type)
    
    # all_item_type = ", ".join(item_types)

        if repair_row and replacement_row:
            # repair_cost = float(repair_row["total_repair_estimate"])
            # replacement_cost = float(replacement_row["total_replacement_estimate"])
            # labor_cost = float(repair_row.get("labor_hours") or 0) * float(repair_row.get("labor_rate") or 0)
            # material_cost = float(repair_row.get("material_cost") or 0)

            repair_cost = float(repair_row["total_repair_estimate"])
            replacement_cost = float(replacement_row["total_replacement_estimate"])
            labor_cost = (
            float(repair_row.get("labor_hours") or 0)
            * float(repair_row.get("labor_rate") or 0)
            )
            material_cost = float(repair_row.get("material_cost") or 0)
    

            total_repair_cost += repair_cost
            total_replacement_cost += replacement_cost
            total_labor_cost += labor_cost
            total_material_cost += material_cost
            # item_types.append(item_type)


        else:
            # ai_costs = _llm_estimate_costs(item_type, item_age)
            ai_costs = _llm_estimate_costs(
            item_type,
            item_age,
            severity,
            estimated_cost,
            adjuster_notes,
            )
            repair_cost = float(ai_costs.get("repair_cost", 500))
            replacement_cost = float(ai_costs.get("replacement_cost", 1000))
            # labor_cost = float(ai_costs.get("labor_cost", 200))
            labor_cost = (
            float(ai_costs["labor_hours"]) *
            float(ai_costs["labor_rate"])
            )
            material_cost = float(ai_costs.get("material_cost", 300))




            repair_result = write_repair_cost(

                item_id=damage_id,

                claim_number=claim_number,

                item_type=item_type,

                material_cost=ai_costs["material_cost"],

                labor_hours=ai_costs["labor_hours"],

                labor_rate=ai_costs["labor_rate"],

                diagnostic_fee=ai_costs["diagnostic_fee"],

                urgency_factor=ai_costs["urgency_factor"],

            )
            
            repair_cost = repair_result["total_repair_estimate"]


            replacement_result = write_replacement_cost(

                item_id=damage_id,

                claim_number=claim_number,

                item_type=item_type,

                replacement_material_cost=ai_costs["replacement_material_cost"],

                installation_hours=ai_costs["installation_hours"],

                labor_rate=ai_costs["labor_rate"],

                delivery_fee=ai_costs["delivery_fee"],

                disposal_fee=ai_costs["disposal_fee"],

            )
            replacement_cost = replacement_result["total_replacement_estimate"]
    

            labor_cost = (
            float(ai_costs["labor_hours"])
            * float(ai_costs["labor_rate"])
            )
            material_cost = float(ai_costs["material_cost"])
            total_repair_cost += repair_cost
            total_replacement_cost += replacement_cost
            total_labor_cost += labor_cost
            total_material_cost += material_cost
            # item_types.append(item_type)
    all_item_type = ", ".join(item_types)

    # if (

    #     total_repair_cost > 0.6 * total_replacement_cost

    #     or item_age >= useful_life_remaining

    # ):

    #     recommendation = "Replace"

    # else:

    #     recommendation = "Repair"



    if total_repair_cost < (total_replacement_cost * 0.40):
        recommendation = "Repair"
    elif total_replacement_cost <= (total_repair_cost * 1.25):
        recommendation = "Replace"
    elif useful_life_remaining < 3:
        recommendation = "Replace"
    else:
        recommendation = "Replace"



    if total_replacement_cost > 0:

        ratio_gap = abs(

            total_repair_cost - total_replacement_cost

        ) / total_replacement_cost

    else:

        ratio_gap = 0

    confidence_score = round(

        min(1.0, 0.5 + ratio_gap),

        2,

    )

    estimate = write_estimate(

        claim_number,

        all_item_type,

        item_age,

        useful_life_remaining,

        total_repair_cost,

        total_replacement_cost,

        total_labor_cost,

        total_material_cost,

        recommendation,

        confidence_score,

    )

    ai_message = (

        f"For claim {claim_number}, the recommendation is to "

        f"{recommendation} the damaged item(s): {all_item_type}. "

        f"The item age is {item_age} years with "

        f"{useful_life_remaining} years of useful life remaining. "

        f"The estimated repair cost is ${total_repair_cost:,.2f} while "

        f"the replacement cost is ${total_replacement_cost:,.2f}. "

        f"The confidence score is {confidence_score}. "

        f"The recommendation is based on the insurer's repair-vs-replacement business rule."

    )

    return {

        "claim_id": claim_id,

        "item_type": all_item_type,

        "item_age": item_age,

        "useful_life_remaining": useful_life_remaining,

        "repair_cost": total_repair_cost,

        "replacement_cost": total_replacement_cost,

        "recommendation": recommendation,

        "confidence_score": confidence_score,

        "estimate": estimate,

        "ai_generated_message": ai_message,

    }
 

        # if repair_cost > 0.6 * replacement_cost or item_age >= useful_life_remaining:
        #     recommendation = "Replace"
        # else:
        #     recommendation = "Repair"


        # if (

        # total_repair_cost > 0.6 * total_replacement_cost

        # or item_age >= useful_life_remaining

        # ):
    
        #     recommendation = "Replace"
        # else:
        #     recommendation = "Repair"

        # # Confidence heuristic: bigger gap between costs => more confident
        # if total_replacement_cost > 0:
        #     # ratio_gap = abs(repair_cost - replacement_cost) / replacement_cost
        #     ratio_gap = abs(
        #     total_repair_cost - total_replacement_cost) / total_replacement_cost
        # else:
        #     ratio_gap = 0
        # confidence_score = round(min(1.0, 0.5 + ratio_gap), 2)

        # # estimate = write_estimate(
        # #     claim_number, item_type, item_age, useful_life_remaining, repair_cost, replacement_cost,
        # #     labor_cost, material_cost, recommendation, confidence_score,
        # # )

        # estimate = write_estimate(
        # claim_number,
        # item_type,
        # item_age,
        # useful_life_remaining,
        # total_repair_cost,
        # total_replacement_cost,
        # total_labor_cost,
        # total_material_cost,
        # recommendation,
        # confidence_score,
        # )




        # ai_message = (
        #     f"For claim {claim_number}, the recommendation is to "
        #     f"{recommendation} the damaged item of type {item_type}. "
        #     f"The item age is {item_age} years with "
        #     f"{useful_life_remaining} years of useful life remaining. "
        #     f"The estimated repair cost is ${total_repair_cost:,.2f} while "
        #     f"the replacement cost is ${total_replacement_cost:,.2f}. "
        #     f"The confidence score is {confidence_score}. "
        #     f"The recommendation is based on the insurer's repair-vs-replacement business rule."
        # )
        # # write_repair_vs_replacement_decision(
        # #     claim_number=claim_number,
        # #     recommended_action=recommendation,
        # #     ai_generated_message=ai_message,
        # # )


        # return {
        #     "claim_id": claim_id,
        #     "item_type": item_type,
        #     "item_age": item_age,
        #     "useful_life_remaining": useful_life_remaining,
        #     "repair_cost": total_repair_cost,
        #     "replacement_cost": total_replacement_cost,
        #     "recommendation": recommendation,
        #     "confidence_score": confidence_score,
        #     "estimate": estimate,
        #     "ai_generated_message":ai_message,
        # }
