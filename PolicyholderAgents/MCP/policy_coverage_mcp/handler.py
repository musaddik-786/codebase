# """
# handler.py — Policy Coverage Verification
# ──────────────────────────────────────────
# Functions:
#   gw_search_policy          Search Guidewire for a policy by number
#   gw_get_policy_coverages   Fetch full coverage detail from Guidewire
#   save_policy_details       Persist Guidewire policy data to local DB
#   get_policy_details        Read policy from local DB
#   verify_coverage           LLM-based coverage verdict for a claim
#   record_claim_payment      Record an approved payment and reduce remaining coverage
# """

# import json
# import logging
# import os
# import random
# import sys
# from datetime import datetime
# from zoneinfo import ZoneInfo

# sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

# from db import get_db_connection, row_to_dict  # noqa: E402
# from dotenv import load_dotenv, find_dotenv
# from openai import AzureOpenAI
# from policy_coverage_mcp import guidewire_client

# load_dotenv(find_dotenv())

# log = logging.getLogger(__name__)

# AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
# AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
# AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
# AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-claims")


# def _get_openai_client() -> AzureOpenAI:
#     return AzureOpenAI(
#         api_key=AZURE_OPENAI_API_KEY,
#         api_version=AZURE_OPENAI_API_VERSION,
#         azure_endpoint=AZURE_OPENAI_ENDPOINT,
#     )


# # ── Guidewire: Policy Search ──────────────────────────────────────────────────

# def gw_search_policy(policy_number: str) -> dict:
#     """
#     Search Guidewire PolicyCenter for the given policy number.
#     Returns found=True with normalised policy dict, or found=False with error.
#     """
#     try:
#         raw = guidewire_client.search_policy(policy_number)
#         parsed = guidewire_client.parse_policy_from_search(raw)

#         if not parsed:
#             return {
#                 "found": False,
#                 "policy": None,
#                 "error": f"No policy found in Guidewire for policy number '{policy_number}'.",
#                 "raw_gw_response": raw,
#             }

#         return {
#             "found": True,
#             "policy": parsed,
#             "error": None,
#             "raw_gw_response": raw,
#         }

#     except Exception as exc:
#         status_code = getattr(getattr(exc, "response", None), "status_code", None)
#         if status_code == 404:
#             return {
#                 "found": False,
#                 "policy": None,
#                 "error": f"Policy '{policy_number}' not found in Guidewire (HTTP 404).",
#                 "raw_gw_response": {},
#             }
#         log.exception("Guidewire policy search failed for %s", policy_number)
#         return {
#             "found": False,
#             "policy": None,
#             "error": f"Guidewire API error: {str(exc)}",
#             "raw_gw_response": {},
#         }


# # ── Guidewire: Policy Coverages ───────────────────────────────────────────────

# def gw_get_policy_coverages(policy_number: str) -> dict:
#     """
#     Fetch full coverage details for a policy from Guidewire.
#     Searches by policy number first, then fetches the detail record.
#     """
#     search_result = gw_search_policy(policy_number)
#     if not search_result["found"]:
#         return search_result

#     gw_policy_id = search_result["policy"]["gw_policy_id"]
#     try:
#         detail = guidewire_client.get_policy_coverages(gw_policy_id)
#         return {
#             "found": True,
#             "policy_id": gw_policy_id,
#             "coverage_detail": detail,
#             "error": None,
#         }
#     except Exception as exc:
#         log.exception("gw_get_policy_coverages failed for %s", gw_policy_id)
#         return {
#             "found": False,
#             "policy_id": gw_policy_id,
#             "coverage_detail": None,
#             "error": str(exc),
#         }


# # ── Local DB: Save & Read policy_details ─────────────────────────────────────

# def save_policy_details(policy_number: str) -> dict:
#     """
#     Fetch policy from Guidewire (search + coverage detail) and persist to the
#     local policy_details table.  Deductible, coverage limit, and exclusions are
#     extracted from the Guidewire coverage response where available.
#     """
#     search_result = gw_search_policy(policy_number)
#     if not search_result["found"]:
#         return search_result

#     policy = search_result["policy"]
#     gw_policy_id = policy.get("gw_policy_id")
#     effective_date = policy.get("effective_date")
#     expiration_date = policy.get("expiration_date")
#     insured_name = policy.get("insured_name")
#     account_number = policy.get("account_number")
#     policy_address = policy.get("insured_address") or (
#         policy.get("raw", {})
#         .get("data", [{}])[0]
#         .get("attributes", {})
#         .get("policyAddress")
#     )

#     coverage_result = gw_get_policy_coverages(policy_number)
#     attrs = {}
#     if coverage_result.get("found"):
#         attrs = (
#             coverage_result
#             .get("coverage_detail", {})
#             .get("data", {})
#             .get("attributes", {})
#         )

#     state = attrs.get("baseState", {}).get("name") if isinstance(attrs.get("baseState"), dict) else None
#     term_type = attrs.get("termType", {}).get("name") if isinstance(attrs.get("termType"), dict) else None
#     premium_amount = (attrs.get("totalPremium") or {}).get("amount") if isinstance(attrs.get("totalPremium"), dict) else None
#     currency = (attrs.get("preferredCoverageCurrency") or {}).get("code") if isinstance(attrs.get("preferredCoverageCurrency"), dict) else None

#     addr = attrs.get("policyAddress") or {}
#     city = addr.get("city") if isinstance(addr, dict) else None
#     country = addr.get("country") if isinstance(addr, dict) else None
#     postal_code = addr.get("postalCode") if isinstance(addr, dict) else None

#     product_name = (attrs.get("product") or {}).get("displayName", "") if isinstance(attrs.get("product"), dict) else ""
#     coverage_type = "Homeowners" if "Homeowners" in product_name else (product_name or policy.get("product_name", ""))
#     status = "Active" if coverage_result.get("found") else (policy.get("status") or "Unknown")

#     # Extract deductible, coverage limit, and exclusions from Guidewire coverage lines
#     deductible = None
#     coverage_limit = None
#     exclusions_list = []

#     lines_data = (attrs.get("lines") or {}).get("data", []) if isinstance(attrs.get("lines"), dict) else []
#     for line in lines_data:
#         line_attrs = line.get("attributes", {}) if isinstance(line, dict) else {}
#         coverages_data = (line_attrs.get("coverages") or {}).get("data", []) if isinstance(line_attrs.get("coverages"), dict) else []
#         for cov in coverages_data:
#             cov_attrs = cov.get("attributes", {}) if isinstance(cov, dict) else {}
#             # Deductible — take the first non-null value found
#             if deductible is None:
#                 ded = cov_attrs.get("deductible") or {}
#                 if isinstance(ded, dict) and ded.get("amount") is not None:
#                     try:
#                         deductible = float(ded["amount"])
#                     except (TypeError, ValueError):
#                         pass
#             # Coverage limit
#             if coverage_limit is None:
#                 lim = cov_attrs.get("coverageAmount") or cov_attrs.get("limit") or {}
#                 if isinstance(lim, dict) and lim.get("amount") is not None:
#                     try:
#                         coverage_limit = float(lim["amount"])
#                     except (TypeError, ValueError):
#                         pass
#             # Exclusions
#             for excl in (cov_attrs.get("exclusions") or []):
#                 name = (excl.get("attributes") or {}).get("name") if isinstance(excl, dict) else None
#                 if name:
#                     exclusions_list.append(name)

#     exclusions = ",".join(exclusions_list) if exclusions_list else None

