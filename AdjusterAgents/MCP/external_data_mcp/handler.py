"""
handler.py — External Data (Weather / Drone / Authority) Verification
─────────────────────────────────────────────────────────────────────────
Routing is DB-driven via loss_type_verification_configs:
  verification_mode = 'weather'   → Open-Meteo real weather + drone LLM
  verification_mode = 'authority' → skip weather API, fire dept / police
                                    time comparison + drone LLM
  verification_mode = 'physical'  → drone LLM only (no external APIs)
  verification_mode = 'generic'   → drone LLM only (unclassified loss type)

Weather data (when applicable) is fetched from the Open-Meteo free API:
  - Geocoding:  https://nominatim.openstreetmap.org/search
  - Historical: https://archive-api.open-meteo.com/v1/archive

Drone authenticity and drone evidence summary are LLM-simulated.
Authority incident logs (fire dept / police times) are LLM-simulated.
"""

import json
import logging
import os
import sys
from typing import Optional

import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from langchain_openai.chat_models import AzureChatOpenAI  # noqa: E402

log = logging.getLogger(__name__)


# ── WMO weather interpretation codes → human-readable description ─────────────
_WMO_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Heavy freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}

# Used only inside _map_weather_fields to set drone_weather_alignment
_WEATHER_LOSS_TYPES = {
    "storm", "flood", "flooding", "hail", "wind", "windstorm", "hurricane",
    "tornado", "rain", "lightning", "snow", "ice", "freeze", "frozen",
    "water damage", "roof damage", "weather",
}

_AUTHORITY_LABELS = {
    "fire_department": "Fire Department",
    "police":          "Police Department",
    "nws":             "National Weather Service",
    "coast_guard":     "Coast Guard",
}


# ── DB-driven loss type routing ───────────────────────────────────────────────

