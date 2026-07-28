"""
fnol_handler.py
───────────────
DB operations for FNOL submissions, inferences, question log,
field attribution, and voice/text extractions.
Uses psycopg2 with RealDictCursor (Azure PostgreSQL).
"""

import logging
import random
from datetime import datetime
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from voice_text_intake_mcp.models import (
    CreateFnolSubmissionRequest,
    UpdateFnolSubmissionRequest,
    SaveVoiceTextExtractionRequest,
    SaveAiInferencesRequest,
    LogQuestionAnswerRequest,
    SaveFieldAttributionRequest,
)

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# FNOL Submissions
# ──────────────────────────────────────────────────────────────────────────────

def cleanup_draft_fnols_for_policy(policy_number: str, conn=None) -> int:
    """
    Delete all draft fnol_submissions for *policy_number* and their child rows.
    Called automatically before creating a new FNOL so reruns and error cases
    don't accumulate orphaned draft data.

    Returns the number of draft submissions removed.
    """
    _own_conn = conn is None
    if _own_conn:
        conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM fnol_submissions WHERE policy_number = %s AND status = 'draft'",
            (policy_number,),
        )
        draft_ids = [r["id"] for r in cur.fetchall()]
        if not draft_ids:
            return 0

        placeholders = ",".join("%s" for _ in draft_ids)
        for child_table in (
            "fnol_ai_inferences",
            "fnol_voice_text_extraction",
            "fnol_mandatory_question_log",
            "fnol_field_attribution",
        ):
            cur.execute(
                f"DELETE FROM {child_table} WHERE fnol_id IN ({placeholders})",
                draft_ids,
            )
        cur.execute(
            f"DELETE FROM fnol_submissions WHERE id IN ({placeholders})",
            draft_ids,
        )
        if _own_conn:
            conn.commit()
        log.info("Cleaned up %d draft FNOL(s) for policy %s", len(draft_ids), policy_number)
        return len(draft_ids)
    except Exception:
        if _own_conn:
            conn.rollback()
        log.exception("cleanup_draft_fnols_for_policy failed for policy %s", policy_number)
        raise
    finally:
        if _own_conn:
            conn.close()