#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO policy_details (
#                 policy_id, gw_policy_id, status, coverage_type,
#                 deductible, coverage_limit, remaining_coverage_limit, exclusions,
#                 effective_date, expiration_date, premium_amount,
#                 insured_name, account_number, policy_address,
#                 state, term_type, currency, city, country, postal_code
#             ) VALUES (
#                 %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
#             )
#             ON CONFLICT (policy_id) DO UPDATE SET
#                 gw_policy_id = EXCLUDED.gw_policy_id,
#                 status = EXCLUDED.status,
#                 coverage_type = EXCLUDED.coverage_type,
#                 deductible = EXCLUDED.deductible,
#                 coverage_limit = EXCLUDED.coverage_limit,
#                 remaining_coverage_limit = COALESCE(
#                     policy_details.remaining_coverage_limit, EXCLUDED.coverage_limit
#                 ),
#                 exclusions = EXCLUDED.exclusions,
#                 effective_date = EXCLUDED.effective_date,
#                 expiration_date = EXCLUDED.expiration_date,
#                 premium_amount = EXCLUDED.premium_amount,
#                 insured_name = EXCLUDED.insured_name,
#                 account_number = EXCLUDED.account_number,
#                 policy_address = EXCLUDED.policy_address,
#                 state = EXCLUDED.state,
#                 term_type = EXCLUDED.term_type,
#                 currency = EXCLUDED.currency,
#                 city = EXCLUDED.city,
#                 country = EXCLUDED.country,
#                 postal_code = EXCLUDED.postal_code
#             """,
#             (
#                 policy_number, gw_policy_id, status, coverage_type,
#                 deductible, coverage_limit, coverage_limit, exclusions,
#                 effective_date, expiration_date, premium_amount,
#                 insured_name, account_number, policy_address,
#                 state, term_type, currency, city, country, postal_code,
#             ),
#         )
#         conn.commit()
#     except Exception:
#         conn.rollback()
#         raise
#     finally:
#         conn.close()

#     return {
#         "saved": True,
#         "policy_id": policy_number,
#         "gw_policy_id": gw_policy_id,
#         "status": status,
#         "coverage_type": coverage_type,
#         "deductible": deductible,
#         "coverage_limit": coverage_limit,
#         "exclusions": exclusions,
#         "premium_amount": premium_amount,
#         "currency": currency,
#     }


# def get_policy_details(policy_id: str) -> dict:
#     """Read a policy record from the local policy_details table."""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM policy_details WHERE policy_id = %s", (policy_id,))
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# # ── Coverage Verification ─────────────────────────────────────────────────────

# def get_coverage_verification_result(claim_id: str) -> dict:
#     """
#     Read an existing coverage verification result for the claim.
#     Returns the record if found, or {"found": False} if none exists yet.
#     """
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM coverage_verification_results WHERE claim_id = %s",
#             (claim_id,),
#         )
#         row = row_to_dict(cur.fetchone())
#         if row:
#             return {"found": True, **row}
#         return {"found": False, "claim_id": claim_id}
#     finally:
#         conn.close()


# def verify_coverage(claim_id: str) -> dict:
#     """
#     Look up the claim and its linked policy from the local DB, send to the LLM
#     to determine the coverage verdict, and persist the result to
#     coverage_verification_results.
#     """
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_id,))
#         claim = row_to_dict(cur.fetchone())
#         if not claim:
#             return {"error": f"Claim {claim_id} not found"}

#         policy_id = claim.get("policy_number")
#         if not policy_id:
#             return {"error": "No policy_number on claim", "claim": claim}

#         cur.execute("SELECT * FROM policy_details WHERE policy_id = %s", (policy_id,))
#         policy = row_to_dict(cur.fetchone())
#         if not policy:
#             return {"error": f"Policy {policy_id} not found in local DB — run save_policy_details first", "claim": claim}
#     finally:
#         conn.close()

#     loss_type = claim.get("loss_type", "")
#     cause_of_loss = claim.get("detected_cause") or claim.get("cause_of_loss", "")
#     coverage_type = policy.get("coverage_type", "")
#     coverage_limit = float(policy.get("remaining_coverage_limit") or policy.get("coverage_limit") or 0)
#     deductible = float(policy.get("deductible") or 0)
#     exclusions_raw = policy.get("exclusions") or ""
#     exclusions = (
#         json.loads(exclusions_raw)
#         if isinstance(exclusions_raw, str) and exclusions_raw.startswith("[")
#         else [x.strip() for x in exclusions_raw.split(",") if x.strip()]
#     )
#     loss_amount = float(
#         claim.get("loss_amount") or claim.get("estimated_loss_amount") or claim.get("estimated_cost") or 0
#     )

#     try:
#         client = _get_openai_client()
#         prompt = (
#             "You are a policy coverage analyst. Determine whether the claim is covered. "
#             "Respond with JSON: "
#             '{"coverage_verdict": "Covered|Partially Covered|Not Covered|Needs Investigation", '
#             '"exclusion_triggered": true/false, '
#             '"exclusion_details": "...", '
#             '"net_payable": <number>, '
#             '"coverage_notes": "..."}.\n\n'
#             f"Policy Coverage Type: {coverage_type}\n"
#             f"Remaining Coverage Limit: {coverage_limit}\n"
#             f"Deductible: {deductible}\n"
#             f"Policy Exclusions: {exclusions}\n"
#             f"Claim Loss Type: {loss_type}\n"
#             f"Cause of Loss: {cause_of_loss}\n"
#             f"Estimated Loss Amount: {loss_amount}"
#         )
#         response = client.chat.completions.create(
#             model=AZURE_OPENAI_CHAT_DEPLOYMENT,
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.0,
#             response_format={"type": "json_object"},
#         )
#         llm_result = json.loads(response.choices[0].message.content)
#     except Exception as e:
#         log.warning("LLM coverage check failed: %s", e)
#         net_payable = max(0.0, loss_amount - deductible)
#         if coverage_limit:
#             net_payable = min(net_payable, coverage_limit)
#         llm_result = {
#             "coverage_verdict": "Needs Investigation",
#             "exclusion_triggered": False,
#             "exclusion_details": "",
#             "net_payable": net_payable,
#             "coverage_notes": "Automated LLM check failed; manual review needed",
#         }

#     conn2 = get_db_connection()
#     try:
#         cur2 = conn2.cursor()
#         cur2.execute(
#             """
#             INSERT INTO coverage_verification_results
#               (claim_id, policy_id, coverage_verdict, exclusion_triggered,
#                exclusion_details, net_payable, coverage_notes, verified_at)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
#             ON CONFLICT (claim_id) DO UPDATE SET
#               coverage_verdict = EXCLUDED.coverage_verdict,
#               exclusion_triggered = EXCLUDED.exclusion_triggered,
#               exclusion_details = EXCLUDED.exclusion_details,
#               net_payable = EXCLUDED.net_payable,
#               coverage_notes = EXCLUDED.coverage_notes,
#               verified_at = EXCLUDED.verified_at
#             """,
#             (
#                 claim_id, str(policy_id),
#                 llm_result.get("coverage_verdict"),
#                 llm_result.get("exclusion_triggered", False),
#                 llm_result.get("exclusion_details"),
#                 llm_result.get("net_payable"),
#                 llm_result.get("coverage_notes"),
#                 datetime.now(ZoneInfo("UTC")).isoformat(),
#             ),
#         )
#         conn2.commit()
#     except Exception as e:
#         conn2.rollback()
#         log.warning("Could not write coverage_verification_results: %s", e)
#     finally:
#         conn2.close()

