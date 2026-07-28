"""
handler.py — Duplicate Claim Check
───────────────────────────────────
Checks for potential duplicate FNOL/claim submissions for a given policy
by matching policy_number + normalized loss_type + date_of_loss (±3 days).
LLM description similarity is used to override the rule-based verdict:
  - Rule match + LLM says NOT similar → is_duplicate = False
  - Rule match + LLM says similar     → is_duplicate = True (confirmed)
  - Rule match + no description       → is_duplicate = True (rule only)
"""

import json
import logging
import os
from datetime import datetime, timedelta

import sys
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

# Canonical loss-type groups — any alias maps to the group's first element
_LOSS_TYPE_GROUPS = [
    ["fire", "fire damage", "house fire", "kitchen fire"],
    ["auto", "motor", "motor accident", "auto accident", "auto damage",
     "vehicle damage", "car accident", "collision"],
    ["theft", "burglary", "robbery", "stolen"],
    ["water damage", "flood", "flooding", "water leak", "pipe burst"],
    ["wind", "hail", "wind/hail", "storm", "tree damage"],
    ["liability", "third party", "bodily injury"],
    ["structural", "foundation", "collapse"],
]

_ALIAS_MAP: dict[str, str] = {}
for group in _LOSS_TYPE_GROUPS:
    canonical = group[0]
    for alias in group:
        _ALIAS_MAP[alias.lower()] = canonical


# def _normalize_loss_type(loss_type: str) -> str:
#     return _ALIAS_MAP.get((loss_type or "").lower().strip(), (loss_type or "").lower().strip())

def _normalize_loss_type(loss_type: str) -> str:
    if not loss_type:
        return ""

    normalized = (
        loss_type.lower()
        .strip()
        .replace("_", " ")        # handle water_damage
        .replace("-", " ")        # handle fire-damage
    )

    # collapse multiple spaces → single space
    normalized = " ".join(normalized.split())

    return _ALIAS_MAP.get(normalized, normalized)

def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


def _parse_date(date_str: str):
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str[:19], fmt)
        except (ValueError, TypeError):
            continue
    return None


def _trim_match(row: dict) -> dict:
    """Return only policyholder-safe fields from a claim/FNOL row."""
    return {
        "claim_number":      row.get("claim_number") or row.get("fnol_number"),
        "date_of_loss":      row.get("date_of_loss"),
        "loss_type":         row.get("loss_type"),
        "status":            row.get("status"),
        "short_description": row.get("short_description") or row.get("cause_of_loss"),
    }


# def check_duplicate_claim(
#     policy_number: str,
#     loss_type: str,
#     date_of_loss: str = None,
#     description: str = None,
# ) -> dict:
#     normalized_input = _normalize_loss_type(loss_type)
#     target_date = _parse_date(date_of_loss) if date_of_loss else None

#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT * FROM claims WHERE policy_number = %s",
#             (policy_number,),
#         )
#         claim_rows = row_to_dict(cur.fetchall()) or []

#         cur.execute(
#             "SELECT * FROM fnol_submissions WHERE policy_number = %s",
#             (policy_number,),
#         )
#         fnol_rows = row_to_dict(cur.fetchall()) or []
#     finally:
#         conn.close()

#     matches = []
#     for row in claim_rows + fnol_rows:
#         # Normalize stored loss_type before comparing
#         stored_loss = _normalize_loss_type(row.get("loss_type") or "")
#         if stored_loss != normalized_input:
#             continue

#         row_date = _parse_date(row.get("date_of_loss") or "")
#         if target_date and row_date:
#             if abs((row_date - target_date).days) <= 3:
#                 matches.append(row)
#         elif not target_date:
#             # No date provided — include all loss_type matches as loose matches
#             matches.append(row)

#     is_duplicate = len(matches) > 0
#     confidence = 0
#     similarity_note = None

#     if is_duplicate:
#         confidence = 70 if target_date else 40

#         if description:
#             try:
#                 client = _get_openai_client()
#                 existing_descriptions = [
#                     m.get("short_description") or m.get("cause_of_loss") or ""
#                     for m in matches
#                     if m.get("short_description") or m.get("cause_of_loss")
#                 ]

#                 if existing_descriptions:
#                     prompt = (
#                         "Compare the NEW loss description with the EXISTING claim "
#                         "description(s) below and respond with JSON: "
#                         '{"similar": true/false, "confidence": 0-100, "note": "<short note>"}.\n\n'
#                         f"NEW: {description}\n\nEXISTING: {existing_descriptions}"
#                     )
#                     response = client.chat.completions.create(
#                         model=AZURE_OPENAI_CHAT_DEPLOYMENT,
#                         messages=[{"role": "user", "content": prompt}],
#                         temperature=0.0,
#                         response_format={"type": "json_object"},
#                     )
#                     result = json.loads(response.choices[0].message.content)
#                     similarity_note = result.get("note")