def create_fnol_submission(req: CreateFnolSubmissionRequest) -> dict:
    # Auto-generate fnol_number if the LLM didn't supply one (#6)
    if not req.fnol_number:
        req.fnol_number = f"FNOL-{datetime.now().year}-{random.randint(10000, 99999)}"
    conn = get_db_connection()
    try:
        # Wipe any previous draft FNOLs for this policy so reruns start clean.
        cleanup_draft_fnols_for_policy(req.policy_number, conn=conn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO fnol_submissions (
                fnol_number, policy_number, policyholder_name, policyholder_address,
                policy_effective_date, policy_expiration_date,
                loss_type, loss_type_source, cause_of_loss, cause_of_loss_source,
                date_of_loss, date_of_loss_source, time_of_loss, time_of_loss_source,
                area_affected, area_affected_source, occupancy_at_loss, occupancy_at_loss_source,
                sudden_vs_gradual, emotional_context, severity, urgency_indicator,
                voice_transcript, text_input, overall_confidence, confidence_notes,
                status, created_at, updated_at
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,'ai_inferred',%s,'ai_inferred',
                %s,'ai_inferred',%s,'ai_inferred',%s,'ai_inferred',%s,'ai_inferred',
                %s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW()
            ) RETURNING *
            """,
            (
                req.fnol_number, req.policy_number, req.policyholder_name, req.policyholder_address,
                req.policy_effective_date, req.policy_expiration_date,
                req.loss_type, req.cause_of_loss,
                req.date_of_loss, req.time_of_loss,
                req.area_affected,
                # Column is INTEGER; psycopg2 sends Python bool as PostgreSQL BOOLEAN
                # which PostgreSQL won't implicitly cast to INTEGER.
                int(req.occupancy_at_loss) if req.occupancy_at_loss is not None else None,
                req.sudden_vs_gradual, req.emotional_context, req.severity, req.urgency_indicator,
                req.voice_transcript, req.text_input, req.overall_confidence, req.confidence_notes,
                req.status or "draft",
            ),
        )
        result = cur.fetchone()
        conn.commit()
        return row_to_dict(result)
    except Exception:
        conn.rollback()
        log.exception("create_fnol_submission failed")
        raise
    finally:
        conn.close()


def get_fnol_submission_by_id(fnol_id: int) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM fnol_submissions WHERE id = %s", (fnol_id,))
        return row_to_dict(cur.fetchone())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_fnol_submission_by_policy(policy_number: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM fnol_submissions WHERE policy_number = %s ORDER BY created_at DESC",
            (policy_number,),
        )
        return row_to_dict(cur.fetchall())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


_UPDATABLE_COLUMNS = {
    "policy_number", "policyholder_name", "policyholder_address",
    "loss_type", "loss_type_source",
    "cause_of_loss", "cause_of_loss_source",
    "date_of_loss", "date_of_loss_source",
    "time_of_loss", "time_of_loss_source",
    "area_affected", "area_affected_source",
    "occupancy_at_loss", "occupancy_at_loss_source",
    "sudden_vs_gradual", "sudden_vs_gradual_source",
    "emotional_context", "emotional_context_source",
    "severity", "severity_source",
    "urgency_indicator", "urgency_indicator_source",
    "voice_transcript", "text_input", "overall_confidence",
    "confidence_notes", "status", "estimated_cost",
}


def update_fnol_submission(fnol_id: int, req: UpdateFnolSubmissionRequest) -> Optional[dict]:
    raw = req.model_dump(exclude_none=True)
    # Whitelist: only allow known columns to reach the dynamic SQL (#5)
    fields = {k: v for k, v in raw.items() if k in _UPDATABLE_COLUMNS}
    if not fields:
        return get_fnol_submission_by_id(fnol_id)

    # psycopg2 maps Python bool → PostgreSQL BOOLEAN, but occupancy_at_loss
    # is INTEGER; convert to int to avoid implicit-cast failure.
    fields = {k: int(v) if isinstance(v, bool) else v for k, v in fields.items()}

    set_clauses = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [fnol_id]

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE fnol_submissions SET {set_clauses}, updated_at = NOW() WHERE id = %s RETURNING *",
            values,
        )
        result = cur.fetchone()
        conn.commit()
        return row_to_dict(result)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def submit_fnol(fnol_id: int) -> dict:
    """
    Marks an FNOL as submitted, sets submitted_at timestamp, and creates
    claims / claims_master / claim_journey_master records if none exist
    for the policy yet.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT * FROM fnol_submissions WHERE id = %s", (fnol_id,))
        fnol = row_to_dict(cur.fetchone())   # use row_to_dict consistently (#3)
        if not fnol:
            raise ValueError(f"FNOL with id={fnol_id} not found")

        cur.execute(
            """
            UPDATE fnol_submissions
            SET status = 'submitted', submitted_at = NOW(), updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (fnol_id,),
        )
        updated = row_to_dict(cur.fetchone())

        claim_number = None
        if fnol.get("policy_number"):
            # Always create a new claim for each FNOL — never reuse an existing one (#2)
            claim_number = f"CLM-{datetime.now().year}-{random.randint(1000, 9999)}"
            cur.execute(
                """
                INSERT INTO claims (
                    claim_number, policyholder_name, policy_number,
                    loss_type, short_description, severity, estimated_cost, status,
                    date_of_loss, location, filed_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s, 'Open', %s,%s, NOW())
                RETURNING id
                """,
                (
                    claim_number,
                    fnol.get("policyholder_name") or "Unknown",
                    fnol["policy_number"],
                    fnol.get("loss_type") or "Unknown",
                    fnol.get("cause_of_loss") or "Reported via FNOL intake",
                    fnol.get("severity") or "Medium",
                    fnol.get("estimated_cost"),
                    fnol.get("date_of_loss"),
                    fnol.get("policyholder_address"),
                ),
            )
            claim_id = cur.fetchone()["id"]

            cur.execute(
                "SELECT coverage_limit, deductible FROM policy_details WHERE policy_number = %s LIMIT 1",
                (fnol["policy_number"],),
            )
            pd_row = cur.fetchone()
            p_coverage_limit = pd_row["coverage_limit"] if pd_row and pd_row["coverage_limit"] else 0
            p_deductible = pd_row["deductible"] if pd_row and pd_row["deductible"] else 0

            cur.execute(
                """
                INSERT INTO claims_master (
                    claim_number, policyholder_name, policy_number, loss_type,
                    date_of_loss, coverage_limit, deductible, status
                ) VALUES (%s,%s,%s,%s,%s,%s,%s, 'Open')
                """,
                (
                    claim_number,
                    fnol.get("policyholder_name") or "Unknown",
                    fnol["policy_number"],
                    fnol.get("loss_type") or "Unknown",
                    fnol.get("date_of_loss"),
                    p_coverage_limit,
                    p_deductible,
                ),
            )

            cur.execute(
                """
                INSERT INTO claim_journey_master (
                    claim_id, claim_number, current_stage, current_stage_name,
                    sub_status, overall_sla_status
                ) VALUES (%s,%s,1,'Claim Initiated','Under Review','on_track')
                """,
                (claim_id, claim_number),
            )

        conn.commit()
        return {"fnol": updated, "claim_number": claim_number, "status": "submitted"}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Mandatory Fields Reference
# ──────────────────────────────────────────────────────────────────────────────

def get_mandatory_fields() -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM fnol_mandatory_fields ORDER BY display_order")
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Voice / Text Extractions
# ──────────────────────────────────────────────────────────────────────────────

def save_voice_text_extraction(req: SaveVoiceTextExtractionRequest) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO fnol_voice_text_extraction (
                fnol_id, input_type, raw_input, transcribed_text,
                extracted_loss_type, extracted_cause, extracted_area,
                extracted_temporal, sudden_gradual_signal, emotional_context,
                extraction_confidence, created_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
            RETURNING *
            """,
            (
                req.fnol_id, req.input_type, req.raw_input, req.transcribed_text,
                req.extracted_loss_type, req.extracted_cause, req.extracted_area,
                req.extracted_temporal, req.sudden_gradual_signal, req.emotional_context,
                req.extraction_confidence,
            ),
        )
        result = cur.fetchone()
        conn.commit()
        return row_to_dict(result)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_voice_text_extractions(fnol_id: int) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM fnol_voice_text_extraction WHERE fnol_id = %s ORDER BY created_at",
            (fnol_id,),
        )
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# AI Inferences
# ──────────────────────────────────────────────────────────────────────────────