#     return {
#         "claim_id": claim_id,
#         "policy_id": str(policy_id),
#         "coverage_type": coverage_type,
#         "remaining_coverage_limit": coverage_limit,
#         "deductible": deductible,
#         "loss_amount": loss_amount,
#         "exclusions": exclusions,
#         **llm_result,
#     }


# # ── Payment Tracking ──────────────────────────────────────────────────────────

# def record_claim_payment(
#     claim_id: str,
#     amount_paid: float,
#     approved_by: str = None,
#     notes: str = None,
# ) -> dict:
#     """
#     Record an approved claim payment and reduce the policy's remaining_coverage_limit
#     in the local policy_details table.

#     This tracks how much of the coverage has been consumed so future verify_coverage
#     calls use the correct remaining limit, not the original full limit.
#     """
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_id,))
#         claim = row_to_dict(cur.fetchone())
#     finally:
#         conn.close()

#     if not claim:
#         return {"error": f"Claim {claim_id} not found"}

#     policy_id = claim.get("policy_number")
#     if not policy_id:
#         return {"error": "No policy_number on claim"}

#     conn2 = get_db_connection()
#     try:
#         cur2 = conn2.cursor()
#         cur2.execute(
#             "SELECT coverage_limit, remaining_coverage_limit FROM policy_details WHERE policy_id = %s",
#             (policy_id,),
#         )
#         policy = row_to_dict(cur2.fetchone())
#     finally:
#         conn2.close()

#     if not policy:
#         return {"error": f"Policy {policy_id} not found in local DB — run save_policy_details first"}

#     coverage_before = float(
#         policy.get("remaining_coverage_limit") or policy.get("coverage_limit") or 0
#     )
#     coverage_after = max(0.0, coverage_before - amount_paid)

#     payment_id = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
#     payment_date = datetime.now(ZoneInfo("UTC")).isoformat()

#     conn3 = get_db_connection()
#     try:
#         cur3 = conn3.cursor()
#         cur3.execute(
#             """
#             INSERT INTO claim_payments (
#                 payment_id, claim_id, policy_id, amount_paid, payment_date,
#                 approved_by, payment_status, coverage_before, coverage_after, notes
#             ) VALUES (%s,%s,%s,%s,%s,%s,'Released',%s,%s,%s)
#             """,
#             (
#                 payment_id, claim_id, policy_id, amount_paid, payment_date,
#                 approved_by, coverage_before, coverage_after, notes,
#             ),
#         )
#         cur3.execute(
#             "UPDATE policy_details SET remaining_coverage_limit = %s WHERE policy_id = %s",
#             (coverage_after, policy_id),
#         )
#         cur3.execute(
#             "UPDATE claims SET status = 'Settled' WHERE claim_number = %s",
#             (claim_id,),
#         )
#         conn3.commit()
#     except Exception:
#         conn3.rollback()
#         raise
#     finally:
#         conn3.close()

#     return {
#         "payment_id": payment_id,
#         "claim_id": claim_id,
#         "policy_id": policy_id,
#         "amount_paid": amount_paid,
#         "coverage_before": coverage_before,
#         "coverage_after": coverage_after,
#         "payment_status": "Released",
#         "payment_date": payment_date,
#     }







# """
# handler.py — Policy Coverage Verification
# ──────────────────────────────────────────
# Functions:
#   gw_search_policy          Search Guidewire for a policy by number
#   gw_get_policy_coverages   Fetch full coverage detail from Guidewire
#   save_policy_details       Persist Guidewire policy data to local DB
#   get_policy_details        Read policy from local DB
#   verify_coverage           LLM-based coverage verdict for a claim
#   record_claim_payment      Record an approved payment and reduce remaining coverage
# """

# import json
# import logging
# import os
# import random
# import sys
# from datetime import datetime
# from zoneinfo import ZoneInfo

# sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

# from db import get_db_connection, row_to_dict  # noqa: E402
# from dotenv import load_dotenv, find_dotenv
# from openai import AzureOpenAI
# from policy_coverage_mcp import guidewire_client

# load_dotenv(find_dotenv())

# log = logging.getLogger(__name__)

# AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
# AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
# AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
# AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-claims")


# def _get_openai_client() -> AzureOpenAI:
#     return AzureOpenAI(
#         api_key=AZURE_OPENAI_API_KEY,
#         api_version=AZURE_OPENAI_API_VERSION,
#         azure_endpoint=AZURE_OPENAI_ENDPOINT,
#     )


# # ── Guidewire: Policy Search ──────────────────────────────────────────────────

# def gw_search_policy(policy_number: str) -> dict:
#     """
#     Search Guidewire PolicyCenter for the given policy number.
#     Returns found=True with normalised policy dict, or found=False with error.
#     """
#     try:
#         raw = guidewire_client.search_policy(policy_number)
#         parsed = guidewire_client.parse_policy_from_search(raw)

#         if not parsed:
#             return {
#                 "found": False,
#                 "policy": None,
#                 "error": f"No policy found in Guidewire for policy number '{policy_number}'.",
#                 "raw_gw_response": raw,
#             }

#         return {
#             "found": True,
#             "policy": parsed,
#             "error": None,
#             "raw_gw_response": raw,
#         }

#     except Exception as exc:
#         status_code = getattr(getattr(exc, "response", None), "status_code", None)
#         if status_code == 404:
#             return {
#                 "found": False,
#                 "policy": None,
#                 "error": f"Policy '{policy_number}' not found in Guidewire (HTTP 404).",
#                 "raw_gw_response": {},
#             }
#         log.exception("Guidewire policy search failed for %s", policy_number)
#         return {
#             "found": False,
#             "policy": None,
#             "error": f"Guidewire API error: {str(exc)}",
#             "raw_gw_response": {},
#         }


# # ── Guidewire: Policy Coverages ───────────────────────────────────────────────

# def gw_get_policy_coverages(policy_number: str) -> dict:
#     """
#     Fetch full coverage details for a policy from Guidewire.
#     Searches by policy number first, then fetches the detail record.
#     """
#     search_result = gw_search_policy(policy_number)
#     if not search_result["found"]:
#         return search_result

#     gw_policy_id = search_result["policy"]["gw_policy_id"]
#     try:
#         detail = guidewire_client.get_policy_coverages(gw_policy_id)
#         return {
#             "found": True,
#             "policy_id": gw_policy_id,
#             "coverage_detail": detail,
#             "error": None,
#         }
#     except Exception as exc:
#         log.exception("gw_get_policy_coverages failed for %s", gw_policy_id)
#         return {
#             "found": False,
#             "policy_id": gw_policy_id,
#             "coverage_detail": None,
#             "error": str(exc),
#         }


# # ── Local DB: Save & Read policy_details ─────────────────────────────────────

# def save_policy_details(policy_number: str) -> dict:
#     """
#     Fetch policy from Guidewire (search + coverage detail) and persist to the
#     local policy_details table.  Deductible, coverage limit, and exclusions are
#     extracted from the Guidewire coverage response where available.
#     """
#     search_result = gw_search_policy(policy_number)
#     if not search_result["found"]:
#         return search_result

#     policy = search_result["policy"]
#     gw_policy_id = policy.get("gw_policy_id")
#     effective_date = policy.get("effective_date")
#     expiration_date = policy.get("expiration_date")
#     insured_name = policy.get("insured_name")
#     account_number = policy.get("account_number")
#     policy_address = policy.get("insured_address") or (
#         policy.get("raw", {})
#         .get("data", [{}])[0]
#         .get("attributes", {})
#         .get("policyAddress")
#     )

