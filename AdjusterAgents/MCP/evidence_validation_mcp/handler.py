"""
handler.py — Evidence Validation
──────────────────────────────────
Verifies evidence authenticity and completeness by cross-checking
evidence_items against required types for the claim's loss_type.

Issue 6 fix: Authenticity is determined from aggregated DB fraud signals
             (fraud_risk_snapshots, fraud_flags, ai_fraud_signals) rather
             than from LLM filename/text analysis.
Issue 7 fix: authenticity_flags in save_validation_result are validated
             against real DB evidence_ids before any status update.
             Hallucinated IDs are silently discarded.
Issue 8 fix: overall_status is set deterministically — "Suspicious" only
             when DB fraud signals exceed defined thresholds.
"""

import base64
import json
import logging
import os
import sys
from typing import Optional
from urllib.parse import unquote

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from azure.storage.blob import BlobServiceClient  # noqa: E402
from db import get_db_connection, row_to_dict  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

log = logging.getLogger(__name__)

# ── Claims bundle parity: 7 mandatory claim data fields (routes.ts line 312) ──
_MANDATORY_CLAIM_FIELDS = [
    ("policy_number",     "Policy Number"),
    ("policyholder_name", "Policyholder Name"),
    ("loss_type",         "Loss Type"),
    ("short_description", "Loss Description"),
    ("location",          "Loss Location"),
    ("date_of_loss",      "Date of Loss"),
    ("severity",          "Severity"),
]

# Blocking fields: missing either stops claim from proceeding (bundle routes.ts line 330)
_BLOCKING_CLAIM_FIELDS = {"short_description", "location"}

# Pass threshold from bundle (routes.ts line 321): completeness >= 85%
_DATA_COMPLETENESS_THRESHOLD = 85


def _check_claim_data_completeness(claim: dict) -> dict:
    """
    Checks the 7 mandatory claim data fields from the claims bundle (routes.ts line 312).
    Returns data_completeness_score, validation_passed (>=85%), blocking_failure flag,
    and failure_reasons list — matching the bundle's intake validation logic exactly.
    """
    completed = 0
    failure_reasons = []
    blocking_failure = False

    for field_key, field_label in _MANDATORY_CLAIM_FIELDS:
        value = claim.get(field_key)
        if value and str(value).strip():
            completed += 1
        else:
            failure_reasons.append(f"Missing mandatory field: {field_label}")
            if field_key in _BLOCKING_CLAIM_FIELDS:
                blocking_failure = True

    data_completeness_score = round((completed / len(_MANDATORY_CLAIM_FIELDS)) * 100, 1)
    validation_passed = not blocking_failure and data_completeness_score >= _DATA_COMPLETENESS_THRESHOLD

    return {
        "data_completeness_score": data_completeness_score,
        "mandatory_fields_total": len(_MANDATORY_CLAIM_FIELDS),
        "mandatory_fields_filled": completed,
        "validation_passed": validation_passed,
        "blocking_failure": blocking_failure,
        "failure_reasons": failure_reasons,
        "pass_threshold_percent": _DATA_COMPLETENESS_THRESHOLD,
    }


def _persist_intake_validation(claim_id: str, completeness: dict) -> None:
    """
    Persists _check_claim_data_completeness's result to claim_intake_validation
    so case-investigation.tsx's "Complete Claim Intake Validation" button can
    read it back later — this check was previously only ever computed
    in-memory inside run_evidence_validation's return value, never saved
    anywhere. Called directly as a side effect of run_evidence_validation
    (not a separate LLM tool call the orchestrator has to remember to make)
    for the same reliability reason as _write_image_authenticity_to_db above.
    Never clears a prior adjuster override just because the check reran.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO claim_intake_validation (
                claim_id, data_completeness_score, mandatory_fields_total,
                mandatory_fields_filled, validation_passed, blocking_failure,
                failure_reasons, checked_at, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
            ON CONFLICT (claim_id) DO UPDATE SET
                data_completeness_score = EXCLUDED.data_completeness_score,
                mandatory_fields_total = EXCLUDED.mandatory_fields_total,
                mandatory_fields_filled = EXCLUDED.mandatory_fields_filled,
                validation_passed = EXCLUDED.validation_passed,
                blocking_failure = EXCLUDED.blocking_failure,
                failure_reasons = EXCLUDED.failure_reasons,
                checked_at = NOW(),
                updated_at = NOW()
            """,
            (
                claim_id,
                completeness["data_completeness_score"],
                completeness["mandatory_fields_total"],
                completeness["mandatory_fields_filled"],
                completeness["validation_passed"],
                completeness["blocking_failure"],
                json.dumps(completeness["failure_reasons"]),
            ),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        log.warning("_persist_intake_validation failed for %s: %s", claim_id, e)
    finally:
        conn.close()