def _get_loss_type_config(loss_type: str) -> dict:
    """
    Reads routing config for this loss type from loss_type_verification_configs.
    Falls back to generic (no external APIs) if the loss type is not in the table.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM loss_type_verification_configs WHERE LOWER(loss_type) = LOWER(%s)",
            (loss_type or "",),
        )
        row = row_to_dict(cur.fetchone())
        if row:
            return row
        log.info("Loss type %r not in loss_type_verification_configs — using generic fallback", loss_type)
        return {
            "verification_mode": "generic",
            "use_weather_api": False,
            "use_authority_check": False,
            "authority_type": None,
        }
    finally:
        conn.close()


# ── Weather helpers (unchanged) ───────────────────────────────────────────────

def _geocode(location: str) -> Optional[tuple]:
    if not location or location.strip() == "":
        return None
    location_clean = " ".join(location.split())
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location_clean, "format": "json", "limit": 1},
            headers={"User-Agent": "JarvisClaimsAgent/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            log.warning("Geocoding: no results for location=%r", location_clean)
            return None
        return (float(results[0]["lat"]), float(results[0]["lon"]))
    except Exception as exc:
        log.warning("Geocoding failed for %r: %s", location_clean, exc)
        return None


def _fetch_historical_weather(lat: float, lon: float, date_str: str) -> Optional[dict]:
    date_only = date_str.split("T")[0].split(" ")[0] if date_str else None
    if not date_only:
        return None
    try:
        resp = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": date_only,
                "end_date": date_only,
                "daily": "precipitation_sum,windspeed_10m_max,weathercode",
                "timezone": "auto",
            },
            timeout=15,
        )
        resp.raise_for_status()
        daily = resp.json().get("daily", {})
        return {
            "precipitation_sum": (daily.get("precipitation_sum") or [None])[0],
            "windspeed_10m_max": (daily.get("windspeed_10m_max") or [None])[0],
            "weathercode": (daily.get("weathercode") or [None])[0],
        }
    except Exception as exc:
        log.warning("Open-Meteo archive failed (lat=%s lon=%s date=%s): %s", lat, lon, date_str, exc)
        return None


def _map_weather_fields(weather_data: dict, loss_type: str, date_of_loss: str) -> dict:
    precip = weather_data.get("precipitation_sum") or 0.0
    wind = weather_data.get("windspeed_10m_max") or 0.0
    code = weather_data.get("weathercode") or 0

    storm_event = _WMO_DESCRIPTIONS.get(int(code), f"Weather code {code}")
    if precip == 0 and wind < 10 and code == 0:
        storm_event = "No significant weather event"

    event_time = date_of_loss or ""

    if precip > 60 or wind > 90 or code in (95, 96, 99):
        zip_code_severity_index = "Severe"
    elif precip > 25 or wind > 60 or code in (65, 67, 75, 82, 86):
        zip_code_severity_index = "High"
    elif precip > 5 or wind > 30 or code in (51, 53, 55, 61, 63, 71, 73, 80, 81, 85):
        zip_code_severity_index = "Moderate"
    else:
        zip_code_severity_index = "Low"

    loss_lower = (loss_type or "").lower()
    is_weather_loss = any(kw in loss_lower for kw in _WEATHER_LOSS_TYPES)

    if not is_weather_loss:
        drone_weather_alignment = "Aligned"
    elif is_weather_loss and zip_code_severity_index in ("High", "Severe"):
        drone_weather_alignment = "Aligned"
    elif is_weather_loss and zip_code_severity_index == "Moderate":
        drone_weather_alignment = "Partial"
    else:
        drone_weather_alignment = "Not Aligned"

    return {
        "storm_event": storm_event,
        "event_time": event_time,
        "zip_code_severity_index": zip_code_severity_index,
        "drone_weather_alignment": drone_weather_alignment,
    }


# ── Authority time comparison ─────────────────────────────────────────────────

def _compare_time_discrepancy(claimant_time: str, authority_time: str) -> dict:
    """
    Compares claimant-reported time vs authority-reported time.
    Returns discrepancy_minutes, discrepancy_flag, fraud_indicator.
    Handles midnight wrap-around (e.g. 23:50 vs 00:10 = 20 min, not 1420).
    """
    if not claimant_time or not authority_time:
        return {
            "discrepancy_minutes": None,
            "discrepancy_flag": "Unknown" if not claimant_time else "Computed",
            "fraud_indicator": "Unknown",
        }
    try:
        def _parse(t):
            parts = t.strip().split(":")
            return int(parts[0]) * 60 + int(parts[1])

        diff = abs(_parse(claimant_time) - _parse(authority_time))
        if diff > 720:  # midnight wrap-around
            diff = 1440 - diff

        if diff < 30:
            flag = "None"
            fraud_indicator = "Low"
        elif diff < 60:
            flag = "Minor"
            fraud_indicator = "Medium"
        else:
            flag = "Significant"
            fraud_indicator = "High"

        return {"discrepancy_minutes": diff, "discrepancy_flag": flag, "fraud_indicator": fraud_indicator}
    except Exception:
        return {"discrepancy_minutes": None, "discrepancy_flag": "Unknown", "fraud_indicator": "Unknown"}


def _simulate_authority_incident(
    claim_id: str, claim: dict, loss_type: str,
    date_of_loss: str, time_of_loss: str, authority_type: str,
) -> dict:
    """
    Uses LLM to simulate an authority-reported incident time (fire dept / police),
    computes time discrepancy vs claimant, writes to authority_incident_logs, returns row.
    """
    authority_label = _AUTHORITY_LABELS.get(authority_type or "", "Authority")

    prompt = f"""
You are simulating an official authority incident report for insurance claims verification.

CLAIM DETAILS:
  claim_id:               {claim_id}
  loss_type:              {loss_type}
  date_of_loss:           {date_of_loss or "Not provided"}
  location:               {claim.get("location") or "Not provided"}
  severity:               {claim.get("severity") or "Medium"}
  description:            {claim.get("short_description") or "Not provided"}
  claimant_reported_time: {time_of_loss or "Not provided in FNOL"}

AUTHORITY: {authority_label}

Generate a realistic {authority_label} incident report time for this {loss_type} claim.