#     coverage_result = gw_get_policy_coverages(policy_number)
#     attrs = {}
#     if coverage_result.get("found"):
#         attrs = (
#             coverage_result
#             .get("coverage_detail", {})
#             .get("data", {})
#             .get("attributes", {})
#         )

#     state = attrs.get("baseState", {}).get("name") if isinstance(attrs.get("baseState"), dict) else None
#     term_type = attrs.get("termType", {}).get("name") if isinstance(attrs.get("termType"), dict) else None
#     premium_amount = (attrs.get("totalPremium") or {}).get("amount") if isinstance(attrs.get("totalPremium"), dict) else None
#     currency = (attrs.get("preferredCoverageCurrency") or {}).get("code") if isinstance(attrs.get("preferredCoverageCurrency"), dict) else None

#     addr = attrs.get("policyAddress") or {}
#     city = addr.get("city") if isinstance(addr, dict) else None
#     country = addr.get("country") if isinstance(addr, dict) else None
#     postal_code = addr.get("postalCode") if isinstance(addr, dict) else None

#     product_name = (attrs.get("product") or {}).get("displayName", "") if isinstance(attrs.get("product"), dict) else ""
#     coverage_type = "Homeowners" if "Homeowners" in product_name else (product_name or policy.get("product_name", ""))
#     status = "Active" if coverage_result.get("found") else (policy.get("status") or "Unknown")

#     # Extract deductible, coverage limit, and exclusions from Guidewire coverage lines
#     deductible = None
#     coverage_limit = None
#     exclusions_list = []

#     lines_data = (attrs.get("lines") or {}).get("data", []) if isinstance(attrs.get("lines"), dict) else []
#     for line in lines_data:
#         line_attrs = line.get("attributes", {}) if isinstance(line, dict) else {}
#         coverages_data = (line_attrs.get("coverages") or {}).get("data", []) if isinstance(line_attrs.get("coverages"), dict) else []
#         for cov in coverages_data:
#             cov_attrs = cov.get("attributes", {}) if isinstance(cov, dict) else {}
#             # Deductible — take the first non-null value found
#             if deductible is None:
#                 ded = cov_attrs.get("deductible") or {}
#                 if isinstance(ded, dict) and ded.get("amount") is not None:
#                     try:
#                         deductible = float(ded["amount"])
#                     except (TypeError, ValueError):
#                         pass
#             # Coverage limit
#             if coverage_limit is None:
#                 lim = cov_attrs.get("coverageAmount") or cov_attrs.get("limit") or {}
#                 if isinstance(lim, dict) and lim.get("amount") is not None:
#                     try:
#                         coverage_limit = float(lim["amount"])
#                     except (TypeError, ValueError):
#                         pass
#             # Exclusions
#             for excl in (cov_attrs.get("exclusions") or []):
#                 name = (excl.get("attributes") or {}).get("name") if isinstance(excl, dict) else None
#                 if name:
#                     exclusions_list.append(name)

#     exclusions = ",".join(exclusions_list) if exclusions_list else None

#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO policy_details (
#                 policy_id, gw_policy_id, status, coverage_type,
#                 deductible, coverage_limit, remaining_coverage_limit, exclusions,
#                 effective_date, expiration_date, premium_amount,
#                 insured_name, account_number, policy_address,
#                 state, term_type, currency, city, country, postal_code
#             ) VALUES (
#                 %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
#             )
#             ON CONFLICT (policy_id) DO UPDATE SET
#                 gw_policy_id = EXCLUDED.gw_policy_id,
#                 status = EXCLUDED.status,
#                 coverage_type = EXCLUDED.coverage_type,
#                 deductible = EXCLUDED.deductible,
#                 coverage_limit = EXCLUDED.coverage_limit,
#                 remaining_coverage_limit = COALESCE(
#                     policy_details.remaining_coverage_limit, EXCLUDED.coverage_limit
#                 ),
#                 exclusions = EXCLUDED.exclusions,
#                 effective_date = EXCLUDED.effective_date,
#                 expiration_date = EXCLUDED.expiration_date,
#                 premium_amount = EXCLUDED.premium_amount,
#                 insured_name = EXCLUDED.insured_name,
#                 account_number = EXCLUDED.account_number,
#                 policy_address = EXCLUDED.policy_address,
#                 state = EXCLUDED.state,
#                 term_type = EXCLUDED.term_type,
#                 currency = EXCLUDED.currency,
#                 city = EXCLUDED.city,
#                 country = EXCLUDED.country,
#                 postal_code = EXCLUDED.postal_code
#             """,
#             (
#                 policy_number, gw_policy_id, status, coverage_type,
#                 deductible, coverage_limit, coverage_limit, exclusions,
#                 effective_date, expiration_date, premium_amount,
#                 insured_name, account_number, policy_address,
#                 state, term_type, currency, city, country, postal_code,
#             ),
#         )
#         conn.commit()
#     except Exception:
#         conn.rollback()
#         raise
#     finally:
#         conn.close()

#     return {
#         "saved": True,
#         "policy_id": policy_number,
#         "gw_policy_id": gw_policy_id,
#         "status": status,
#         "coverage_type": coverage_type,
#         "deductible": deductible,
#         "coverage_limit": coverage_limit,
#         "exclusions": exclusions,
#         "premium_amount": premium_amount,
#         "currency": currency,
#     }


# def get_policy_details(policy_id: str) -> dict:
#     """Read a policy record from the local policy_details table."""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM policy_details WHERE policy_id = %s", (policy_id,))
#         return row_to_dict(cur.fetchone())
#     finally:
#         conn.close()


# # ── Coverage Verification ─────────────────────────────────────────────────────

# def get_coverage_verification_result(claim_id: str) -> dict:
#     """
#     Read an existing coverage verification result for the claim.
#     Returns the record if found, or {"found": False} if none exists yet.
#     """
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM coverage_verification_results WHERE claim_id = %s",
#             (claim_id,),
#         )
#         row = row_to_dict(cur.fetchone())
#         if row:
#             return {"found": True, **row}
#         return {"found": False, "claim_id": claim_id}
#     finally:
#         conn.close()


# def verify_coverage(claim_id: str) -> dict:
#     """
#     Look up the claim and its linked policy from the local DB, send to the LLM
#     to determine the coverage verdict, and persist the result to
#     coverage_verification_results.
#     """
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_id,))
#         claim = row_to_dict(cur.fetchone())
#         if not claim:
#             return {"error": f"Claim {claim_id} not found"}

#         policy_id = claim.get("policy_number")
#         if not policy_id:
#             return {"error": "No policy_number on claim", "claim": claim}

#         cur.execute("SELECT * FROM policy_details WHERE policy_id = %s", (policy_id,))
#         policy = row_to_dict(cur.fetchone())
#         if not policy:
#             return {"error": f"Policy {policy_id} not found in local DB — run save_policy_details first", "claim": claim}
#     finally:
#         conn.close()

#     loss_type = claim.get("loss_type", "")
#     cause_of_loss = claim.get("detected_cause") or claim.get("cause_of_loss", "")
#     coverage_type = policy.get("coverage_type", "")
#     coverage_limit = float(policy.get("remaining_coverage_limit") or policy.get("coverage_limit") or 0)
#     deductible = float(policy.get("deductible") or 0)
#     exclusions_raw = policy.get("exclusions") or ""
#     exclusions = (
#         json.loads(exclusions_raw)
#         if isinstance(exclusions_raw, str) and exclusions_raw.startswith("[")
#         else [x.strip() for x in exclusions_raw.split(",") if x.strip()]
#     )
#     loss_amount = float(
#         claim.get("loss_amount") or claim.get("estimated_loss_amount") or claim.get("estimated_cost") or 0
#     )