_REQUIRED_EVIDENCE_BY_LOSS_TYPE = {
    "fire":      ["Photos", "Fire Report", "Police Report", "Repair Estimate"],
    "water":     ["Photos", "Plumber Report", "Repair Estimate"],
    "auto":      ["Photos", "Police Report", "Repair Estimate", "Driver License"],
    "theft":     ["Police Report", "Inventory List", "Photos"],
    "liability": ["Incident Report", "Medical Records", "Witness Statement"],
    "flood":     ["Photos", "Weather Report", "Repair Estimate"],
    "wind":      ["Photos", "Weather Report", "Repair Estimate"],
    "medical":   ["Medical Records", "Doctor Statement", "Bills"],
}


def _get_required_evidence_types(loss_type: str) -> list:
    """Case-insensitive partial match so 'Water Damage' → 'water' rules."""
    lt = (loss_type or "").lower()
    for key, types in _REQUIRED_EVIDENCE_BY_LOSS_TYPE.items():
        if key in lt:
            return types
    return ["Photos", "Incident Report"]


def _get_llm():
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def get_evidence_items(claim_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM evidence_items WHERE claim_id = %s ORDER BY id DESC",
            (claim_id,),
        )
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def get_claim_documents(claim_id: str) -> list:
    """Return all documents uploaded for a claim from the shared documents table."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM documents WHERE claim_number = %s ORDER BY uploaded_at DESC",
            (claim_id,),
        )
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def get_damage_items(claim_id: str) -> list:
    """Return all damage items assessed for a claim from the damage_items table."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM damage_items WHERE claim_number = %s ORDER BY id DESC",
            (claim_id,),
        )
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


def get_active_fraud_flags(claim_id: str) -> dict:
    """
    Returns the actual fraud_flags table records for a claim where status = 'Active'.
    Each record includes: flag_type, flag_description, risk_score, detected_by, created_at.

    This is the authoritative source for adjuster-visible fraud flags — distinct from
    drone/weather/image authenticity findings that run_evidence_validation generates.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, claim_id, flag_type, flag_description, risk_score,
                      detected_by, status, flagged_at
               FROM fraud_flags
               WHERE claim_id = %s AND status = 'Active'
               ORDER BY id DESC""",
            (claim_id,),
        )
        flags = row_to_dict(cur.fetchall())
        return {
            "claim_id": claim_id,
            "active_flag_count": len(flags),
            "fraud_flags": flags,
            "note": (
                "These are actual fraud_flags table records. "
                "Weather/drone/image authenticity findings are separate — "
                "they are generated by run_evidence_validation, not stored here."
            ),
        }
    except Exception as exc:
        conn.rollback()
        log.error("get_active_fraud_flags failed for %s: %s", claim_id, exc)
        return {"claim_id": claim_id, "active_flag_count": 0, "fraud_flags": []}
    finally:
        conn.close()


