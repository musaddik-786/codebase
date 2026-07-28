"""
voice_text_intake_router.py
────────────────────────────
FastAPI route handlers for the Voice/Text Intake MCP. Each route has an
explicit operation_id — these become the MCP tool names exposed to the
LangGraph agent via fastapi-mcp.

Tool / Endpoint map:
  create_fnol_submission         POST  /api/fnol/create_submission
  get_fnol_submission            GET   /api/fnol/get_submission/{fnol_id}
  get_fnol_by_policy              GET   /api/fnol/get_by_policy/{policy_number}
  update_fnol_submission          PATCH /api/fnol/update_submission/{fnol_id}
  submit_fnol                     POST  /api/fnol/submit/{fnol_id}
  get_mandatory_fields            GET   /api/fnol/mandatory_fields
  save_voice_text_extraction      POST  /api/fnol/save_extraction
  get_voice_text_extractions      GET   /api/fnol/get_extractions/{fnol_id}
  save_ai_inferences               POST  /api/fnol/save_inferences
  log_question_answer              POST  /api/fnol/log_question
  get_question_log                 GET   /api/fnol/get_question_log/{fnol_id}
  save_field_attribution           POST  /api/fnol/save_attribution
  extract_fnol_fields_from_text    POST  /api/voice/extract_fields
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from voice_text_intake_mcp.models import (
    CreateFnolSubmissionRequest,
    UpdateFnolSubmissionRequest,
    ExtractFnolFieldsRequest,
    SaveVoiceTextExtractionRequest,
    SaveAiInferencesRequest,
    LogQuestionAnswerRequest,
    SaveFieldAttributionRequest,
    AiInferenceItem,
)
from voice_text_intake_mcp import fnol_handler, voice_handler

log = logging.getLogger(__name__)

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# FNOL Submission CRUD
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/api/fnol/create_submission",
    operation_id="create_fnol_submission",
    summary="Create a new FNOL submission record",
    tags=["FNOL"],
)
def create_fnol_submission(req: CreateFnolSubmissionRequest):
    """
    Creates a new First Notice of Loss (FNOL) record in the database.
    Use this as the first step after collecting the policyholder's identity
    and policy number.
    """
    try:
        return fnol_handler.create_fnol_submission(req)
    except Exception as e:
        log.exception("create_fnol_submission error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/fnol/get_submission/{fnol_id}",
    operation_id="get_fnol_submission",
    summary="Retrieve an FNOL submission by its ID",
    tags=["FNOL"],
)
def get_fnol_submission(fnol_id: int):
    """
    Fetches the full FNOL submission record for the given fnol_id.
    Use to check current state, field values, and completion status.
    """
    record = fnol_handler.get_fnol_submission_by_id(fnol_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"FNOL {fnol_id} not found")
    return record


@router.get(
    "/api/fnol/get_by_policy/{policy_number}",
    operation_id="get_fnol_by_policy",
    summary="Look up existing FNOL submissions for a policy number",
    tags=["FNOL"],
)
def get_fnol_by_policy(policy_number: str):
    """
    Returns all FNOL submissions linked to the given policy_number, newest
    first. Use this before creating a new FNOL to check for duplicates or
    pre-populate data from the most recent open submission.
    """
    return fnol_handler.get_fnol_submission_by_policy(policy_number)


@router.patch(
    "/api/fnol/update_submission/{fnol_id}",
    operation_id="update_fnol_submission",
    summary="Update fields on an existing FNOL submission",
    tags=["FNOL"],
)
def update_fnol_submission(fnol_id: int, req: UpdateFnolSubmissionRequest):
    """
    Partially updates the FNOL record identified by fnol_id. Only fields
    included in the request body are modified. Use this to progressively
    populate FNOL fields as the agent extracts them from the conversation.
    """
    try:
        record = fnol_handler.update_fnol_submission(fnol_id, req)
        if not record:
            raise HTTPException(status_code=404, detail=f"FNOL {fnol_id} not found")
        return record
    except HTTPException:
        raise
    except Exception as e:
        log.exception("update_fnol_submission error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/fnol/submit/{fnol_id}",
    operation_id="submit_fnol",
    summary="Finalise and submit the FNOL — creates a claim record",
    tags=["FNOL"],
)
def submit_fnol(fnol_id: int):
    """
    Marks the FNOL as submitted (status='submitted', submitted_at=now).
    If no existing claim exists for the policy, automatically creates one
    in 'Open' status (claims, claims_master, claim_journey_master).
    Returns the updated FNOL and the assigned claim_number.
    """
    try:
        return fnol_handler.submit_fnol(fnol_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("submit_fnol error")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Mandatory Fields Reference
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/api/fnol/mandatory_fields",
    operation_id="get_mandatory_fields",
    summary="Get the list of mandatory FNOL fields with inference questions",
    tags=["FNOL"],
)
def get_mandatory_fields():
    """
    Returns all mandatory FNOL field definitions including their labels,
    whether they can be AI-inferred, and the question to ask the policyholder
    to elicit each value. Use this to drive the conversational Q&A loop.
    """
    return fnol_handler.get_mandatory_fields()


# ──────────────────────────────────────────────────────────────────────────────
# Voice / Text Extractions
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/api/fnol/save_extraction",
    operation_id="save_voice_text_extraction",
    summary="Save raw voice/text input alongside extracted FNOL fields",
    tags=["FNOL"],
)
def save_voice_text_extraction(req: SaveVoiceTextExtractionRequest):
    """
    Persists the raw voice transcript or text input along with the structured
    fields extracted from it. Creates an audit trail linking input to output.
    Call this after running extract_fnol_fields_from_text.
    """
    try:
        return fnol_handler.save_voice_text_extraction(req)
    except Exception as e:
        log.exception("save_voice_text_extraction error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/fnol/get_extractions/{fnol_id}",
    operation_id="get_voice_text_extractions",
    summary="Get all voice/text extraction records for an FNOL",
    tags=["FNOL"],
)
def get_voice_text_extractions(fnol_id: int):
    """
    Returns all voice/text extraction records linked to the given FNOL,
    ordered by creation time.
    """
    return fnol_handler.get_voice_text_extractions(fnol_id)


# ──────────────────────────────────────────────────────────────────────────────
# AI Inferences
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/api/fnol/save_inferences",
    operation_id="save_ai_inferences",
    summary="Store AI-inferred field values with confidence scores",
    tags=["FNOL"],
)
def save_ai_inferences(req: SaveAiInferencesRequest):
    """
    Saves one or more AI-inferred FNOL field values, each with a confidence
    score and source attribution. These records track which values were
    inferred by the LLM vs confirmed by the policyholder.
    """
    try:
        return fnol_handler.save_ai_inferences(req)
    except Exception as e:
        log.exception("save_ai_inferences error")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Mandatory Question Log
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/api/fnol/log_question",
    operation_id="log_question_answer",
    summary="Log a question asked to the policyholder and their answer",
    tags=["FNOL"],
)
def log_question_answer(req: LogQuestionAnswerRequest):
    """
    Records each question the agent asks and the policyholder's response.
    Enables a full audit trail of the intake conversation. Call once per
    question-answer exchange during the Q&A loop.
    """
    try:
        return fnol_handler.log_question_answer(req)
    except Exception as e:
        log.exception("log_question_answer error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/fnol/get_question_log/{fnol_id}",
    operation_id="get_question_log",
    summary="Get the full Q&A log for an FNOL",
    tags=["FNOL"],
)
def get_question_log(fnol_id: int):
    """
    Returns all question-answer pairs logged for the given FNOL, ordered by
    question_order. Use to check which fields have been covered and which
    are still outstanding.
    """
    return fnol_handler.get_question_log(fnol_id)


# ──────────────────────────────────────────────────────────────────────────────
# Field Attribution
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/api/fnol/save_attribution",
    operation_id="save_field_attribution",
    summary="Record the source of each FNOL field value",
    tags=["FNOL"],
)
def save_field_attribution(req: SaveFieldAttributionRequest):
    """
    Saves attribution records showing where each FNOL field value came from
    (voice transcript, text input, AI inferred, or manually entered).
    Supports the confidence and audit display in the UI.
    """
    try:
        return fnol_handler.save_field_attribution(req)
    except Exception as e:
        log.exception("save_field_attribution error")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Draft Cleanup
# ──────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/api/fnol/cleanup_drafts/{policy_number}",
    operation_id="cleanup_draft_fnols",
    summary="Delete all draft FNOL submissions and their child records for a policy",
    tags=["FNOL"],
)
def cleanup_draft_fnols(policy_number: str):
    """
    Removes every fnol_submissions row in 'draft' status for the given
    policy_number, along with all linked rows in fnol_ai_inferences,
    fnol_voice_text_extraction, fnol_mandatory_question_log, and
    fnol_field_attribution.

    Called automatically by create_fnol_submission. Also call this explicitly
    at the start of a new session or after an error to guarantee a clean slate.
    Returns the count of draft submissions removed.
    """
    try:
        removed = fnol_handler.cleanup_draft_fnols_for_policy(policy_number)
        return {"policy_number": policy_number, "drafts_removed": removed}
    except Exception as e:
        log.exception("cleanup_draft_fnols error")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Voice / Text Extraction via LLM
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/api/voice/extract_fields",
    operation_id="extract_fnol_fields_from_text",
    summary="Extract structured FNOL fields from free text or browser voice transcript using LLM",
    tags=["Voice"],
)
def extract_fnol_fields_from_text(req: ExtractFnolFieldsRequest):
    """
    Sends raw_text (a browser-generated voice transcript or typed input) to
    Azure OpenAI and extracts structured FNOL fields (loss_type, cause_of_loss,
    date_of_loss, area_affected, etc.) with per-field confidence scores.
    Automatically:
      1. Saves the extraction result to fnol_voice_text_extraction.
      2. Creates ai_inference records for all extracted fields.
      3. Writes non-null extracted values back to fnol_submissions so the
         orchestrator does not need a separate update_fnol_submission call to
         persist fields that were captured in this turn.
    Returns the full extraction JSON from the LLM.
    """
    try:
        extraction = voice_handler.extract_fnol_fields(req.raw_text)

        if "error" in extraction:
            raise HTTPException(status_code=502, detail=extraction["error"])

        fields = extraction.get("fields", {})

        # ── 1. Save raw extraction row ──────────────────────────────────────
        field_col_map = {
            "loss_type":         "extracted_loss_type",
            "cause_of_loss":     "extracted_cause",
            "area_affected":     "extracted_area",
            "date_of_loss":      "extracted_temporal",
            "sudden_vs_gradual": "sudden_gradual_signal",
            "emotional_context": "emotional_context",
        }
        raw_conf = extraction.get("overall_confidence")
        save_kwargs = {
            "fnol_id":              req.fnol_id,
            "input_type":           req.input_type or "text",
            "raw_input":            req.raw_text,
            "transcribed_text":     req.raw_text if req.input_type == "voice_transcript" else None,
            # LLM may return float (e.g. 85.5); DB column is INTEGER — round here (#14)
            "extraction_confidence": int(round(raw_conf)) if raw_conf is not None else None,
        }
        for field_name, col in field_col_map.items():
            if field_name in fields and fields[field_name].get("value") is not None:
                save_kwargs[col] = str(fields[field_name]["value"])

        fnol_handler.save_voice_text_extraction(SaveVoiceTextExtractionRequest(**save_kwargs))

        # ── 2. Save per-field AI inference records ──────────────────────────
        inferences = []
        for field_name, info in fields.items():
            if info.get("value") is not None:
                raw_c = info.get("confidence")
                inferences.append(
                    AiInferenceItem(
                        field_name=field_name,
                        inferred_value=str(info["value"]),
                        # LLM may return float; DB column INTEGER — round (#15)
                        confidence=int(round(raw_c)) if raw_c is not None else None,
                        source=req.input_type or "text",
                        source_details=info.get("source_snippet"),
                    )
                )
        if inferences:
            fnol_handler.save_ai_inferences(
                SaveAiInferencesRequest(fnol_id=req.fnol_id, inferences=inferences)
            )

        # ── 3. Auto-persist extracted values to fnol_submissions ─────────────
        # Map extraction field names → UpdateFnolSubmissionRequest field names.
        # This ensures the FNOL record reflects the extracted data immediately,
        # without relying on the orchestrator LLM to issue a separate
        # update_fnol_submission call (which it sometimes skips).
        fnol_field_map = {
            "loss_type":          "loss_type",
            "cause_of_loss":      "cause_of_loss",
            "date_of_loss":       "date_of_loss",
            "time_of_loss":       "time_of_loss",
            "area_affected":      "area_affected",
            "sudden_vs_gradual":  "sudden_vs_gradual",
            "emotional_context":  "emotional_context",
            "severity":           "severity",
            "urgency_indicator":  "urgency_indicator",
        }
        # Corresponding _source column for each field — written alongside the
        # value so Stage 2 / Stage 3 UI can show the correct attribution badge.
        source_col_map = {
            "loss_type":          "loss_type_source",
            "cause_of_loss":      "cause_of_loss_source",
            "date_of_loss":       "date_of_loss_source",
            "time_of_loss":       "time_of_loss_source",
            "area_affected":      "area_affected_source",
            "sudden_vs_gradual":  "sudden_vs_gradual_source",
            "emotional_context":  "emotional_context_source",
            "severity":           "severity_source",
            "urgency_indicator":  "urgency_indicator_source",
        }
        # Source label is determined by how the user submitted this turn.
        field_source = "voice_transcript" if req.input_type == "voice_transcript" else "text_input"

        update_data: dict = {}
        for ext_field, sub_field in fnol_field_map.items():
            info = fields.get(ext_field, {})
            val = info.get("value")
            if val is not None:
                update_data[sub_field] = str(val)
                src_col = source_col_map.get(ext_field)
                if src_col:
                    update_data[src_col] = field_source

        # occupancy_at_loss comes back as bool/string — normalise to int (1/0)
        # because the DB column is INTEGER, not BOOLEAN; psycopg2 sends Python
        # bool as PostgreSQL BOOLEAN which PostgreSQL won't cast to INTEGER.
        occ_info = fields.get("occupancy_at_loss", {})
        occ_val = occ_info.get("value")
        if occ_val is not None:
            if isinstance(occ_val, bool):
                update_data["occupancy_at_loss"] = int(occ_val)
            elif isinstance(occ_val, str):
                update_data["occupancy_at_loss"] = 1 if occ_val.lower() in ("true", "yes", "1") else 0
            update_data["occupancy_at_loss_source"] = field_source

        if update_data:
            try:
                fnol_handler.update_fnol_submission(
                    req.fnol_id,
                    UpdateFnolSubmissionRequest(**update_data),
                )
                extraction["auto_persist_status"] = "ok"
            except Exception as exc:
                log.warning("Auto-update of fnol_submissions failed: %s", exc, exc_info=True)
                # Surface failure so the orchestrator can detect it and call
                # update_fnol_submission explicitly (#9)
                extraction["auto_persist_status"] = "failed"
                extraction["auto_persist_error"] = str(exc)

        overall_confidence = extraction.get("overall_confidence")
        if overall_confidence is not None:
            try:
                fnol_handler.update_fnol_submission(
                    req.fnol_id,
                    UpdateFnolSubmissionRequest(
                        overall_confidence=int(round(overall_confidence))
                        if isinstance(overall_confidence, float) else overall_confidence
                    ),
                )
            except Exception:
                log.warning("Failed to persist overall_confidence", exc_info=True)  # (#16)

        return extraction
    except HTTPException:
        raise
    except Exception as e:
        log.exception("extract_fnol_fields_from_text error")
        raise HTTPException(status_code=500, detail=str(e))