#     try:
#         client = _get_openai_client()
#         prompt = (
#             "You are a policy coverage analyst. Determine whether the claim is covered. "
#             "Respond with JSON: "
#             '{"coverage_verdict": "Covered|Partially Covered|Not Covered|Needs Investigation", '
#             '"exclusion_triggered": true/false, '
#             '"exclusion_details": "...", '
#             '"net_payable": <number>, '
#             '"coverage_notes": "..."}.\n\n'
#             f"Policy Coverage Type: {coverage_type}\n"
#             f"Remaining Coverage Limit: {coverage_limit}\n"
#             f"Deductible: {deductible}\n"
#             f"Policy Exclusions: {exclusions}\n"
#             f"Claim Loss Type: {loss_type}\n"
#             f"Cause of Loss: {cause_of_loss}\n"
#             f"Estimated Loss Amount: {loss_amount}"
#         )
#         response = client.chat.completions.create(
#             model=AZURE_OPENAI_CHAT_DEPLOYMENT,
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.0,
#             response_format={"type": "json_object"},
#         )
#         llm_result = json.loads(response.choices[0].message.content)
#     except Exception as e:
#         log.warning("LLM coverage check failed: %s", e)
#         net_payable = max(0.0, loss_amount - deductible)
#         if coverage_limit:
#             net_payable = min(net_payable, coverage_limit)
#         llm_result = {
#             "coverage_verdict": "Needs Investigation",
#             "exclusion_triggered": False,
#             "exclusion_details": "",
#             "net_payable": net_payable,
#             "coverage_notes": "Automated LLM check failed; manual review needed",
#         }

#     conn2 = get_db_connection()
#     try:
#         cur2 = conn2.cursor()
#         cur2.execute(
#             """
#             INSERT INTO coverage_verification_results
#               (claim_id, policy_id, coverage_verdict, exclusion_triggered,
#                exclusion_details, net_payable, coverage_notes, verified_at)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
#             ON CONFLICT (claim_id) DO UPDATE SET
#               coverage_verdict = EXCLUDED.coverage_verdict,
#               exclusion_triggered = EXCLUDED.exclusion_triggered,
#               exclusion_details = EXCLUDED.exclusion_details,
#               net_payable = EXCLUDED.net_payable,
#               coverage_notes = EXCLUDED.coverage_notes,
#               verified_at = EXCLUDED.verified_at
#             """,
#             (
#                 claim_id, str(policy_id),
#                 llm_result.get("coverage_verdict"),
#                 llm_result.get("exclusion_triggered", False),
#                 llm_result.get("exclusion_details"),
#                 llm_result.get("net_payable"),
#                 llm_result.get("coverage_notes"),
#                 datetime.now(ZoneInfo("UTC")).isoformat(),
#             ),
#         )
#         conn2.commit()
#     except Exception as e:
#         conn2.rollback()
#         log.warning("Could not write coverage_verification_results: %s", e)
#     finally:
#         conn2.close()

#     return {
#         "claim_id": claim_id,
#         "policy_id": str(policy_id),
#         "coverage_type": coverage_type,
#         "remaining_coverage_limit": coverage_limit,
#         "deductible": deductible,
#         "loss_amount": loss_amount,
#         "exclusions": exclusions,
#         **llm_result,
#     }


# # ── Payment Tracking ──────────────────────────────────────────────────────────

# def record_claim_payment(
#     claim_id: str,
#     amount_paid: float,
#     approved_by: str = None,
#     notes: str = None,
# ) -> dict:
#     """
#     Record an approved claim payment and reduce the policy's remaining_coverage_limit
#     in the local policy_details table.

#     This tracks how much of the coverage has been consumed so future verify_coverage
#     calls use the correct remaining limit, not the original full limit.
#     """
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_id,))
#         claim = row_to_dict(cur.fetchone())
#     finally:
#         conn.close()

#     if not claim:
#         return {"error": f"Claim {claim_id} not found"}

#     policy_id = claim.get("policy_number")
#     if not policy_id:
#         return {"error": "No policy_number on claim"}

#     conn2 = get_db_connection()
#     try:
#         cur2 = conn2.cursor()
#         cur2.execute(
#             "SELECT coverage_limit, remaining_coverage_limit FROM policy_details WHERE policy_id = %s",
#             (policy_id,),
#         )
#         policy = row_to_dict(cur2.fetchone())
#     finally:
#         conn2.close()

#     if not policy:
#         return {"error": f"Policy {policy_id} not found in local DB — run save_policy_details first"}

#     coverage_before = float(
#         policy.get("remaining_coverage_limit") or policy.get("coverage_limit") or 0
#     )
#     coverage_after = max(0.0, coverage_before - amount_paid)

#     payment_id = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
#     payment_date = datetime.now(ZoneInfo("UTC")).isoformat()

#     conn3 = get_db_connection()
#     try:
#         cur3 = conn3.cursor()
#         cur3.execute(
#             """
#             INSERT INTO claim_payments (
#                 payment_id, claim_id, policy_id, amount_paid, payment_date,
#                 approved_by, payment_status, coverage_before, coverage_after, notes
#             ) VALUES (%s,%s,%s,%s,%s,%s,'Released',%s,%s,%s)
#             """,
#             (
#                 payment_id, claim_id, policy_id, amount_paid, payment_date,
#                 approved_by, coverage_before, coverage_after, notes,
#             ),
#         )
#         cur3.execute(
#             "UPDATE policy_details SET remaining_coverage_limit = %s WHERE policy_id = %s",
#             (coverage_after, policy_id),
#         )
#         cur3.execute(
#             "UPDATE claims SET status = 'Settled' WHERE claim_number = %s",
#             (claim_id,),
#         )
#         conn3.commit()
#     except Exception:
#         conn3.rollback()
#         raise
#     finally:
#         conn3.close()

#     return {
#         "payment_id": payment_id,
#         "claim_id": claim_id,
#         "policy_id": policy_id,
#         "amount_paid": amount_paid,
#         "coverage_before": coverage_before,
#         "coverage_after": coverage_after,
#         "payment_status": "Released",
#         "payment_date": payment_date,
#     }


# def get_claim_details(claim_id: str) -> dict:

#     """

#     Fetch claim details from the local claims table.

#     Used by the Policy Coverage Agent to obtain the linked policy number.

#     """

#     conn = get_db_connection()

#     try:

#         cur = conn.cursor()

#         cur.execute(

#             "SELECT * FROM claims WHERE claim_number = %s",

#             (claim_id,),

#         )

#         claim = row_to_dict(cur.fetchone())

#         if not claim:

#             return {

#                 "found": False,

#                 "claim_id": claim_id,

#                 "error": f"Claim '{claim_id}' not found"

#             }

#         return {

#             "found": True,

#             "claim": claim

#         }

#     finally:

#         conn.close()
 








"""
handler.py — Policy Coverage Verification
──────────────────────────────────────────
Functions:
  gw_search_policy          Search Guidewire for a policy by number
  gw_get_policy_coverages   Fetch full coverage detail from Guidewire
  save_policy_details       Persist Guidewire policy data to local DB
  get_policy_details        Read policy from local DB
  verify_coverage           LLM-based coverage verdict for a claim
  record_claim_payment      Record an approved payment and reduce remaining coverage
"""

import json
import logging
import os
import random
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from dotenv import load_dotenv, find_dotenv
from openai import AzureOpenAI
from policy_coverage_mcp import guidewire_client