def _get_fraud_signals(claim_id: str) -> dict:
    """
    Issue 6 & 8: Query DB tables for actual fraud signals rather than
    relying on LLM filename interpretation.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # fraud_risk_snapshots
        fraud_score = 0
        try:
            cur.execute(
                "SELECT fraud_score FROM fraud_risk_snapshots WHERE claim_id = %s ORDER BY created_at DESC LIMIT 1",
                (claim_id,),
            )
            row = cur.fetchone()
            fraud_score = int((row["fraud_score"] if row else 0) or 0)
        except Exception:
            conn.rollback()

        # active fraud_flags count
        flag_count = 0
        try:
            cur.execute(
                "SELECT COUNT(*) FROM fraud_flags WHERE claim_id = %s AND status = 'Active'",
                (claim_id,),
            )
            row = cur.fetchone()
            flag_count = int(row["count"] if row else 0)
        except Exception:
            conn.rollback()

        # ai_fraud_signals count
        signal_count = 0
        try:
            cur.execute(
                "SELECT COUNT(*) FROM ai_fraud_signals WHERE claim_id = %s",
                (claim_id,),
            )
            row = cur.fetchone()
            signal_count = int(row["count"] if row else 0)
        except Exception:
            conn.rollback()

        return {
            "fraud_score": fraud_score,
            "active_flag_count": flag_count,
            "ai_signal_count": signal_count,
        }
    except Exception:
        conn.rollback()
        return {"fraud_score": 0, "active_flag_count": 0, "ai_signal_count": 0}
    finally:
        conn.close()


def _determine_overall_status(
    completeness_pct: float,
    signals: dict,
    drone_fraud_score: int = 0,
    image_suspicious_count: int = 0,
) -> str:
    """
    Issue 8: Deterministic status from DB signals.
    'Suspicious' requires concrete DB fraud evidence — not LLM guessing.
    drone_fraud_score is blended via max() so the higher signal wins.
    image_suspicious_count: flagged images from GPT-4.1 vision analysis (>=1 → Suspicious).
    """
    fraud_score = signals.get("fraud_score", 0)
    flag_count = signals.get("active_flag_count", 0)
    signal_count = signals.get("ai_signal_count", 0)
    effective_score = max(fraud_score, drone_fraud_score)

    if effective_score >= 70 or flag_count >= 2 or signal_count >= 3 or image_suspicious_count >= 1:
        return "Suspicious"
    if completeness_pct >= 100:
        return "Complete"
    return "Incomplete"


def _get_drone_authenticity(claim_id: str) -> Optional[dict]:
    """Queries drone_authenticity_data for the claim. Returns None if no record."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM drone_authenticity_data WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        row = cur.fetchone()
        return row_to_dict(row) if row else None
    except Exception:
        conn.rollback()
        return None
    finally:
        conn.close()


