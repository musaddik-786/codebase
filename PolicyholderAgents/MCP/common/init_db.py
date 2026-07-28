"""
init_db.py
──────────
Creates all PostgreSQL tables for the Policyholder Agents platform and seeds
reference/sample data. Safe to re-run (idempotent).

Run:
    py -3 MCP/common/init_db.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import get_db_connection  # noqa: E402

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS claims (
    id SERIAL PRIMARY KEY,
    claim_number TEXT UNIQUE,
    policyholder_name TEXT,
    policy_number TEXT,
    loss_type TEXT,
    short_description TEXT,
    ai_generated_summary TEXT,
    detected_cause TEXT,
    severity TEXT,
    complexity TEXT,
    estimated_cost REAL,
    coverage INTEGER DEFAULT 1,
    ai_confidence INTEGER,
    status TEXT DEFAULT 'Open',
    location TEXT,
    assigned_adjuster TEXT,
    assigned_vendor TEXT,
    date_of_loss TEXT,
    filed_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claims_master (
    id SERIAL PRIMARY KEY,
    claim_number TEXT UNIQUE,
    policyholder_name TEXT,
    policy_number TEXT,
    loss_type TEXT,
    date_of_loss TEXT,
    coverage_limit REAL,
    deductible REAL,
    status TEXT
);

CREATE TABLE IF NOT EXISTS claim_journey_master (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER,
    claim_number TEXT,
    current_stage INTEGER DEFAULT 1,
    current_stage_name TEXT DEFAULT 'Claim Initiated',
    sub_status TEXT DEFAULT 'Under Review',
    journey_start_date TIMESTAMP DEFAULT NOW(),
    last_stage_change_date TIMESTAMP DEFAULT NOW(),
    expected_completion_date TEXT,
    overall_sla_status TEXT DEFAULT 'on_track',
    total_days_in_journey INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS stage_time_sla_tracking (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER,
    claim_number TEXT,
    stage_number INTEGER,
    stage_name TEXT,
    entered_at TIMESTAMP DEFAULT NOW(),
    exited_at TIMESTAMP,
    sla_days INTEGER,
    sla_status TEXT
);

CREATE TABLE IF NOT EXISTS policy_details (
    id SERIAL PRIMARY KEY,
    policy_number TEXT UNIQUE,
    gw_policy_id TEXT,
    status TEXT DEFAULT 'Active',
    coverage_type TEXT,
    deductible REAL,
    coverage_limit REAL,
    remaining_coverage_limit REAL,
    exclusions TEXT,
    effective_date TEXT,
    expiration_date TEXT,
    policyholder_name TEXT,
    account_number TEXT,
    policy_address TEXT,
    state TEXT,
    term_type TEXT,
    premium_amount REAL,
    currency TEXT,
    city TEXT,
    country TEXT,
    postal_code TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS coverage_verification_results (
    id SERIAL PRIMARY KEY,
    claim_number TEXT UNIQUE,
    policy_number TEXT,
    coverage_verdict TEXT,
    exclusion_triggered INTEGER DEFAULT 0,
    exclusion_details TEXT,
    net_payable REAL,
    coverage_notes TEXT,
    verified_at TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claim_payments (
    id SERIAL PRIMARY KEY,
    payment_id TEXT UNIQUE,
    claim_number TEXT,
    policy_number TEXT,
    amount_paid REAL,
    payment_date TEXT,
    approved_by TEXT,
    payment_status TEXT DEFAULT 'Released',
    coverage_before REAL,
    coverage_after REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fnol_submissions (
    id SERIAL PRIMARY KEY,
    fnol_number TEXT UNIQUE,
    policy_number TEXT,
    policyholder_name TEXT,
    policyholder_address TEXT,
    policy_effective_date TEXT,
    policy_expiration_date TEXT,
    loss_type TEXT,
    loss_type_source TEXT,
    cause_of_loss TEXT,
    cause_of_loss_source TEXT,
    date_of_loss TEXT,
    date_of_loss_source TEXT,
    time_of_loss TEXT,
    time_of_loss_source TEXT,
    area_affected TEXT,
    area_affected_source TEXT,
    occupancy_at_loss INTEGER,
    occupancy_at_loss_source TEXT,
    sudden_vs_gradual TEXT,
    sudden_vs_gradual_source TEXT,
    emotional_context TEXT,
    emotional_context_source TEXT,
    severity TEXT,
    severity_source TEXT,
    urgency_indicator TEXT,
    urgency_indicator_source TEXT,
    voice_transcript TEXT,
    text_input TEXT,
    overall_confidence INTEGER,
    confidence_notes TEXT,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    submitted_at TIMESTAMP
);
ALTER TABLE fnol_submissions ADD COLUMN IF NOT EXISTS estimated_cost REAL;

CREATE TABLE IF NOT EXISTS fnol_mandatory_fields (
    id SERIAL PRIMARY KEY,
    field_name TEXT UNIQUE,
    field_label TEXT,
    field_category TEXT,
    is_required INTEGER DEFAULT 1,
    can_be_inferred INTEGER DEFAULT 1,
    inference_question TEXT,
    input_type TEXT DEFAULT 'text',
    input_options TEXT,
    display_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fnol_ai_inferences (
    id SERIAL PRIMARY KEY,
    fnol_id INTEGER,
    field_name TEXT,
    inferred_value TEXT,
    confidence INTEGER,
    source TEXT,
    source_details TEXT,
    customer_confirmed INTEGER DEFAULT 0,
    customer_edited_value TEXT,
    inferred_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fnol_voice_text_extraction (
    id SERIAL PRIMARY KEY,
    fnol_id INTEGER,
    input_type TEXT,
    raw_input TEXT,
    transcribed_text TEXT,
    extracted_loss_type TEXT,
    extracted_cause TEXT,
    extracted_area TEXT,
    extracted_temporal TEXT,
    sudden_gradual_signal TEXT,
    emotional_context TEXT,
    extraction_confidence INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fnol_mandatory_question_log (
    id SERIAL PRIMARY KEY,
    fnol_id INTEGER,
    question_text TEXT,
    field_name TEXT,
    answer_text TEXT,
    answer_type TEXT,
    was_skipped INTEGER DEFAULT 0,
    question_order INTEGER DEFAULT 0,
    asked_at TIMESTAMP DEFAULT NOW(),
    answered_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fnol_field_attribution (
    id SERIAL PRIMARY KEY,
    fnol_id INTEGER,
    field_name TEXT,
    field_label TEXT,
    field_value TEXT,
    source TEXT,
    confidence INTEGER,
    was_edited INTEGER DEFAULT 0,
    was_confirmed INTEGER DEFAULT 0,
    original_value TEXT,
    edited_value TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    confirmed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    document_id TEXT UNIQUE,
    claim_number TEXT,
    file_name TEXT,
    file_url TEXT,
    file_size INTEGER,
    content_type TEXT,
    document_type TEXT,
    classification_confidence INTEGER DEFAULT 0,
    uploaded_by TEXT,
    uploaded_by_role TEXT,
    status TEXT DEFAULT 'Classified',
    visibility TEXT DEFAULT 'public',
    extracted_data TEXT,
    insights TEXT,
    investigation_notes TEXT,
    flagged INTEGER DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customer_feedback_per_stage (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    claim_number TEXT,
    stage_number INTEGER,
    stage_name TEXT,
    sentiment TEXT,
    sentiment_score REAL,
    comment TEXT,
    submitted_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claim_sentiment_tracker (
    id SERIAL PRIMARY KEY,
    tracker_id TEXT UNIQUE,
    claim_row_id TEXT,
    claim_number TEXT,
    policyholder_name TEXT,
    current_sentiment TEXT,
    sentiment_score REAL,
    sentiment_trend TEXT,
    last_interaction_date TEXT,
    escalation_risk TEXT,
    satisfaction_rating REAL,
    nps_score INTEGER,
    notes TEXT,
    assigned_adjuster TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS communication_history (
    id SERIAL PRIMARY KEY,
    communication_id TEXT UNIQUE,
    claim_row_id TEXT,
    claim_number TEXT,
    policyholder_name TEXT,
    communication_type TEXT,
    direction TEXT,
    subject TEXT,
    summary TEXT,
    sentiment_detected TEXT,
    handled_by TEXT,
    response_time_minutes INTEGER,
    resolution_status TEXT,
    follow_up_required INTEGER DEFAULT 0,
    follow_up_date TEXT,
    attachments TEXT,
    communication_date TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS segmentation_result_output (
    id SERIAL PRIMARY KEY,
    claim_number TEXT UNIQUE,
    severity TEXT,
    complexity TEXT,
    stp_score INTEGER,
    recommended_path TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stp_classification (
    id SERIAL PRIMARY KEY,
    stp_id TEXT,
    claim_number TEXT UNIQUE,
    readiness INTEGER DEFAULT 0,
    fraud_ambiguity TEXT DEFAULT 'Low',
    subrogation TEXT DEFAULT 'Low',
    vis INTEGER DEFAULT 0,
    stp_score INTEGER DEFAULT 0,
    stp_category TEXT DEFAULT 'Manual Review',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS intake_validation_result_output (
    id SERIAL PRIMARY KEY,
    claim_number TEXT UNIQUE,
    completeness_score INTEGER,
    missing_fields TEXT,
    coverage_status TEXT,
    docs_status TEXT DEFAULT 'Not Checked',
    missing_docs TEXT,
    fraud_risk TEXT,
    fraud_risk_score INTEGER,
    fraud_flags TEXT,
    recommendation TEXT,
    overall_result TEXT,
    validated_at TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policyholder_actions (
    id SERIAL PRIMARY KEY,
    claim_row_id TEXT,
    claim_number TEXT,
    action_type TEXT,
    action_label TEXT,
    details TEXT,
    stage_at_action INTEGER,
    performed_by TEXT DEFAULT 'Policyholder',
    timestamp TIMESTAMP DEFAULT NOW()
);
"""