load_dotenv(find_dotenv())

log = logging.getLogger(__name__)

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-claims")


def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


# ── Guidewire: Policy Search ──────────────────────────────────────────────────

def gw_search_policy(policy_number: str) -> dict:
    """
    Search Guidewire PolicyCenter for the given policy number.
    Returns found=True with normalised policy dict, or found=False with error.
    """
    try:
        raw = guidewire_client.search_policy(policy_number)
        parsed = guidewire_client.parse_policy_from_search(raw)

        if not parsed:
            return {
                "found": False,
                "policy": None,
                "error": f"No policy found in Guidewire for policy number '{policy_number}'.",
                "raw_gw_response": raw,
            }

        return {
            "found": True,
            "policy": parsed,
            "error": None,
            "raw_gw_response": raw,
        }

    except Exception as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code == 404:
            return {
                "found": False,
                "policy": None,
                "error": f"Policy '{policy_number}' not found in Guidewire (HTTP 404).",
                "raw_gw_response": {},
            }
        log.exception("Guidewire policy search failed for %s", policy_number)
        return {
            "found": False,
            "policy": None,
            "error": f"Guidewire API error: {str(exc)}",
            "raw_gw_response": {},
        }


# ── Guidewire: Policy Coverages ───────────────────────────────────────────────

def gw_get_policy_coverages(policy_number: str) -> dict:
    """
    Fetch full coverage details for a policy from Guidewire.
    Searches by policy number first, then fetches the detail record.
    """
    search_result = gw_search_policy(policy_number)
    if not search_result["found"]:
        return search_result

    gw_policy_id = search_result["policy"]["gw_policy_id"]
    try:
        detail = guidewire_client.get_policy_coverages(gw_policy_id)
        return {
            "found": True,
            "policy_id": gw_policy_id,
            "coverage_detail": detail,
            "error": None,
        }
    except Exception as exc:
        log.exception("gw_get_policy_coverages failed for %s", gw_policy_id)
        return {
            "found": False,
            "policy_id": gw_policy_id,
            "coverage_detail": None,
            "error": str(exc),
        }


# ── Local DB: Save & Read policy_details ─────────────────────────────────────

def save_policy_details(policy_number: str) -> dict:
    """
    Fetch policy from Guidewire (search + coverage detail) and persist to the
    local policy_details table.  Deductible, coverage limit, and exclusions are
    extracted from the Guidewire coverage response where available.
    """
    search_result = gw_search_policy(policy_number)
    if not search_result["found"]:
        return search_result

    policy = search_result["policy"]
    gw_policy_id = policy.get("gw_policy_id")
    effective_date = policy.get("effective_date")
    expiration_date = policy.get("expiration_date")
    policyholder_name = policy.get("policyholder_name")
    account_number = policy.get("account_number")
    policy_address = policy.get("policyholder_address") or (
        policy.get("raw", {})
        .get("data", [{}])[0]
        .get("attributes", {})
        .get("policyAddress")
    )

    coverage_result = gw_get_policy_coverages(policy_number)
    attrs = {}
    if coverage_result.get("found"):
        raw_detail = coverage_result.get("coverage_detail", {})
        log.info("[GW DEBUG] raw_detail top-level keys: %s", list(raw_detail.keys()) if isinstance(raw_detail, dict) else type(raw_detail).__name__)
        data_node = raw_detail.get("data", {}) if isinstance(raw_detail, dict) else {}
        log.info("[GW DEBUG] data_node type=%s", type(data_node).__name__)
        # Guidewire detail endpoint may return data as a dict (single record) or as a list
        if isinstance(data_node, list):
            log.info("[GW DEBUG] data is a LIST with %d items — taking first element", len(data_node))
            data_node = data_node[0] if data_node else {}
        attrs = data_node.get("attributes", {}) if isinstance(data_node, dict) else {}
        log.info("[GW DEBUG] attrs keys: %s", sorted(attrs.keys()))
        log.info("[GW DEBUG] totalPremium=%s  lines_type=%s", attrs.get("totalPremium"), type(attrs.get("lines")).__name__)
    else:
        log.warning("[GW DEBUG] gw_get_policy_coverages not found for %s: %s", policy_number, coverage_result.get("error"))

    state = attrs.get("baseState", {}).get("name") if isinstance(attrs.get("baseState"), dict) else None
    term_type = attrs.get("termType", {}).get("name") if isinstance(attrs.get("termType"), dict) else None
    premium_amount = (attrs.get("totalPremium") or {}).get("amount") if isinstance(attrs.get("totalPremium"), dict) else None
    currency = (attrs.get("preferredCoverageCurrency") or {}).get("code") if isinstance(attrs.get("preferredCoverageCurrency"), dict) else None

    addr = attrs.get("policyAddress") or {}
    city = addr.get("city") if isinstance(addr, dict) else None
    country = addr.get("country") if isinstance(addr, dict) else None
    postal_code = addr.get("postalCode") if isinstance(addr, dict) else None

    product_name = (attrs.get("product") or {}).get("displayName", "") if isinstance(attrs.get("product"), dict) else ""
    coverage_type = "Homeowners" if "Homeowners" in product_name else (product_name or policy.get("product_name", ""))
    status = "Active" if coverage_result.get("found") else (policy.get("status") or "Unknown")

    # Extract deductible, coverage limit, and exclusions from Guidewire coverage lines
    # deductible = None
    # coverage_limit = None
    # exclusions_list = []

    # lines_data = (attrs.get("lines") or {}).get("data", []) if isinstance(attrs.get("lines"), dict) else []
    # for line in lines_data:
    #     line_attrs = line.get("attributes", {}) if isinstance(line, dict) else {}
    #     coverages_data = (line_attrs.get("coverages") or {}).get("data", []) if isinstance(line_attrs.get("coverages"), dict) else []
    #     for cov in coverages_data:
    #         cov_attrs = cov.get("attributes", {}) if isinstance(cov, dict) else {}
    #         # Deductible — take the first non-null value found
    #         if deductible is None:
    #             ded = cov_attrs.get("deductible") or {}
    #             if isinstance(ded, dict) and ded.get("amount") is not None:
    #                 try:
    #                     deductible = float(ded["amount"])
    #                 except (TypeError, ValueError):
    #                     pass
    #         # Coverage limit
    #         if coverage_limit is None:
    #             lim = cov_attrs.get("coverageAmount") or cov_attrs.get("limit") or {}
    #             if isinstance(lim, dict) and lim.get("amount") is not None:
    #                 try:
    #                     # coverage_limit = float(lim["amount"])
    #                     coverage_limit = 500000
    #                 except (TypeError, ValueError):
    #                     pass
    #         # Exclusions
    #         for excl in (cov_attrs.get("exclusions") or []):
    #             name = (excl.get("attributes") or {}).get("name") if isinstance(excl, dict) else None
    #             if name:
    #                 exclusions_list.append(name)

    # exclusions = ",".join(exclusions_list) if exclusions_list else None