def _get_weather_alignment(claim_id: str) -> Optional[dict]:
    """Queries weather_location_alignment for the claim. Returns None if no record."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM weather_location_alignment WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        row = cur.fetchone()
        return row_to_dict(row) if row else None
    except Exception:
        conn.rollback()
        return None
    finally:
        conn.close()


def _compute_drone_fraud_score(drone_data: dict) -> int:
    """
    Computes fraud risk score from drone_authenticity_data fields.
    Reference bundle formula (DroneVerification.tsx lines 399-408):

      score = 100 - drone_match_percent
      if tamper_indicator != "None":      score += 20
      if geo_match == "None":             score += 15
      elif geo_match == "Partial":        score += 8
      if damage_inflation_index == "High":    score += 15
      elif damage_inflation_index == "Medium": score += 8
      if weather_event_match == "No":     score += 10

      return min(100, max(0, score))

    Returns 0 if drone_data is None or empty.
    """
    if not drone_data:
        return 0

    try:
        drone_match_percent = float(drone_data.get("drone_match_percent") or 100)
        score = 100 - drone_match_percent

        tamper_indicator = str(drone_data.get("tamper_indicator") or "None")
        if tamper_indicator != "None":
            score += 20

        geo_match = str(drone_data.get("geo_match") or "")
        if geo_match == "None":
            score += 15
        elif geo_match == "Partial":
            score += 8

        damage_inflation_index = str(drone_data.get("damage_inflation_index") or "")
        if damage_inflation_index == "High":
            score += 15
        elif damage_inflation_index == "Medium":
            score += 8

        weather_event_match = str(drone_data.get("weather_event_match") or "Yes")
        if weather_event_match == "No":
            score += 10

        return int(min(100, max(0, score)))
    except Exception as e:
        log.warning("_compute_drone_fraud_score failed: %s", e)
        return 0


def _generate_drone_auto_flags(drone_data: dict, documents: list, weather_data: dict = None) -> list:
    """
    Generates authenticity_flags from drone data using reference bundle hard rules.

    RED FLAGS (auto_flag conditions):
      - drone_match_percent < 60   → "Auto-Fraud Red Flag: Drone Match < 60%"
      - tamper_indicator != "None" → "Red Flag: Image Tampering Detected"
      - geo_match == "None"        → "Red Flag: Geo Location Mismatch"

    AMBER FLAGS (warnings):
      - geo_match == "Partial"                         → "Warning: Partial Geo Location Match"
      - damage_inflation_index == "High"               → "Warning: High Damage Inflation Index"
      - weather_location_alignment.drone_weather_alignment != "Verified"
                                                       → "Warning: Weather Event Mismatch"

    Weather mismatch reads from weather_location_alignment.drone_weather_alignment (not
    drone_authenticity_data.weather_event_match), matching the reference DroneVerification.tsx.

    Each flag uses evidence_id from the first evidence item (if any).
    Returns list of dicts: [{evidence_id, concern, flag_type}]
    """
    if not drone_data:
        return []

    first_evidence_id = None
    if documents:
        first_evidence_id = documents[0].get("document_id")

    flags = []

    try:
        drone_match_percent = float(drone_data.get("drone_match_percent") or 100)
        if drone_match_percent < 60:
            flags.append({
                "evidence_id": first_evidence_id,
                "concern": "Auto-Fraud Red Flag: Drone Match < 60%",
                "flag_type": "red",
            })

        tamper_indicator = str(drone_data.get("tamper_indicator") or "None")
        if tamper_indicator != "None":
            flags.append({
                "evidence_id": first_evidence_id,
                "concern": "Red Flag: Image Tampering Detected",
                "flag_type": "red",
            })

        geo_match = str(drone_data.get("geo_match") or "")
        if geo_match == "None":
            flags.append({
                "evidence_id": first_evidence_id,
                "concern": "Red Flag: Geo Location Mismatch",
                "flag_type": "red",
            })
        elif geo_match == "Partial":
            flags.append({
                "evidence_id": first_evidence_id,
                "concern": "Warning: Partial Geo Location Match",
                "flag_type": "amber",
            })

        # Damage inflation amber flag (reference DroneVerification.tsx)
        damage_inflation_index = str(drone_data.get("damage_inflation_index") or "")
        if damage_inflation_index == "High":
            flags.append({
                "evidence_id": first_evidence_id,
                "concern": "Warning: High Damage Inflation Index",
                "flag_type": "amber",
            })

        # Weather mismatch: use weather_location_alignment.drone_weather_alignment
        # (reference DroneVerification.tsx reads selectedWeatherData.droneWeatherAlignment)
        drone_weather_alignment = None
        if weather_data:
            drone_weather_alignment = str(weather_data.get("drone_weather_alignment") or "")
        if drone_weather_alignment and drone_weather_alignment != "Verified":
            flags.append({
                "evidence_id": first_evidence_id,
                "concern": "Warning: Weather Event Mismatch",
                "flag_type": "amber",
            })

    except Exception as e:
        log.warning("_generate_drone_auto_flags failed: %s", e)

    return flags


# ── Image Authenticity Validation (GPT-4.1 Vision) ───────────────────────────

_IMAGE_RISK_ORDER = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


def _fetch_claim_image_docs(claim_number: str) -> list:
    """Return all image documents for the claim from the documents table."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM documents WHERE claim_number = %s AND content_type ILIKE 'image/%%' ORDER BY uploaded_at",
            (claim_number,),
        )
        return row_to_dict(cur.fetchall())
    except Exception:
        conn.rollback()
        return []
    finally:
        conn.close()