MANDATORY_FIELDS = [
    ("loss_type", "Type of Loss", "loss_details", 1, 1,
     "What type of loss occurred (e.g. water damage, fire, theft)?", "text", None, 1),
    ("cause_of_loss", "Cause of Loss", "loss_details", 1, 1,
     "What caused the loss?", "text", None, 2),
    ("date_of_loss", "Date of Loss", "loss_details", 1, 1,
     "On what date did the loss occur?", "date", None, 3),
    ("time_of_loss", "Time of Loss", "loss_details", 1, 1,
     "Approximately what time did the loss occur?", "time", None, 4),
    ("area_affected", "Area Affected", "loss_details", 1, 1,
     "Which room or area was affected?", "text", None, 5),
    ("occupancy_at_loss", "Occupancy at Time of Loss", "loss_details", 1, 1,
     "Was the property occupied at the time of the loss?", "boolean", None, 6),
    ("sudden_vs_gradual", "Sudden or Gradual", "loss_details", 1, 1,
     "Did this happen suddenly or develop gradually over time?", "select",
     '["Sudden", "Gradual"]', 7),
    ("severity", "Severity", "loss_details", 1, 1,
     "How severe would you say the damage is — minor, moderate, or severe?", "select",
     '["Low", "Medium", "High", "Critical"]', 8),
    ("policyholder_address", "Policyholder Property Address", "policy_details", 1, 1,
     "What is the address of the insured property?", "text", None, 9),
    ("policy_number", "Policy Number", "policy_details", 1, 1,
     "What is your policy number?", "text", None, 10),
]


