"""
external_data_router.py
───────────────────────────
FastAPI routes for the External Data (Weather/Drone/Authority) Verification MCP.

Tool / Endpoint map:
  get_weather_alignment        GET  /api/external_data/weather/{claim_id}
  write_weather_alignment      POST /api/external_data/weather/{claim_id}
  get_drone_authenticity       GET  /api/external_data/drone/{claim_id}
  write_drone_analysis         POST /api/external_data/drone/{claim_id}
  get_drone_evidence_summary   GET  /api/external_data/drone_summary/{claim_id}
  get_authority_incident_log   GET  /api/external_data/authority/{claim_id}
  run_external_data_checks     POST /api/external_data/run/{claim_id}
"""

import logging
from fastapi import APIRouter, HTTPException

from external_data_mcp import handler
from external_data_mcp.models import DroneAnalysisRequest, WeatherAlignmentRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/external_data/weather/{claim_id}",
    operation_id="get_weather_alignment",
    summary="Get the latest weather/location alignment for a claim",
    tags=["ExternalData"],
)
def get_weather_alignment(claim_id: str):
    """Returns the most recent weather_location_alignment row for the claim, or null."""
    return handler.get_weather_alignment(claim_id)


@router.post(
    "/api/external_data/weather/{claim_id}",
    operation_id="write_weather_alignment",
    summary="Write a weather/location alignment record for a claim",
    tags=["ExternalData"],
)
def write_weather_alignment(claim_id: str, body: WeatherAlignmentRequest):
    """Inserts a new weather_location_alignment row for the given claim_id."""
    try:
        return handler.write_weather_alignment(
            claim_id, body.storm_event, body.event_time, body.zip_code_severity_index, body.drone_weather_alignment,
        )
    except Exception as e:
        log.exception("write_weather_alignment error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/external_data/drone/{claim_id}",
    operation_id="get_drone_authenticity",
    summary="Get the latest drone authenticity data for a claim",
    tags=["ExternalData"],
)
def get_drone_authenticity(claim_id: str):
    """Returns the most recent drone_authenticity_data row for the claim, or null."""
    return handler.get_drone_authenticity(claim_id)


@router.post(
    "/api/external_data/drone/{claim_id}",
    operation_id="write_drone_analysis",
    summary="Write a drone authenticity analysis record for a claim",
    tags=["ExternalData"],
)
def write_drone_analysis(claim_id: str, body: DroneAnalysisRequest):
    """Inserts a new drone_authenticity_data row for the given claim_id."""
    try:
        return handler.write_drone_analysis(
            claim_id, body.roof_condition, body.weather_event_match, body.drone_match_percent,
            body.geo_match, body.damage_inflation_index, body.tamper_indicator,
            body.drone_image_urls, body.drone_capture_time,
        )
    except Exception as e:
        log.exception("write_drone_analysis error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/external_data/drone_summary/{claim_id}",
    operation_id="get_drone_evidence_summary",
    summary="Get the latest drone evidence summary for a claim",
    tags=["ExternalData"],
)
def get_drone_evidence_summary(claim_id: str):
    """Returns the most recent drone_evidence_summary row for the claim, or null."""
    return handler.get_drone_evidence_summary(claim_id)


@router.get(
    "/api/external_data/authority/{claim_id}",
    operation_id="get_authority_incident_log",
    summary="Get the latest authority incident log (fire dept / police time comparison) for a claim",
    tags=["ExternalData"],
)
def get_authority_incident_log(claim_id: str):
    """
    Returns the most recent authority_incident_logs row for the claim.
    Only populated for loss types configured to use authority checks
    (e.g. Fire → fire_department, Theft → police).
    """
    return handler.get_authority_incident_log(claim_id)


@router.post(
    "/api/external_data/run/{claim_id}",
    operation_id="run_external_data_checks",
    summary="Run (simulated) external weather and drone data checks for a claim",
    tags=["ExternalData"],
)
def run_external_data_checks(claim_id: str):
    """
    Fetches the claim and uses an LLM to SIMULATE a plausible weather event
    record and drone authenticity assessment consistent with the claim's
    loss_type/date/location (no real weather/drone API is wired up), writes
    both records, and returns the combined result with simulated: true.
    """
    try:
        return handler.run_external_data_checks(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("run_external_data_checks error")
        raise HTTPException(status_code=500, detail=str(e))