def _download_image_as_data_uri(file_url: str, content_type: str) -> Optional[str]:
    """Download a private Azure Blob image and return a base64 data URI."""
    try:
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
        container = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "claims-evidence")
        blob_service = BlobServiceClient.from_connection_string(conn_str)
        blob_name = unquote(file_url.split(f"/{container}/")[-1].split("?")[0])
        blob_client = blob_service.get_blob_client(container=container, blob=blob_name)
        data = blob_client.download_blob().readall()
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:{content_type};base64,{b64}"
    except Exception as e:
        log.warning("_download_image_as_data_uri failed for %s: %s", file_url, e)
        return None


def _write_image_authenticity_to_db(
    document_id: str, insights_dict: dict, investigation_notes: str, flagged: int
) -> None:
    """Persist authenticity analysis back to documents.insights / investigation_notes / flagged."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE documents
               SET insights = %s, investigation_notes = %s, flagged = %s
               WHERE document_id = %s""",
            (json.dumps(insights_dict), investigation_notes, flagged, document_id),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        log.warning("_write_image_authenticity_to_db failed for %s: %s", document_id, e)
    finally:
        conn.close()


def _analyze_single_image_authenticity(doc: dict, claim: dict) -> dict:
    """
    Download one image and call GPT-4.1 vision to assess authenticity across
    5 dimensions: AI generation, tampering, damage-claim consistency, staging
    risk, and environmental consistency.
    """
    document_id = doc.get("document_id", "")
    file_name = doc.get("file_name", "")
    file_url = doc.get("file_url", "")
    content_type = doc.get("content_type", "image/jpeg")
    file_size = doc.get("file_size", 0)

    base_result = {
        "document_id": document_id,
        "file_name": file_name,
        "authenticity_verdict": "Unknown",
        "confidence_score": 0,
        "ai_generation_indicators": [],
        "tampering_indicators": [],
        "damage_claim_consistency": "Unknown",
        "consistency_notes": "",
        "staging_risk": "Low",
        "overall_risk_level": "Low",
        "summary": "Image analysis could not be completed.",
        "flagged": 0,
    }

    data_uri = _download_image_as_data_uri(file_url, content_type)
    if not data_uri:
        base_result["summary"] = "Image could not be downloaded for analysis."
        return base_result

    loss_type = claim.get("loss_type") or "Other"
    short_description = claim.get("short_description") or "No description provided"
    severity = claim.get("severity") or "Unknown"
    date_of_loss = str(claim.get("date_of_loss") or "Unknown")

    prompt_text = (
        "You are an insurance fraud investigator specializing in image authenticity analysis.\n\n"
        "Analyze this image submitted as supporting evidence for an insurance claim.\n\n"
        "Claim Context:\n"
        f"- Loss Type: {loss_type}\n"
        f"- Claim Description: {short_description}\n"
        f"- Severity: {severity}\n"
        f"- Date of Loss: {date_of_loss}\n"
        f"- File Name: {file_name}\n"
        f"- File Size: {file_size} bytes\n\n"
        "Evaluate the image across these 5 dimensions:\n\n"
        "1. AI GENERATION INDICATORS — Look for: unnatural textures, perfect symmetry, anatomical errors "
        "(merged objects, wrong proportions), repetitive background patterns, text rendering artifacts "
        "(garbled or unnatural fonts), lighting and shadow inconsistencies typical of generative AI models.\n\n"
        "2. IMAGE MANIPULATION / TAMPERING — Look for: copy-paste cloning artifacts, inconsistent shadow "
        "directions, compression artifacts that differ across image regions (suggesting selective editing), "
        "unnatural edge blending, color or lighting discontinuities between areas.\n\n"
        "3. DAMAGE-CLAIM CONSISTENCY — Does the visible damage in the image actually match the claimed "
        "loss_type and description? Flag any mismatch (e.g. claim says fire damage but image shows water "
        "stains, or no damage is visible at all).\n\n"
        "4. STAGING RISK — Does the damage appear deliberately arranged rather than naturally occurring? "
        "Signs: too-clean surroundings, items placed too deliberately, damage pattern too symmetric or "
        "uniform, inconsistent wear patterns.\n\n"
        "5. ENVIRONMENTAL CONSISTENCY — Are seasonal, weather, and time-of-day cues visible in the image "
        "consistent with the claimed date of loss and loss type? Flag any inconsistency (e.g. snow on "
        "ground but summer foliage visible).\n\n"
        "Respond with ONLY a valid JSON object — no markdown fences, no extra text:\n"
        "{\n"
        '  "authenticity_verdict": "Genuine | Suspicious | AI-Generated | Tampered",\n'
        '  "confidence_score": <integer 0-100>,\n'
        '  "ai_generation_indicators": [<list of specific signals found, or empty list>],\n'
        '  "tampering_indicators": [<list of specific signals found, or empty list>],\n'
        '  "damage_claim_consistency": "Consistent | Inconsistent | Partially Consistent",\n'
        '  "consistency_notes": "<what matches or does not match the claim description>",\n'
        '  "staging_risk": "Low | Medium | High",\n'
        '  "overall_risk_level": "Low | Medium | High | Critical",\n'
        '  "summary": "<2-3 sentence adjuster-facing assessment of this image>"\n'
        "}"
    )

    try:
        llm = _get_llm()
        message = HumanMessage(content=[
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": data_uri}},
        ])
        response = llm.invoke([message])
        raw = (response.content or "").strip()

        # Strip markdown code fences if the model wraps them
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:].strip()

        parsed = json.loads(raw)

        verdict = parsed.get("authenticity_verdict", "Genuine")
        confidence = int(parsed.get("confidence_score", 0))
        # Flag only when the model is reasonably confident the image is problematic
        flagged = 1 if verdict in {"AI-Generated", "Tampered", "Suspicious"} and confidence >= 60 else 0

        result = {
            "document_id": document_id,
            "file_name": file_name,
            **parsed,
            "flagged": flagged,
        }

        # Write back: insights = full analysis JSON, investigation_notes = human-readable summary
        insights_payload = {k: v for k, v in parsed.items()}
        investigation_notes = (
            f"Authenticity Verdict: {verdict} ({confidence}% confidence). "
            f"{parsed.get('summary', '')}"
        )
        _write_image_authenticity_to_db(document_id, insights_payload, investigation_notes, flagged)

        return result

    except Exception as e:
        log.warning("_analyze_single_image_authenticity failed for %s: %s", document_id, e)
        base_result["summary"] = f"Image analysis failed: {str(e)[:120]}"
        return base_result