# Extract deductible, coverage limit, and exclusions from Guidewire coverage lines
    # deductible = None
    # coverage_limit = None
    # exclusions_list = []
    # lines_data = (attrs.get("lines") or {}).get("data", []) if isinstance(attrs.get("lines"), dict) else []
    # for line in lines_data:
    #     line_attrs = line.get("attributes", {}) if isinstance(line, dict) else {}
    #     coverages_data = (
    #         (line_attrs.get("coverages") or {}).get("data", [])
    #         if isinstance(line_attrs.get("coverages"), dict)
    #         else []
    #     )
    #     for cov in coverages_data:
    #         cov_attrs = cov.get("attributes", {}) if isinstance(cov, dict) else {}
    #         # Deductible
    #         if deductible is None:
    #             ded = cov_attrs.get("deductible") or {}
    #             if isinstance(ded, dict) and ded.get("amount") is not None:
    #                 try:
    #                     deductible = float(ded["amount"])
    #                 except (TypeError, ValueError):
    #                     pass
    #         # Coverage Limit
    #         if coverage_limit is None:
    #             lim = cov_attrs.get("coverageAmount") or cov_attrs.get("limit") or {}
    #             if isinstance(lim, dict) and lim.get("amount") is not None:
    #                 try:
    #                     coverage_limit = float(lim["amount"])
    #                 except (TypeError, ValueError):
    #                     pass
    #         # Exclusions
    #         for excl in (cov_attrs.get("exclusions") or []):
    #             name = (
    #                 (excl.get("attributes") or {}).get("name")
    #                 if isinstance(excl, dict)
    #                 else None
    #             )
    #             if name:
    #                 exclusions_list.append(name)
    # # Fallback ONLY if Guidewire did not provide a coverage limit
    # if coverage_limit is None:
    #     log.warning(
    #         "Guidewire did not return a coverage limit for policy %s. Using default PoC value 500000.",
    #         policy_number,
    #     )
    #     coverage_limit = 500000.0
    # exclusions = ",".join(exclusions_list) if exclusions_list else None








    # Extract deductible, coverage limit, and exclusions from Guidewire coverage lines
    deductible = None
    coverage_limit = None
    exclusions_list = []

    lines_data = (
        (attrs.get("lines") or {}).get("data", [])
        if isinstance(attrs.get("lines"), dict)
        else []
    )

    for line in lines_data:
        line_attrs = line.get("attributes", {}) if isinstance(line, dict) else {}

        coverages_data = (
            (line_attrs.get("coverages") or {}).get("data", [])
            if isinstance(line_attrs.get("coverages"), dict)
            else []
        )

        for cov in coverages_data:
            cov_attrs = cov.get("attributes", {}) if isinstance(cov, dict) else {}

            # Deductible from Guidewire
            if deductible is None:
                ded = cov_attrs.get("deductible") or {}
                if isinstance(ded, dict) and ded.get("amount") is not None:
                    try:
                        deductible = float(ded["amount"])
                    except (TypeError, ValueError):
                        pass

            # Coverage Limit from Guidewire
            if coverage_limit is None:
                lim = cov_attrs.get("coverageAmount") or cov_attrs.get("limit") or {}
                if isinstance(lim, dict) and lim.get("amount") is not None:
                    try:
                        coverage_limit = float(lim["amount"])
                    except (TypeError, ValueError):
                        pass

            # Exclusions
            for excl in (cov_attrs.get("exclusions") or []):
                name = (
                    (excl.get("attributes") or {}).get("name")
                    if isinstance(excl, dict)
                    else None
                )
                if name:
                    exclusions_list.append(name)

    # ------------------------------------------------------------------
    # PoC fallback logic when Guidewire does not provide values
    # ------------------------------------------------------------------
    coverage = (coverage_type or "").lower()

    if premium_amount is not None:
        premium_amount = float(premium_amount)

        # Coverage Limit
        # Industry benchmark: homeowners premium ≈ 0.7% of dwelling coverage → limit = premium / 0.007
        # Vehicle premium ≈ 3% of vehicle value → limit = premium / 0.03
        if coverage_limit is None:
            if "vehicle" in coverage:
                coverage_limit = round(premium_amount / 0.03, 2)
            elif "homeowners" in coverage or "personal" in coverage:
                coverage_limit = round(premium_amount / 0.007, 2)
            log.info(
                "Coverage limit not returned by Guidewire. Calculated value: %s",
                coverage_limit,
            )

        # Deductible
        # Homeowners: typically $1,000–$2,500; approximate as 1% of coverage limit
        # Vehicle: typically $500–$1,000; approximate as 1% of coverage limit
        if deductible is None:
            if coverage_limit is not None:
                deductible = round(coverage_limit * 0.01, 2)
            elif "vehicle" in coverage:
                deductible = round(premium_amount * 0.35, 2)
            elif "homeowners" in coverage or "personal" in coverage:
                deductible = round(premium_amount * 0.65, 2)
            log.info(
                "Deductible not returned by Guidewire. Calculated value: %s",
                deductible,
            )

    exclusions = ",".join(exclusions_list) if exclusions_list else None



    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO policy_details (
                policy_number, gw_policy_id, status, coverage_type,
                deductible, coverage_limit, remaining_coverage_limit, exclusions,
                effective_date, expiration_date, premium_amount,
                policyholder_name, account_number, policy_address,
                state, term_type, currency, city, country, postal_code
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
            )
            ON CONFLICT (policy_number) DO UPDATE SET
                gw_policy_id = EXCLUDED.gw_policy_id,
                status = EXCLUDED.status,
                coverage_type = EXCLUDED.coverage_type,
                deductible = EXCLUDED.deductible,
                coverage_limit = EXCLUDED.coverage_limit,
                remaining_coverage_limit = COALESCE(
                    policy_details.remaining_coverage_limit, EXCLUDED.coverage_limit
                ),
                exclusions = EXCLUDED.exclusions,
                effective_date = EXCLUDED.effective_date,
                expiration_date = EXCLUDED.expiration_date,
                premium_amount = EXCLUDED.premium_amount,
                policyholder_name = EXCLUDED.policyholder_name,
                account_number = EXCLUDED.account_number,
                policy_address = EXCLUDED.policy_address,
                state = EXCLUDED.state,
                term_type = EXCLUDED.term_type,
                currency = EXCLUDED.currency,
                city = EXCLUDED.city,
                country = EXCLUDED.country,
                postal_code = EXCLUDED.postal_code
            """,
            (
                policy_number, gw_policy_id, status, coverage_type,
                deductible, coverage_limit, coverage_limit, exclusions,
                effective_date, expiration_date, premium_amount,
                policyholder_name, account_number, policy_address,
                state, term_type, currency, city, country, postal_code,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "saved": True,
        "policy_number": policy_number,
        "gw_policy_id": gw_policy_id,
        "status": status,
        "coverage_type": coverage_type,
        "deductible": deductible,
        "coverage_limit": coverage_limit,
        "exclusions": exclusions,
        "premium_amount": premium_amount,
        "currency": currency,
    }


def get_policy_details(policy_number: str) -> dict:
    """Read a policy record from the local policy_details table."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM policy_details WHERE policy_number = %s", (policy_number,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


# ── Coverage Verification ─────────────────────────────────────────────────────

def get_coverage_verification_result(claim_id: str) -> dict:
    """
    Read an existing coverage verification result for the claim.
    Returns the record if found, or {"found": False} if none exists yet.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM coverage_verification_results WHERE claim_number = %s",
            (claim_id,),
        )
        row = row_to_dict(cur.fetchone())
        if row:
            return {"found": True, **row}
        return {"found": False, "claim_number": claim_id}
    finally:
        conn.close()


def verify_coverage(claim_id: str) -> dict:
    """
    Look up the claim and its linked policy from the local DB, send to the LLM
    to determine the coverage verdict, and persist the result to
    coverage_verification_results.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_id,))
        claim = row_to_dict(cur.fetchone())
        if not claim:
            return {"error": f"Claim {claim_id} not found"}

        policy_number = claim.get("policy_number")
        if not policy_number:
            return {"error": "No policy_number on claim", "claim": claim}

        cur.execute("SELECT * FROM policy_details WHERE policy_number = %s", (policy_number,))
        policy = row_to_dict(cur.fetchone())
        if not policy:
            return {"error": f"Policy {policy_number} not found in local DB — run save_policy_details first", "claim": claim}
    finally:
        conn.close()

    loss_type = claim.get("loss_type", "")
    cause_of_loss = claim.get("detected_cause") or claim.get("cause_of_loss", "")
    coverage_type = policy.get("coverage_type", "")
    coverage_limit = float(policy.get("remaining_coverage_limit") or policy.get("coverage_limit") or 0)
    deductible = float(policy.get("deductible") or 0)
    exclusions_raw = policy.get("exclusions") or ""
    exclusions = (
        json.loads(exclusions_raw)
        if isinstance(exclusions_raw, str) and exclusions_raw.startswith("[")
        else [x.strip() for x in exclusions_raw.split(",") if x.strip()]
    )
    loss_amount = float(
        claim.get("loss_amount") or claim.get("estimated_loss_amount") or claim.get("estimated_cost") or 0
    )

    try:
        client = _get_openai_client()
        prompt = (
            "You are a policy coverage analyst. Determine whether the claim is covered.\n"
            "IMPORTANT: If Estimated Loss Amount is 0 or not provided, the damage has not yet been assessed. "
            "Do NOT return 'Needs Investigation' solely because the loss amount is zero. "
            "Instead, evaluate whether the loss type and cause of loss are covered under the policy type "
            "and whether any exclusions apply. "
            "If covered with no exclusion triggered, return coverage_verdict='Covered - Pending Assessment' "
            "with net_payable=0 and coverage_notes explaining that the net payable will be calculated "
            "once the damage assessment is complete.\n"
            "Respond with JSON only: "
            '{"coverage_verdict": "Covered|Covered - Pending Assessment|Partially Covered|Not Covered|Needs Investigation", '
            '"exclusion_triggered": true/false, '
            '"exclusion_details": "...", '
            '"net_payable": <number>, '
            '"coverage_notes": "..."}.\n\n'
            f"Policy Coverage Type: {coverage_type}\n"
            f"Remaining Coverage Limit: {coverage_limit}\n"
            f"Deductible: {deductible}\n"
            f"Policy Exclusions: {exclusions}\n"
            f"Claim Loss Type: {loss_type}\n"
            f"Cause of Loss: {cause_of_loss}\n"
            f"Estimated Loss Amount: {loss_amount}"
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        llm_result = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.warning("LLM coverage check failed: %s", e)
        net_payable = max(0.0, loss_amount - deductible)
        if coverage_limit:
            net_payable = min(net_payable, coverage_limit)
        llm_result = {
            "coverage_verdict": "Needs Investigation",
            "exclusion_triggered": False,
            "exclusion_details": "",
            "net_payable": net_payable,
            "coverage_notes": "Automated LLM check failed; manual review needed",
        }

    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        cur2.execute(
            """
            INSERT INTO coverage_verification_results
              (claim_number, policy_number, coverage_verdict, exclusion_triggered,
               exclusion_details, net_payable, coverage_notes, verified_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (claim_number) DO UPDATE SET
              coverage_verdict = EXCLUDED.coverage_verdict,
              exclusion_triggered = EXCLUDED.exclusion_triggered,
              exclusion_details = EXCLUDED.exclusion_details,
              net_payable = EXCLUDED.net_payable,
              coverage_notes = EXCLUDED.coverage_notes,
              verified_at = EXCLUDED.verified_at
            """,
            (
                claim_id, str(policy_number),
                llm_result.get("coverage_verdict"),
                llm_result.get("exclusion_triggered", False),
                llm_result.get("exclusion_details"),
                llm_result.get("net_payable"),
                llm_result.get("coverage_notes"),
                datetime.now(ZoneInfo("UTC")).isoformat(),
            ),
        )
        conn2.commit()
    except Exception as e:
        conn2.rollback()
        log.warning("Could not write coverage_verification_results: %s", e)
    finally:
        conn2.close()

    return {
        "claim_number": claim_id,
        "policy_number": str(policy_number),
        "coverage_type": coverage_type,
        "remaining_coverage_limit": coverage_limit,
        "deductible": deductible,
        "loss_amount": loss_amount,
        "exclusions": exclusions,
        **llm_result,
    }


# ── Payment Tracking ──────────────────────────────────────────────────────────

def record_claim_payment(
    claim_id: str,
    amount_paid: float,
    approved_by: str = None,
    notes: str = None,
) -> dict:
    """
    Record an approved claim payment and reduce the policy's remaining_coverage_limit
    in the local policy_details table.

    This tracks how much of the coverage has been consumed so future verify_coverage
    calls use the correct remaining limit, not the original full limit.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_id,))
        claim = row_to_dict(cur.fetchone())
    finally:
        conn.close()

    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    policy_number = claim.get("policy_number")
    if not policy_number:
        return {"error": "No policy_number on claim"}

    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        cur2.execute(
            "SELECT coverage_limit, remaining_coverage_limit FROM policy_details WHERE policy_number = %s",
            (policy_number,),
        )
        policy = row_to_dict(cur2.fetchone())
    finally:
        conn2.close()

    if not policy:
        return {"error": f"Policy {policy_number} not found in local DB — run save_policy_details first"}

    coverage_before = float(
        policy.get("remaining_coverage_limit") or policy.get("coverage_limit") or 0
    )
    coverage_after = max(0.0, coverage_before - amount_paid)

    payment_id = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
    payment_date = datetime.now(ZoneInfo("UTC")).isoformat()

    conn3 = get_db_connection()
    try:
        cur3 = conn3.cursor()
        cur3.execute(
            """
            INSERT INTO claim_payments (
                payment_id, claim_number, policy_number, amount_paid, payment_date,
                approved_by, payment_status, coverage_before, coverage_after, notes
            ) VALUES (%s,%s,%s,%s,%s,%s,'Released',%s,%s,%s)
            """,
            (
                payment_id, claim_id, policy_number, amount_paid, payment_date,
                approved_by, coverage_before, coverage_after, notes,
            ),
        )
        cur3.execute(
            "UPDATE policy_details SET remaining_coverage_limit = %s WHERE policy_number = %s",
            (coverage_after, policy_number),
        )
        cur3.execute(
            "UPDATE claims SET status = 'Settled' WHERE claim_number = %s",
            (claim_id,),
        )
        conn3.commit()
    except Exception:
        conn3.rollback()
        raise
    finally:
        conn3.close()

    return {
        "payment_id": payment_id,
        "claim_number": claim_id,
        "policy_number": policy_number,
        "amount_paid": amount_paid,
        "coverage_before": coverage_before,
        "coverage_after": coverage_after,
        "payment_status": "Released",
        "payment_date": payment_date,
    }


def get_claim_details(claim_id: str) -> dict:

    """

    Fetch claim details from the local claims table.

    Used by the Policy Coverage Agent to obtain the linked policy number.

    """

    conn = get_db_connection()

    try:

        cur = conn.cursor()

        cur.execute(

            "SELECT * FROM claims WHERE claim_number = %s",

            (claim_id,),

        )

        claim = row_to_dict(cur.fetchone())

        if not claim:

            return {

                "found": False,

                "claim_id": claim_id,

                "error": f"Claim '{claim_id}' not found"

            }

        return {

            "found": True,

            "claim": claim

        }

    finally:

        conn.close()
 