RULES for authority_reported_time:
- Genuine claims: authority time usually within 30 minutes of claimant-reported time
- Slightly suspicious: 30–90 minutes difference
- Highly suspicious: more than 90 minutes difference, or authority time recorded BEFORE claimant time
- If claimant time is not provided, generate a plausible authority time for the date and loss type
- Use 24-hour format "HH:MM"
- Fire incidents: commonly reported between 18:00–02:00
- Theft incidents: commonly reported between 20:00–06:00

RESPOND with ONLY this JSON (no markdown, no extra keys):
{{
  "authority_reported_time": "HH:MM",
  "authority_notes": "one sentence describing what the {authority_label} recorded at the scene"
}}
"""

    llm = _get_llm()
    response = llm.invoke(prompt)
    content = response.content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]

    try:
        parsed = json.loads(content)
    except Exception:
        log.warning("Could not parse authority incident JSON for %s: %s", claim_id, content)
        parsed = {
            "authority_reported_time": "",
            "authority_notes": "Authority record simulation failed — please retry",
        }

    authority_time = parsed.get("authority_reported_time", "")
    notes = parsed.get("authority_notes", "")

    discrepancy = _compare_time_discrepancy(time_of_loss, authority_time)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO authority_incident_logs (
                claim_id, loss_type, authority_type, authority_reported_time,
                authority_reported_date, claimant_reported_time,
                time_discrepancy_minutes, discrepancy_flag,
                authority_source, fraud_indicator, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                claim_id, loss_type, authority_type, authority_time,
                date_of_loss, time_of_loss or None,
                discrepancy["discrepancy_minutes"],
                discrepancy["discrepancy_flag"],
                f"Simulated {authority_label} Record",
                discrepancy["fraud_indicator"],
                notes,
            ),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
    finally:
        conn.close()

    return {
        "id": new_id,
        "claim_id": claim_id,
        "loss_type": loss_type,
        "authority_type": authority_type,
        "authority_reported_time": authority_time,
        "authority_reported_date": date_of_loss,
        "claimant_reported_time": time_of_loss or None,
        "time_discrepancy_minutes": discrepancy["discrepancy_minutes"],
        "discrepancy_flag": discrepancy["discrepancy_flag"],
        "authority_source": f"Simulated {authority_label} Record",
        "fraud_indicator": discrepancy["fraud_indicator"],
        "notes": notes,
        "simulated": True,
    }


def get_authority_incident_log(claim_id: str) -> dict:
    """Returns the most recent authority_incident_logs row for the claim, or null."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM authority_incident_logs WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


# ── LLM helper ────────────────────────────────────────────────────────────────

def _get_llm():
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


# ── Existing read/write helpers (unchanged) ───────────────────────────────────