def _validate_image_authenticity(claim_number: str, claim: dict) -> dict:
    """
    Runs GPT-4.1 vision authenticity analysis on every image document attached
    to the claim. Aggregates results and returns per-image breakdown with
    overall risk level and flagged count.
    """
    image_docs = _fetch_claim_image_docs(claim_number)
    if not image_docs:
        return {
            "images_analyzed": 0,
            "images_flagged": 0,
            "overall_image_risk": "N/A",
            "per_image_results": [],
            "message": "No image documents found for this claim.",
        }

    per_image_results = []
    images_flagged = 0
    highest_risk = "Low"

    for doc in image_docs:
        result = _analyze_single_image_authenticity(doc, claim)
        per_image_results.append(result)

        doc_risk = result.get("overall_risk_level", "Low")
        if _IMAGE_RISK_ORDER.get(doc_risk, 0) > _IMAGE_RISK_ORDER.get(highest_risk, 0):
            highest_risk = doc_risk

        if result.get("flagged") == 1:
            images_flagged += 1

    return {
        "images_analyzed": len(image_docs),
        "images_flagged": images_flagged,
        "overall_image_risk": highest_risk,
        "per_image_results": per_image_results,
    }


# ─────────────────────────────────────────────────────────────────────────────

def run_evidence_validation(claim_id: str) -> dict:
    """
    Cross-checks submitted documents against required evidence types for the
    claim's loss_type. Determines overall_status from aggregated DB fraud
    signals — not from LLM filename analysis. Returns the validation result
    WITHOUT updating the DB; call save_validation_result to persist.

    Reads from the shared `documents` table (real uploads), not `evidence_items`
    (seed-data-only, never populated for real claims).

    Issue 6: Authenticity is derived from fraud_risk_snapshots / fraud_flags
             / ai_fraud_signals, not from LLM guessing at filenames.
    Issue 8: overall_status is "Suspicious" only when DB signals confirm it.
    """
    claim = _get_claim(claim_id)
    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    # ── Claims bundle parity: check 7 mandatory claim data fields ──
    claim_data_completeness = _check_claim_data_completeness(claim)
    _persist_intake_validation(claim_id, claim_data_completeness)

    loss_type = claim.get("loss_type") or "Other"
    documents = get_claim_documents(claim_id)

    required_types = _get_required_evidence_types(loss_type)
    submitted_types = [d.get("document_type", "") for d in documents]
    missing_types = [t for t in required_types if not any(t.lower() in s.lower() for s in submitted_types)]
    completeness_pct = round((len(required_types) - len(missing_types)) / max(len(required_types), 1) * 100, 1)

    # Issue 6 & 8: Get real DB fraud signals
    signals = _get_fraud_signals(claim_id)

    # Drone authenticity + weather alignment signals
    drone_data = _get_drone_authenticity(claim_id)
    weather_data = _get_weather_alignment(claim_id)

    drone_fraud_score = _compute_drone_fraud_score(drone_data or {})
    drone_flags = _generate_drone_auto_flags(drone_data or {}, documents, weather_data or {})

    # Image authenticity validation via GPT-4.1 vision (additive — runs for all image docs)
    image_authenticity = _validate_image_authenticity(claim_id, claim)
    image_suspicious_count = image_authenticity.get("images_flagged", 0)

    overall_status = _determine_overall_status(
        completeness_pct, signals, drone_fraud_score, image_suspicious_count
    )

    # Effective fraud score (higher of DB snapshot and drone computation)
    effective_fraud_score = max(signals.get("fraud_score", 0), drone_fraud_score)

    # Issue 6: Build authenticity_flags from DB signals using real document_ids only
    authenticity_flags = []
    if signals.get("fraud_score", 0) >= 70 or signals.get("active_flag_count", 0) >= 2:
        for doc in documents:
            did = doc.get("document_id")
            if did:
                authenticity_flags.append({
                    "evidence_id": did,
                    "concern": (
                        f"Claim has elevated fraud signals "
                        f"(score={signals['fraud_score']}, "
                        f"flags={signals['active_flag_count']}) — manual review required."
                    ),
                })

    # Append auto-flags generated from drone analysis
    authenticity_flags.extend(drone_flags)

    # LLM used only for the recommendation text (low-stakes, non-authoritative)
    recommendation = "Review missing evidence types before proceeding to next workflow step."
    try:
        llm = _get_llm()
        image_auth_summary = (
            f"Images analyzed: {image_authenticity.get('images_analyzed', 0)}, "
            f"flagged suspicious: {image_suspicious_count}, "
            f"overall image risk: {image_authenticity.get('overall_image_risk', 'N/A')}"
        )
        rec_prompt = (
            f"Insurance evidence validation summary for a {loss_type} claim:\n"
            f"  Evidence completeness: {completeness_pct}%\n"
            f"  Missing evidence types: {missing_types or 'none'}\n"
            f"  Overall status: {overall_status}\n"
            f"  Fraud score: {signals['fraud_score']}\n"
            f"  Image authenticity check: {image_auth_summary}\n\n"
            "Provide a single concise sentence recommending what the adjuster should do next. "
            "No JSON, no bullet points — plain text only."
        )
        response = llm.invoke(rec_prompt)
        text = (response.content or "").strip()
        if text:
            recommendation = text
    except Exception as e:
        log.warning("LLM recommendation failed: %s", e)

    return {
        "claim_id": claim_id,
        "loss_type": loss_type,
        # ── Claims bundle parity: 7-field mandatory claim data completeness ──
        "claim_data_completeness": claim_data_completeness,
        # ── Existing: evidence document completeness vs required types ──
        "required_evidence_types": required_types,
        "submitted_evidence_count": len(documents),
        "missing_evidence_types": missing_types,
        "completeness_percent": completeness_pct,
        "fraud_signals": signals,
        "authenticity_flags": authenticity_flags,
        "overall_status": overall_status,
        "recommendation": recommendation,
        "drone_data": drone_data,
        "weather_alignment": weather_data,
        "drone_fraud_score": drone_fraud_score,
        "effective_fraud_score": effective_fraud_score,
        "drone_flags": drone_flags,
        # ── Image authenticity: GPT-4.1 vision analysis of all uploaded images ──
        "image_authenticity": image_authenticity,
    }