#                     if result.get("similar"):
#                         # LLM confirms similarity — raise confidence
#                         confidence = max(confidence, result.get("confidence", confidence))
#                     else:
#                         # LLM says descriptions are unrelated — override rule match
#                         is_duplicate = False
#                         confidence = result.get("confidence", 20)
#             except Exception as e:
#                 log.warning("similarity check failed: %s", e)

#     return {
#         "is_duplicate": is_duplicate,
#         "matches": [_trim_match(m) for m in matches],
#         "confidence": confidence,
#         "similarity_note": similarity_note,
#     }


def check_duplicate_claim(
    policy_number: str,
    loss_type: str,
    date_of_loss: str = None,
    description: str = None,
) -> dict:

    normalized_input = _normalize_loss_type(loss_type)
    target_date = _parse_date(date_of_loss) if date_of_loss else None

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM claims WHERE policy_number = %s",
            (policy_number,),
        )
        claim_rows = row_to_dict(cur.fetchall()) or []

        cur.execute(
            "SELECT * FROM fnol_submissions WHERE policy_number = %s",
            (policy_number,),
        )
        fnol_rows = row_to_dict(cur.fetchall()) or []

    finally:
        conn.close()

    all_rows = claim_rows + fnol_rows

    same_loss_matches = []
    for row in all_rows:
        stored_loss = _normalize_loss_type(row.get("loss_type") or "")
        # if stored_loss == normalized_input:
        #     same_loss_matches.append(row)
        if not stored_loss:
            continue

    # DEFAULT RESPONSE
    decision = "CREATE"
    reason = "No similar claims found"
    confidence = 80
    matches = [_trim_match(m) for m in same_loss_matches]

    if same_loss_matches:

        # Sort by most recent
        same_loss_matches.sort(
            key=lambda x: x.get("date_of_loss") or "", reverse=True
        )

        latest = same_loss_matches[0]

        status = (latest.get("status") or "").lower()
        row_date = _parse_date(latest.get("date_of_loss"))

        # CASE 1: OPEN CLAIM → UPDATE ONLY
        if status in ["open", "in_progress", "pending", "submitted", "draft"]:
            decision = "UPDATE"
            reason = "An active claim already exists for this loss type. Please update it."
            confidence = 95

        # CASE 2: CLOSED / APPROVED CLAIM
        elif status in ["closed", "approved", "completed"]:

            if target_date and row_date:
                diff_days = abs((target_date - row_date).days)

                # 🔴 Within 7 days → BLOCK
                if diff_days <= 7:
                    decision = "BLOCK"
                    reason = "A similar claim was recently closed. Cannot create or update within 7 days."
                    confidence = 90

                # Beyond 7 days → NEW CLAIM
                else:
                    decision = "CREATE"
                    reason = "Previous claim is closed and beyond 7 days. New claim can be created."
                    confidence = 85

            else:
                # No date → safer to block
                decision = "BLOCK"
                reason = "A similar claim exists but date is required to determine eligibility."
                confidence = 70

    # OPTIONAL LLM SIMILARITY (only if not already BLOCK/UPDATE)
    similarity_note = None

    if decision == "CREATE" and description and same_loss_matches:
        try:
            client = _get_openai_client()

            existing_descriptions = [
                m.get("short_description") or m.get("cause_of_loss") or ""
                for m in same_loss_matches
                if m.get("short_description") or m.get("cause_of_loss")
            ]

            if existing_descriptions:
                prompt = (
                    "Compare the NEW loss description with the EXISTING claim "
                    "description(s) below and respond with JSON: "
                    '{"similar": true/false, "confidence": 0-100, "note": "<short note>"}.\n\n'
                    f"NEW: {description}\n\nEXISTING: {existing_descriptions}"
                )

                response = client.chat.completions.create(
                    model=AZURE_OPENAI_CHAT_DEPLOYMENT,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    response_format={"type": "json_object"},
                )

                result = json.loads(response.choices[0].message.content)
                similarity_note = result.get("note")

                #  If LLM says similar → BLOCK
                if result.get("similar"):
                    decision = "BLOCK"
                    reason = "Description is very similar to an existing claim."
                    confidence = max(confidence, result.get("confidence", 85))

        except Exception as e:
            log.warning("LLM similarity check failed: %s", e)

    return {
        "decision": decision,   # NEW FIELD (CREATE / UPDATE / BLOCK)
        "reason": reason,       #  human readable explanation
        "matches": matches,
        "confidence": confidence,
        "similarity_note": similarity_note,
    }
    log.info(
    f"ROW DEBUG → policy: {row.get('policy_number')} | "
    f"loss_raw: {row.get('loss_type')} | normalized: {stored_loss} | status: {status}")


def get_recent_claims_for_policy(policy_number: str, days: int = 90) -> list:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM claims
            WHERE policy_number = %s AND (date_of_loss IS NULL OR date_of_loss >= %s)
            ORDER BY filed_at DESC
            """,
            (policy_number, cutoff),
        )
        rows = row_to_dict(cur.fetchall()) or []
        return [_trim_match(r) for r in rows]
    finally:
        conn.close()