def save_ai_inferences(req: SaveAiInferencesRequest) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        created = []
        for item in req.inferences:
            cur.execute(
                """
                INSERT INTO fnol_ai_inferences (
                    fnol_id, field_name, inferred_value, confidence,
                    source, source_details, customer_confirmed, inferred_at
                ) VALUES (%s,%s,%s,%s,%s,%s,0,NOW())
                RETURNING *
                """,
                (
                    req.fnol_id, item.field_name, item.inferred_value,
                    item.confidence, item.source, item.source_details,
                ),
            )
            created.append(row_to_dict(cur.fetchone()))
        conn.commit()
        return created
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Mandatory Question Log
# ──────────────────────────────────────────────────────────────────────────────

def log_question_answer(req: LogQuestionAnswerRequest) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        answered_at = datetime.utcnow().isoformat() if req.answer_text else None
        cur.execute(
            """
            INSERT INTO fnol_mandatory_question_log (
                fnol_id, question_text, field_name, answer_text,
                answer_type, was_skipped, question_order,
                asked_at, answered_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,NOW(),%s)
            RETURNING *
            """,
            (
                req.fnol_id, req.question_text, req.field_name,
                req.answer_text, req.answer_type, int(req.was_skipped or False),
                req.question_order or 0, answered_at,
            ),
        )
        result = cur.fetchone()
        conn.commit()
        return row_to_dict(result)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_question_log(fnol_id: int) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM fnol_mandatory_question_log WHERE fnol_id = %s ORDER BY question_order",
            (fnol_id,),
        )
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Field Attribution
# ──────────────────────────────────────────────────────────────────────────────

def save_field_attribution(req: SaveFieldAttributionRequest) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        created = []
        for item in req.attributions:
            cur.execute(
                """
                INSERT INTO fnol_field_attribution (
                    fnol_id, field_name, field_label, field_value, source,
                    confidence, was_edited, was_confirmed, original_value,
                    edited_value, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                RETURNING *
                """,
                (
                    req.fnol_id, item.field_name, item.field_label,
                    item.field_value, item.source, item.confidence,
                    int(item.was_edited or False), int(item.was_confirmed or False),
                    item.original_value, item.edited_value,
                ),
            )
            created.append(row_to_dict(cur.fetchone()))
        conn.commit()
        return created
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