def init_db():
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Execute schema (CREATE TABLE IF NOT EXISTS is idempotent)
        cur.execute(SCHEMA_SQL)

        # Column migrations — safely add columns that may be missing from
        # tables created by an earlier schema version.
        migrations = [
            "ALTER TABLE claims ADD COLUMN IF NOT EXISTS complexity TEXT",
            "ALTER TABLE claims ADD COLUMN IF NOT EXISTS ai_generated_summary TEXT",
            "ALTER TABLE claims ADD COLUMN IF NOT EXISTS detected_cause TEXT",
            "ALTER TABLE claims ADD COLUMN IF NOT EXISTS assigned_adjuster TEXT",
            "ALTER TABLE claims ADD COLUMN IF NOT EXISTS assigned_vendor TEXT",
            "ALTER TABLE claims ADD COLUMN IF NOT EXISTS police_report_number TEXT",
            "ALTER TABLE claim_journey_master ADD COLUMN IF NOT EXISTS sub_status TEXT DEFAULT 'Under Review'",
            "ALTER TABLE claim_journey_master ADD COLUMN IF NOT EXISTS overall_sla_status TEXT DEFAULT 'on_track'",
            # policy_details extended columns
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS gw_policy_id TEXT",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS remaining_coverage_limit REAL",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS exclusions TEXT",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS effective_date TEXT",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS expiration_date TEXT",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS policyholder_name TEXT",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS account_number TEXT",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS policy_address TEXT",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS state TEXT",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS term_type TEXT",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS premium_amount REAL",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS currency TEXT",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS city TEXT",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS country TEXT",
            "ALTER TABLE policy_details ADD COLUMN IF NOT EXISTS postal_code TEXT",
            # customer_feedback_per_stage — add sentiment_score column
            "ALTER TABLE customer_feedback_per_stage ADD COLUMN IF NOT EXISTS sentiment_score REAL",
            # stp_classification — add missing stp_score column and unique constraint
            "ALTER TABLE stp_classification ADD COLUMN IF NOT EXISTS stp_score INTEGER DEFAULT 0",
            # intake_validation_result_output — add missing columns for existing DBs
            "ALTER TABLE intake_validation_result_output ADD COLUMN IF NOT EXISTS missing_fields TEXT",
            "ALTER TABLE intake_validation_result_output ADD COLUMN IF NOT EXISTS docs_status TEXT DEFAULT 'Not Checked'",
            "ALTER TABLE intake_validation_result_output ADD COLUMN IF NOT EXISTS missing_docs TEXT",
            "ALTER TABLE intake_validation_result_output ADD COLUMN IF NOT EXISTS fraud_risk_score INTEGER",
            "ALTER TABLE intake_validation_result_output ADD COLUMN IF NOT EXISTS fraud_flags TEXT",
            "ALTER TABLE intake_validation_result_output ADD COLUMN IF NOT EXISTS recommendation TEXT",
            "ALTER TABLE intake_validation_result_output ADD COLUMN IF NOT EXISTS overall_result TEXT",
            "ALTER TABLE intake_validation_result_output ADD COLUMN IF NOT EXISTS validated_at TEXT",
            # Deduplicate before adding unique indexes (keep latest row per claim_number)
            "DELETE FROM intake_validation_result_output WHERE id NOT IN (SELECT MAX(id) FROM intake_validation_result_output GROUP BY claim_number)",
            "DELETE FROM stp_classification WHERE id NOT IN (SELECT MAX(id) FROM stp_classification GROUP BY claim_number)",
            "DELETE FROM segmentation_result_output WHERE id NOT IN (SELECT MAX(id) FROM segmentation_result_output GROUP BY claim_number)",
            # Unique indexes — required for ON CONFLICT (claim_number) DO UPDATE in handlers
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_intake_validation_claim_number ON intake_validation_result_output(claim_number)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_stp_classification_claim_number ON stp_classification(claim_number)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_segmentation_result_claim_number ON segmentation_result_output(claim_number)",
            # Rename the pre-rename "insured_address" mandatory field row left over
            # from an earlier schema version — ON CONFLICT DO NOTHING in the seed
            # loop below can't fix this since policyholder_address is a different
            # field_name, so the stale row would otherwise never update.
            """
            UPDATE fnol_mandatory_fields
               SET field_name = 'policyholder_address',
                   field_label = 'Policyholder Property Address'
             WHERE field_name = 'insured_address'
               AND NOT EXISTS (
                   SELECT 1 FROM fnol_mandatory_fields WHERE field_name = 'policyholder_address'
               )
            """,
            # Some DBs already had both rows (a newer init_db seeded
            # policyholder_address before this instance's insured_address row was
            # ever renamed) — the UPDATE above is then a no-op, so drop the
            # redundant leftover directly. fnol_ai_inferences /
            # fnol_mandatory_question_log store field_name as plain text with no
            # FK, so this is safe and doesn't touch audit history.
            """
            DELETE FROM fnol_mandatory_fields
             WHERE field_name = 'insured_address'
               AND EXISTS (
                   SELECT 1 FROM fnol_mandatory_fields WHERE field_name = 'policyholder_address'
               )
            """,
        ]
        for m in migrations:
            cur.execute(m)

        # Seed mandatory fields
        for row in MANDATORY_FIELDS:
            cur.execute(
                """
                INSERT INTO fnol_mandatory_fields (
                    field_name, field_label, field_category, is_required,
                    can_be_inferred, inference_question, input_type,
                    input_options, display_order
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (field_name) DO NOTHING
                """,
                row,
            )

        # Seed sample policy
        cur.execute(
            """
            INSERT INTO policy_details (policy_number, status, coverage_type, deductible, coverage_limit)
            VALUES ('POL-1001', 'Active', 'Homeowners', 1000, 250000)
            ON CONFLICT DO NOTHING
            """
        )
        cur.execute(
            """
            INSERT INTO policy_details (policy_number, status, coverage_type, deductible, coverage_limit)
            VALUES ('POL-1002', 'Active', 'Auto', 500, 50000)
            ON CONFLICT DO NOTHING
            """
        )

        # Seed sample claim
        cur.execute("SELECT COUNT(*) FROM claims WHERE claim_number = 'CLM-2026-1001'")
        count = cur.fetchone()["count"]
        if count == 0:
            cur.execute(
                """
                INSERT INTO claims (
                    claim_number, policyholder_name, policy_number, loss_type,
                    short_description, severity, complexity, estimated_cost,
                    coverage, ai_confidence, status, location, date_of_loss
                ) VALUES (
                    'CLM-2026-1001', 'John Doe', 'POL-1001', 'Water Damage',
                    'Burst pipe in kitchen caused flooding', 'Medium', 'Low', 8500,
                    TRUE, 85, 'Open', '123 Main St, Springfield', '2026-05-20'
                ) RETURNING id
                """
            )
            claim_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO claims_master (
                    claim_number, policyholder_name, policy_number, loss_type,
                    date_of_loss, coverage_limit, deductible, status
                ) VALUES (
                    'CLM-2026-1001', 'John Doe', 'POL-1001', 'Homeowners',
                    '2026-05-20', 250000, 1000, 'Open'
                ) ON CONFLICT (claim_number) DO NOTHING
                """
            )

            cur.execute("SELECT COUNT(*) FROM claim_journey_master WHERE claim_number = 'CLM-2026-1001'")
            if cur.fetchone()["count"] == 0:
                cur.execute(
                    """
                    INSERT INTO claim_journey_master (
                        claim_id, claim_number, current_stage, current_stage_name,
                        sub_status, overall_sla_status
                    ) VALUES (%s, 'CLM-2026-1001', 1, 'Claim Initiated', 'Under Review', 'on_track')
                    """,
                    (claim_id,),
                )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized on Azure PostgreSQL.")