def get_weather_alignment(claim_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM weather_location_alignment WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def write_weather_alignment(claim_id: str, storm_event: str, event_time: str,
                             zip_code_severity_index: str, drone_weather_alignment: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO weather_location_alignment (
                claim_id, storm_event, event_time, zip_code_severity_index, drone_weather_alignment
            ) VALUES (%s,%s,%s,%s,%s)
            """,
            (claim_id, storm_event, event_time, zip_code_severity_index, drone_weather_alignment),
        )
        conn.commit()
        return {"claim_id": claim_id, "storm_event": storm_event, "event_time": event_time,
                "zip_code_severity_index": zip_code_severity_index, "drone_weather_alignment": drone_weather_alignment}
    finally:
        conn.close()


def get_drone_authenticity(claim_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM drone_authenticity_data WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def write_drone_analysis(claim_id: str, roof_condition: str, weather_event_match: str,
                          drone_match_percent: int, geo_match: str, damage_inflation_index: str,
                          tamper_indicator: str, drone_image_urls: Optional[list] = None,
                          drone_capture_time: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO drone_authenticity_data (
                claim_id, drone_capture_time, roof_condition, weather_event_match,
                drone_match_percent, geo_match, damage_inflation_index, tamper_indicator, drone_image_urls
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (claim_id, drone_capture_time, roof_condition, weather_event_match,
             drone_match_percent, geo_match, damage_inflation_index, tamper_indicator,
             json.dumps(drone_image_urls) if drone_image_urls is not None else None),
        )
        conn.commit()
        return {
            "claim_id": claim_id, "drone_capture_time": drone_capture_time,
            "roof_condition": roof_condition, "weather_event_match": weather_event_match,
            "drone_match_percent": drone_match_percent, "geo_match": geo_match,
            "damage_inflation_index": damage_inflation_index, "tamper_indicator": tamper_indicator,
            "drone_image_urls": drone_image_urls,
        }
    finally:
        conn.close()


def get_drone_evidence_summary(claim_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM drone_evidence_summary WHERE claim_id = %s ORDER BY id DESC LIMIT 1",
            (claim_id,),
        )
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def write_drone_evidence_summary(claim_id: str, drone_capture_time: Optional[str],
                                  roof_condition_rating: str, weather_event_alignment: str,
                                  damage_match_percent: str, manipulation_flags: str,
                                  drone_notes: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO drone_evidence_summary (
                claim_id, drone_capture_time, roof_condition_rating,
                weather_event_alignment, damage_match_percent,
                manipulation_flags, drone_notes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (claim_id, drone_capture_time, roof_condition_rating,
             weather_event_alignment, damage_match_percent,
             manipulation_flags, drone_notes),
        )
        conn.commit()
        return {
            "claim_id": claim_id, "drone_capture_time": drone_capture_time,
            "roof_condition_rating": roof_condition_rating,
            "weather_event_alignment": weather_event_alignment,
            "damage_match_percent": damage_match_percent,
            "manipulation_flags": manipulation_flags,
            "drone_notes": drone_notes,
        }
    finally:
        conn.close()


def _get_claim(claim_id: str):
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


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_external_data_checks(claim_id: str) -> dict:
    claim = _get_claim(claim_id)
    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    location     = claim.get("location") or ""
    date_of_loss = claim.get("date_of_loss") or ""
    loss_type    = claim.get("loss_type") or ""
    time_of_loss = claim.get("time_of_loss") or ""

    # ── Routing: read config from DB — no hardcoded loss type sets ────────────
    config            = _get_loss_type_config(loss_type)
    use_weather_api   = config.get("use_weather_api", False)
    use_authority_check = config.get("use_authority_check", False)
    authority_type    = config.get("authority_type") or ""
    verification_mode = config.get("verification_mode", "generic")

    # ── Step 1: Weather data ──────────────────────────────────────────────────
    weather_real = False
    if use_weather_api:
        coords = _geocode(location)
        if coords:
            raw_weather = _fetch_historical_weather(coords[0], coords[1], date_of_loss)
            if raw_weather:
                weather_fields = _map_weather_fields(raw_weather, loss_type, date_of_loss)
                weather_real = True
                log.info(
                    "Open-Meteo: location=%r date=%r precip=%.1fmm wind=%.1fkm/h code=%s",
                    location, date_of_loss,
                    raw_weather.get("precipitation_sum") or 0,
                    raw_weather.get("windspeed_10m_max") or 0,
                    raw_weather.get("weathercode"),
                )
            else:
                log.warning("Open-Meteo archive returned no data — using default weather fields")
                weather_fields = {
                    "storm_event": "Weather data unavailable for this date/location",
                    "event_time": date_of_loss,
                    "zip_code_severity_index": "Low",
                    "drone_weather_alignment": "Aligned",
                }
        else:
            log.warning("Could not geocode location %r — using default weather fields", location)
            weather_fields = {
                "storm_event": "Location could not be resolved for weather lookup",
                "event_time": date_of_loss,
                "zip_code_severity_index": "Low",
                "drone_weather_alignment": "Aligned",
            }
    else:
        # Weather API not applicable for this loss type
        weather_fields = {
            "storm_event": f"Weather API not applicable for {loss_type or 'this'} claims",
            "event_time": date_of_loss,
            "zip_code_severity_index": "N/A",
            "drone_weather_alignment": "N/A",
        }

    # ── Step 2: LLM drone simulation ──────────────────────────────────────────
    if use_weather_api:
        weather_context = f"""REAL WEATHER DATA (already fetched — use this to inform drone assessment):
  storm_event:             {weather_fields['storm_event']}
  zip_code_severity_index: {weather_fields['zip_code_severity_index']}
  drone_weather_alignment: {weather_fields['drone_weather_alignment']}"""
    else:
        weather_context = (
            f"WEATHER: Not applicable for {loss_type or 'this'} loss type. "
            "Do not base the drone assessment on weather conditions. "
            "Set weather_event_match to \"Yes\" (weather is irrelevant, not suspicious)."
        )

    llm = _get_llm()
    prompt = f"""
You are simulating drone verification data for an insurance claims adjuster.
Generate plausible, internally consistent data for the drone assessment only.

CLAIM DETAILS:
  loss_type:         {loss_type}
  short_description: {claim.get('short_description')}
  location:          {location}
  date_of_loss:      {date_of_loss}
  severity:          {claim.get('severity')}

{weather_context}

════════════════════════════════════════
DRONE ASSESSMENT FIELD RULES
════════════════════════════════════════

drone_match_percent — integer between 0 and 100 (whole number, no decimals)
  How closely drone aerial imagery matches the reported damage extent.
  Genuine claims with clear physical damage (fire, flood, hail, storm): 70–95
  Ambiguous or interior-only damage (theft, pipe burst, equipment): 50–80
  Suspected inflated claims: 30–60

geo_match — MUST be EXACTLY one of: "Full" | "Partial" | "None"
  Whether drone GPS coordinates match the reported loss location.
  "Full"    = GPS coordinates match the claim location precisely
  "Partial" = minor discrepancy, same area but slightly off
  "None"    = location does not match at all (suspicious)
  Most genuine claims use "Full". Use "None" only for Critical-severity fraud scenarios.

weather_event_match — MUST be EXACTLY one of: "Yes" | "No"
  Whether conditions at drone capture time are consistent with the reported loss.
  If drone_weather_alignment is "Aligned"      → use "Yes"
  If drone_weather_alignment is "Not Aligned"  → use "No"
  If drone_weather_alignment is "Partial"      → use "Yes"
  If drone_weather_alignment is "N/A"          → use "Yes" (weather not applicable for this loss type)

damage_inflation_index — MUST be EXACTLY one of: "Low" | "Medium" | "High"
  Whether drone-visible damage aligns with the reported cost estimate.
  "Low"    = visible damage aligns with estimate (genuine)
  "Medium" = 20–30% discrepancy detected
  "High"   = >30% discrepancy, likely over-reported damage (suspicious)
  Most genuine claims use "Low".

tamper_indicator — MUST be EXACTLY one of: "None" | "Possible" | "Likely"
  Whether drone imagery shows signs of manipulation or staged damage.
  "None"     = no signs of tampering
  "Possible" = minor anomalies, not conclusive
  "Likely"   = strong evidence of staged or tampered imagery (suspicious)
  Most genuine claims use "None".

roof_condition — free text, 1 sentence describing the aerial view of the property or site.
  Must be consistent with the loss_type and severity.

drone_capture_time — ISO 8601 datetime string, format: "YYYY-MM-DDTHH:MM:SS"
  Must be within 1–3 days after date_of_loss.

════════════════════════════════════════
FRAUD RISK SCORE FORMULA — calibrate your values against this target
════════════════════════════════════════
  base score    = 100 - drone_match_percent
  tamper != "None"              → +20
  geo_match == "None"           → +15
  geo_match == "Partial"        → +8
  damage_inflation == "High"    → +15
  damage_inflation == "Medium"  → +8
  weather_event_match == "No"   → +10
  Final score clamped 0–100:
    < 30  = Low Risk    (genuine claim)
    30–59 = Medium Risk
    ≥ 60  = High Risk   (potential fraud)

  Target fraud risk level by claim severity:
    Low or Medium severity genuine claim  → Low Risk    (final score < 30)
    High severity genuine claim           → Low-Medium  (final score 15–45)
    Critical severity claim               → Medium Risk  (final score 30–55)

════════════════════════════════════════
DRONE EVIDENCE SUMMARY FIELD RULES
════════════════════════════════════════

roof_condition_rating — MUST be EXACTLY one of: "Good" | "Fair" | "Poor" | "Critical"
  Overall aerial condition rating of the property.
  Correlate with severity: Low → "Good" or "Fair", High → "Poor", Critical → "Critical"

weather_event_alignment — 1 sentence summarising how drone capture data aligns with the
  conditions at time of loss (for non-weather loss types, describe physical scene alignment instead)

damage_match_percent — the same integer value as drone_match_percent but as a quoted string, e.g. "84"

manipulation_flags — "None detected" if clean; otherwise describe specific anomalies found

drone_notes — 1 sentence adjuster note summarising the overall drone assessment finding

════════════════════════════════════════
RESPOND with ONLY this JSON object (no markdown fences, no extra keys, no explanation):
{{
  "drone": {{
    "drone_capture_time": "YYYY-MM-DDTHH:MM:SS",
    "roof_condition": "...",
    "weather_event_match": "Yes" | "No",
    "drone_match_percent": <integer 0-100>,
    "geo_match": "Full" | "Partial" | "None",
    "damage_inflation_index": "Low" | "Medium" | "High",
    "tamper_indicator": "None" | "Possible" | "Likely"
  }},
  "drone_evidence_summary": {{
    "roof_condition_rating": "Good" | "Fair" | "Poor" | "Critical",
    "weather_event_alignment": "...",
    "damage_match_percent": "<same integer as drone_match_percent as a string>",
    "manipulation_flags": "...",
    "drone_notes": "..."
  }}
}}
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
        log.warning("Could not parse LLM JSON: %s", content)
        return {
            "claim_id": claim_id,
            "error": "LLM returned unparseable JSON. External data checks could not be completed. Please retry.",
            "simulated": False,
        }

    drone = parsed.get("drone", {})
    summary = parsed.get("drone_evidence_summary", {})

    # ── Step 3: Write weather, drone, drone_summary records ───────────────────
    weather_row = write_weather_alignment(
        claim_id,
        weather_fields["storm_event"],
        weather_fields["event_time"],
        weather_fields["zip_code_severity_index"],
        weather_fields["drone_weather_alignment"],
    )

    drone_row = write_drone_analysis(
        claim_id,
        drone.get("roof_condition", "No aerial assessment available"),
        drone.get("weather_event_match", "Yes"),
        int(drone.get("drone_match_percent", 50)),
        drone.get("geo_match", "Full"),
        drone.get("damage_inflation_index", "Low"),
        drone.get("tamper_indicator", "None"),
        drone_image_urls=None,
        drone_capture_time=drone.get("drone_capture_time", date_of_loss),
    )

    summary_row = write_drone_evidence_summary(
        claim_id,
        drone.get("drone_capture_time", date_of_loss),
        summary.get("roof_condition_rating", "Fair"),
        summary.get("weather_event_alignment", ""),
        summary.get("damage_match_percent", str(drone.get("drone_match_percent", 50))),
        summary.get("manipulation_flags", "None detected"),
        summary.get("drone_notes", ""),
    )

    # ── Step 4: Authority time check (fire dept / police) — if applicable ─────
    authority_row = None
    if use_authority_check and authority_type:
        authority_row = _simulate_authority_incident(
            claim_id, claim, loss_type, date_of_loss, time_of_loss, authority_type,
        )

    weather_row["real_weather"] = weather_real
    drone_row["simulated"] = True
    summary_row["simulated"] = True

    result = {
        "claim_id": claim_id,
        "verification_mode": verification_mode,
        "weather_alignment": weather_row,
        "drone_authenticity": drone_row,
        "drone_evidence_summary": summary_row,
        "simulated": True,
        "note": (
            "Weather data sourced from Open-Meteo historical archive (real). "
            "Drone assessment is simulated."
            if use_weather_api else
            f"Weather API not used for {loss_type} claims. "
            "Drone assessment is simulated."
            + (" Authority incident time comparison included." if authority_row else "")
        ),
    }
    if authority_row:
        result["authority_incident_log"] = authority_row

    return result