def _update_document_validation(document_id: str, flagged: int, note: str) -> None:
    """
    Persist validation outcome back to documents.flagged / investigation_notes.

    flagged is combined via GREATEST so this never downgrades a document already
    flagged by the image-authenticity vision pipeline (_write_image_authenticity_to_db).
    investigation_notes only fills in when NULL, so it never overwrites the more
    detailed per-image vision write with this generic signals-based note.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE documents
               SET flagged = GREATEST(COALESCE(flagged, 0), %s),
                   investigation_notes = COALESCE(investigation_notes, %s)
               WHERE document_id = %s""",
            (flagged, note, document_id),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        log.warning("_update_document_validation failed for %s: %s", document_id, e)
    finally:
        conn.close()


def save_validation_result(claim_id: str, overall_status: str, authenticity_flags: list) -> dict:
    """
    Persists a validation result by updating the claim's documents.
    Flagged items → flagged=1 with a concern note; everything else → flagged=0
    with a default "verified" note (unless a vision-analysis note already exists).

    Reads/writes the shared `documents` table (real uploads), not `evidence_items`
    (seed-data-only, never populated for real claims).

    Issue 7: Incoming authenticity_flags are validated against actual DB
             document_ids. Any flag with a hallucinated or unknown ID is
             silently discarded so no DB update is attempted for ghost records.
    """
    documents = get_claim_documents(claim_id)

    # Issue 7: Build the set of VALID document_ids from the DB, not from the LLM
    valid_ids = {doc.get("document_id") for doc in documents if doc.get("document_id")}

    # Only keep flags whose id actually exists in the DB, keyed by concern text
    flags_by_id = {
        f.get("evidence_id"): f.get("concern") or "Flagged during evidence validation."
        for f in (authenticity_flags or [])
        if f.get("evidence_id") in valid_ids
    }

    hallucinated_count = len([
        f for f in (authenticity_flags or [])
        if f.get("evidence_id") and f.get("evidence_id") not in valid_ids
    ])
    if hallucinated_count:
        log.warning(
            "save_validation_result: discarded %d flag(s) with document_id not found in DB for claim %s",
            hallucinated_count,
            claim_id,
        )

    updated_count = 0
    for doc in documents:
        did = doc.get("document_id")
        if not did:
            continue
        if did in flags_by_id:
            _update_document_validation(did, 1, flags_by_id[did])
        else:
            _update_document_validation(did, 0, "Verified — no evidence concerns identified.")
        updated_count += 1

    return {
        "claim_id": claim_id,
        "overall_status": overall_status,
        "items_updated": updated_count,
        "hallucinated_ids_discarded": hallucinated_count,
        "saved": True,
    }
