"""
init_db.py
──────────
Creates all PostgreSQL tables needed by the Adjuster Agents platform in the
Azure PostgreSQL claims database and seeds
reference/sample data. Safe to re-run (idempotent). Uses
CREATE TABLE IF NOT EXISTS everywhere so it never clobbers tables already
created by PolicyholderAgents' init_db, and is safe to run before or after
that one.

Run:
    py -3 MCP/common/init_db.py  (against Azure PostgreSQL)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import get_db_connection  # noqa: E402

SCHEMA_SQL = """
-- Minimal re-declaration of shared tables (already created by
-- PolicyholderAgents' init_db, but declared here defensively so this
-- script is safe to run first on a fresh db).
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
    filed_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policy_details (
    id SERIAL PRIMARY KEY,
    policy_id TEXT,
    status TEXT DEFAULT 'Active',
    coverage_type TEXT,
    deductible REAL,
    "limit" REAL,
    created_at TEXT DEFAULT NOW()
);

-- ── New tables for the Adjuster persona ──────────────────────────────────

CREATE TABLE IF NOT EXISTS claim_triage (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    damage_severity TEXT,
    complexity TEXT,
    fraud_risk_score INTEGER,
    routing TEXT,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_flags (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    flag_type TEXT,
    flag_description TEXT,
    risk_score INTEGER,
    detected_by TEXT,
    status TEXT DEFAULT 'Active',
    flagged_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_fraud_signals (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    fraud_score INTEGER,
    indicator TEXT,
    value TEXT,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_risk_snapshots (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    fraud_score INTEGER,
    red_flag_count INTEGER DEFAULT 0,
    prior_claims TEXT DEFAULT 'Low',
    vendor_risk TEXT DEFAULT 'Low',
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS weather_location_alignment (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    storm_event TEXT,
    event_time TEXT,
    zip_code_severity_index TEXT,
    drone_weather_alignment TEXT,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drone_authenticity_data (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    drone_capture_time TEXT,
    roof_condition TEXT,
    weather_event_match TEXT,
    drone_match_percent INTEGER,
    geo_match TEXT,
    damage_inflation_index TEXT,
    tamper_indicator TEXT,
    drone_image_urls JSONB DEFAULT '[]'::jsonb,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drone_evidence_summary (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    drone_capture_time TEXT,
    roof_condition_rating TEXT,
    weather_event_alignment TEXT,
    damage_match_percent TEXT,
    manipulation_flags TEXT,
    drone_notes TEXT
);

CREATE TABLE IF NOT EXISTS authority_incident_logs (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    loss_type TEXT,
    authority_type TEXT,
    authority_reported_time TEXT,
    authority_reported_date TEXT,
    claimant_reported_time TEXT,
    time_discrepancy_minutes INTEGER,
    discrepancy_flag TEXT,
    authority_source TEXT,
    fraud_indicator TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS loss_type_verification_configs (
    id SERIAL PRIMARY KEY,
    loss_type TEXT UNIQUE,
    verification_mode TEXT,
    use_weather_api BOOLEAN DEFAULT FALSE,
    use_authority_check BOOLEAN DEFAULT FALSE,
    authority_type TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS damage_items (
    id SERIAL PRIMARY KEY,
    damage_id TEXT UNIQUE,
    claim_number TEXT,
    category TEXT,
    severity TEXT,
    estimated_cost REAL,
    adjuster_notes TEXT,
    created_date TEXT
);

CREATE TABLE IF NOT EXISTS condition_assessments (
    id SERIAL PRIMARY KEY,
    item_id TEXT,
    claim_id TEXT,
    structural_integrity_score REAL,
    age_years INTEGER,
    wear_level TEXT,
    remaining_useful_life_years INTEGER,
    safety_risk TEXT,
    environmental_impact TEXT,
    adjuster_notes TEXT,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS external_verifications (
    id SERIAL PRIMARY KEY,
    verification_id TEXT UNIQUE,
    claim_id TEXT,
    type TEXT,
    status TEXT,
    result TEXT,
    timestamp TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verification_details (
    id SERIAL PRIMARY KEY,
    verification_id TEXT,
    field TEXT,
    expected TEXT,
    actual TEXT,
    flag TEXT,
    severity TEXT DEFAULT 'Advisory',
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS loss_assessments (
    id SERIAL PRIMARY KEY,
    assessment_id TEXT UNIQUE,
    claim_number TEXT,
    total_parts_cost REAL,
    total_labor_cost REAL,
    depreciation_percent REAL,
    deductible REAL,
    subrogation_likelihood TEXT,
    system_recommendation TEXT,
    adjuster_override TEXT,
    final_recommendation TEXT,
    confidence_score REAL,
    notes TEXT,
    assessment_date TEXT
);

CREATE TABLE IF NOT EXISTS loss_estimation_outputs (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    ai_estimated_loss REAL DEFAULT 0,
    deductible REAL DEFAULT 0,
    net_payable REAL DEFAULT 0,
    repair_recommended TEXT DEFAULT 'Yes',
    confidence REAL DEFAULT 0,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS estimates (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    item_type TEXT,
    item_age INTEGER,
    useful_life_remaining INTEGER,
    repair_cost REAL,
    replacement_cost REAL,
    labor_cost REAL,
    material_cost REAL,
    recommendation TEXT,
    confidence_score REAL,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repair_costs (
    id SERIAL PRIMARY KEY,
    item_id TEXT,
    claim_id TEXT,
    item_type TEXT,
    material_cost REAL,
    labor_hours REAL,
    labor_rate REAL,
    diagnostic_fee REAL,
    urgency_factor REAL,
    total_repair_estimate REAL,
    notes TEXT,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS replacement_costs (
    id SERIAL PRIMARY KEY,
    item_id TEXT,
    claim_id TEXT,
    item_type TEXT,
    replacement_material_cost REAL,
    installation_hours REAL,
    labor_rate REAL,
    delivery_fee REAL,
    disposal_fee REAL,
    total_replacement_estimate REAL,
    notes TEXT,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payment_disbursements (
    id SERIAL PRIMARY KEY,
    payment_id TEXT UNIQUE,
    claim_id TEXT,
    claim_number TEXT,
    amount REAL,
    payment_method TEXT,
    status TEXT DEFAULT 'Pending',
    triggered_by TEXT,
    approved_by TEXT,
    triggered_at TEXT DEFAULT NOW(),
    completed_at TEXT
);

-- HITL approval gates + per-claim stage tracking, local copy of the tables
-- OrchestratorAgent/MCP/common/init_db.py also creates (same names, same
-- shared Postgres DB — idempotent either way, not a fork of the data). Lets
-- AdjusterOrchestrator open/check gates without OrchestratorAgent running.
CREATE TABLE IF NOT EXISTS claim_orchestration_state (
    id SERIAL PRIMARY KEY,
    claim_id TEXT UNIQUE,
    current_stage TEXT,
    status TEXT DEFAULT 'Open',
    last_action TEXT,
    updated_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS human_approval_requests (
    id SERIAL PRIMARY KEY,
    approval_id TEXT UNIQUE,
    claim_id TEXT,
    gate_type TEXT,
    status TEXT DEFAULT 'Pending',
    summary TEXT,
    requested_by TEXT,
    requested_at TEXT DEFAULT NOW(),
    decided_by TEXT,
    decided_at TEXT,
    decision_notes TEXT
);

CREATE TABLE IF NOT EXISTS adjuster_findings (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    adjuster_name TEXT,
    cause_of_loss TEXT,
    coverage_confirmed TEXT,
    fraud_risk TEXT,
    fraud_risk_score INTEGER DEFAULT 25,
    repair_vs_replace TEXT,
    adjusted_reserve REAL,
    recommended_vendor TEXT,
    final_settlement REAL,
    findings_date TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auto_adjudication_threshold_configs (
    id SERIAL PRIMARY KEY,
    config_id TEXT,
    max_loss_amount REAL,
    max_severity_level TEXT,
    max_complexity_level TEXT,
    max_fraud_score INTEGER DEFAULT 50
);

CREATE TABLE IF NOT EXISTS auto_assignment_log (
    id SERIAL PRIMARY KEY,
    assignment_id TEXT,
    claim_id TEXT,
    assigned_to TEXT,
    assignment_type TEXT,
    reason TEXT,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_items (
    id SERIAL PRIMARY KEY,
    evidence_id TEXT UNIQUE,
    claim_id TEXT,
    evidence_type TEXT,
    description TEXT,
    source TEXT,
    status TEXT DEFAULT 'Pending',
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cost_variance_output (
    id SERIAL PRIMARY KEY,
    vendor_id TEXT,
    avg_estimate REAL,
    avg_actual REAL,
    variance REAL,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_decision_recommendations (
    id SERIAL PRIMARY KEY,
    recommendation_id TEXT,
    claim_id TEXT,
    stp_score INTEGER DEFAULT 0,
    recommended_action TEXT,
    confidence REAL DEFAULT 0,
    generated_on TEXT DEFAULT NOW()
);

-- FinancialLeakageAgent's own persistence for score_leakage() — previously a
-- pure read-compute-return function with no DB write at all. One row per run
-- (kept like ai_decision_recommendations, not overwritten); adjuster_risk_override/
-- adjuster_notes are set later by the adjuster's own Save action, not by the agent.
CREATE TABLE IF NOT EXISTS financial_leakage_outputs (
    id SERIAL PRIMARY KEY,
    claim_id TEXT NOT NULL,
    total_estimated_cost NUMERIC,
    total_actual_cost NUMERIC,
    overall_variance_percent NUMERIC,
    leakage_score INTEGER,
    leakage_risk TEXT,
    risk_flags JSONB DEFAULT '[]'::jsonb,
    recommendation TEXT,
    adjuster_risk_override TEXT,
    adjuster_notes TEXT,
    generated_on TIMESTAMP DEFAULT NOW()
);

-- EvidenceValidationAgent's persisted claim-intake-completeness check (the
-- 7-mandatory-FNOL-field check, _check_claim_data_completeness). This is
-- deliberately the ADJUSTER-side re-check, distinct from PolicyholderAgents'
-- own intake_validation_result_output (populated at FNOL submission time,
-- before an adjuster is ever involved) — the two are not meant to be the
-- same signal. Previously computed fresh inside run_evidence_validation()'s
-- in-memory return every time and never saved anywhere, so nothing could
-- read it back later. One row per claim (ON CONFLICT (claim_id) DO UPDATE)
-- refreshed automatically every time evidence validation runs;
-- overridden/overridden_by/overridden_notes are set later by the adjuster's
-- own manual override action (case-investigation.tsx's "Complete Claim
-- Intake Validation" button), not by the agent, and are NOT cleared by a
-- later automatic refresh of the underlying check.
CREATE TABLE IF NOT EXISTS claim_intake_validation (
    id SERIAL PRIMARY KEY,
    claim_id TEXT UNIQUE NOT NULL,
    data_completeness_score NUMERIC NOT NULL DEFAULT 0,
    mandatory_fields_total INTEGER NOT NULL DEFAULT 0,
    mandatory_fields_filled INTEGER NOT NULL DEFAULT 0,
    validation_passed BOOLEAN NOT NULL DEFAULT FALSE,
    blocking_failure BOOLEAN NOT NULL DEFAULT FALSE,
    failure_reasons JSONB DEFAULT '[]'::jsonb,
    overridden BOOLEAN NOT NULL DEFAULT FALSE,
    overridden_by TEXT,
    overridden_notes TEXT,
    checked_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Adjuster's manual "Complete Investigation" sign-off (case-investigation.tsx
-- Adjuster Actions panel). One row per claim, created only once the button
-- is actually clicked — its presence IS the "completed" flag, gated
-- server-side (not just in the UI) on claim_intake_validation having
-- already passed/been overridden. Deliberately no override/notes columns
-- here unlike claim_intake_validation: this is a plain manual sign-off, not
-- a check that can fail and need justifying.
CREATE TABLE IF NOT EXISTS claim_investigation_completion (
    id SERIAL PRIMARY KEY,
    claim_id TEXT UNIQUE NOT NULL,
    completed_by TEXT,
    completed_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auto_adjudication_records (
    id SERIAL PRIMARY KEY,
    record_id TEXT UNIQUE,
    claim_id TEXT,
    eligible_for_auto_adjudication BOOLEAN,
    decision TEXT,
    stp_category TEXT,
    gates_passed INTEGER DEFAULT 0,
    gates_failed INTEGER DEFAULT 0,
    failed_gate_list TEXT,
    threshold_config_id TEXT,
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_trace_logs (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    gate_name TEXT,
    gate_result TEXT,
    value_evaluated TEXT,
    threshold_used TEXT,
    evaluated_at TIMESTAMP DEFAULT NOW()
);

-- ── STP (Straight-Through Processing) scoring tables ─────────────────────────

CREATE TABLE IF NOT EXISTS stp_score_input_factors (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    fnol_completeness REAL DEFAULT 0,
    readiness_score REAL DEFAULT 0,
    coverage_score REAL DEFAULT 0,
    severity_score REAL DEFAULT 0,
    fraud_ambiguity_score REAL DEFAULT 0,
    subrogation_risk_score REAL DEFAULT 0,
    vis REAL DEFAULT 50,
    similarity_index REAL DEFAULT 0.7,
    fraud_ambiguity TEXT DEFAULT 'Low',
    subrogation_risk TEXT DEFAULT 'Low',
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stp_calculation_result (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    weighted_score INTEGER,
    stp_category TEXT,
    fraud_ambiguity TEXT DEFAULT 'Low',
    subrogation_risk TEXT DEFAULT 'Low',
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS segmentation_result_output (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    severity TEXT,
    complexity TEXT,
    stp_score INTEGER,
    recommended_path TEXT,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS intake_validation_result_output (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    completeness_score INTEGER,
    coverage_status TEXT,
    fraud_risk TEXT DEFAULT 'Low',
    passed BOOLEAN,
    blocking_reason TEXT,
    validated_at TEXT DEFAULT NOW()
);
"""


def init_db():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(SCHEMA_SQL)

        # Column migrations — safely add columns that may be missing from tables
        # created by an earlier schema version (idempotent on PostgreSQL).
        _migrations = [
            "ALTER TABLE claims ADD COLUMN IF NOT EXISTS complexity TEXT",
            "ALTER TABLE claims ADD COLUMN IF NOT EXISTS ai_generated_summary TEXT",
            "ALTER TABLE claims ADD COLUMN IF NOT EXISTS detected_cause TEXT",
            "ALTER TABLE claims ADD COLUMN IF NOT EXISTS assigned_adjuster TEXT",
            "ALTER TABLE claims ADD COLUMN IF NOT EXISTS assigned_vendor TEXT",
            "ALTER TABLE auto_adjudication_threshold_configs ADD COLUMN IF NOT EXISTS max_fraud_score INTEGER DEFAULT 50",
            "ALTER TABLE adjuster_findings ADD COLUMN IF NOT EXISTS system_recommended_reserve REAL",
            # drone_authenticity_data column type migrations
            "ALTER TABLE drone_authenticity_data ALTER COLUMN drone_match_percent TYPE INTEGER USING drone_match_percent::integer",
            "ALTER TABLE drone_authenticity_data ALTER COLUMN drone_image_urls TYPE JSONB USING CASE WHEN drone_image_urls IS NULL THEN '[]'::jsonb ELSE drone_image_urls::jsonb END",
            # payment eligibility threshold: add min_stp_score column
            "ALTER TABLE auto_adjudication_threshold_configs ADD COLUMN IF NOT EXISTS min_stp_score INTEGER DEFAULT 50",
            # structural_integrity_score aligned with reference bundle: decimal fraction 0.50-0.90
            "ALTER TABLE condition_assessments ALTER COLUMN structural_integrity_score TYPE REAL USING structural_integrity_score::real",
            # verification_details severity tier: "Critical" (policy_exists, policy_status,
            # date_of_loss_in_policy_window) drives coverage_verdict; "Advisory" (default) never blocks.
            "ALTER TABLE verification_details ADD COLUMN IF NOT EXISTS severity TEXT DEFAULT 'Advisory'",
             # time_of_loss: claimant-reported time captured during FNOL
            "ALTER TABLE claims ADD COLUMN IF NOT EXISTS time_of_loss VARCHAR(10)",
        ]
        for _m in _migrations:
            cur.execute(_m)

        # Seed auto-adjudication threshold configs
        cur.execute("SELECT COUNT(*) FROM auto_adjudication_threshold_configs WHERE config_id = 'DEFAULT'")
        if cur.fetchone()["count"] == 0:
            cur.execute(
                """
                INSERT INTO auto_adjudication_threshold_configs (
                    config_id, max_loss_amount, max_severity_level, max_complexity_level, max_fraud_score
                ) VALUES ('DEFAULT', 10000, 'Medium', 'Moderate', 50)
                """
            )

        cur.execute("SELECT COUNT(*) FROM auto_adjudication_threshold_configs WHERE config_id = 'HIGH_VALUE'")
        if cur.fetchone()["count"] == 0:
            cur.execute(
                """
                INSERT INTO auto_adjudication_threshold_configs (
                    config_id, max_loss_amount, max_severity_level, max_complexity_level, max_fraud_score
                ) VALUES ('HIGH_VALUE', 25000, 'High', 'Moderate', 70)
                """
            )

        # Seed loss_type_verification_configs (DB-driven routing — no hardcoding in handler)
        _loss_type_seeds = [
            ("Water Damage", "weather",   True,  False, None,              "Full Open-Meteo weather verification"),
            ("Flood",        "weather",   True,  False, None,              "Full Open-Meteo weather verification"),
            ("Storm",        "weather",   True,  False, None,              "Full Open-Meteo weather verification"),
            ("Hail",         "weather",   True,  False, None,              "Full Open-Meteo weather verification"),
            ("Wind",         "weather",   True,  False, None,              "Full Open-Meteo weather verification"),
            ("Lightning",    "weather",   True,  False, None,              "Full Open-Meteo weather verification"),
            ("Snow",         "weather",   True,  False, None,              "Full Open-Meteo weather verification"),
            ("Ice",          "weather",   True,  False, None,              "Full Open-Meteo weather verification"),
            ("Fire",         "authority", False, True,  "fire_department", "Authority time check via fire department"),
            ("Fire Damage",  "authority", False, True,  "fire_department", "Authority time check via fire department"),
            ("Theft",        "authority", False, True,  "police",          "Authority time check via police report"),
            ("Auto",         "authority", False, True,  "police",          "Authority time check via police report"),
            ("Structural",   "physical",  False, False, None,              "Physical inspection only — no external API"),
            ("Unknown",      "generic",   False, False, None,              "Generic checks — loss type unclassified"),
        ]
        for (lt, mode, use_wx, use_auth, auth_type, desc) in _loss_type_seeds:
            cur.execute(
                "SELECT COUNT(*) FROM loss_type_verification_configs WHERE LOWER(loss_type) = LOWER(%s)",
                (lt,),
            )
            if cur.fetchone()["count"] == 0:
                cur.execute(
                    """
                    INSERT INTO loss_type_verification_configs
                        (loss_type, verification_mode, use_weather_api, use_authority_check, authority_type, description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (lt, mode, use_wx, use_auth, auth_type, desc),
                )


        # Seed adjuster_findings for the sample claim CLM-2026-1001
        cur.execute("SELECT COUNT(*) FROM adjuster_findings WHERE claim_id = 'CLM-2026-1001'")
        if cur.fetchone()["count"] == 0:
            cur.execute("SELECT loss_type FROM claims WHERE claim_number = 'CLM-2026-1001'")
            row = cur.fetchone()
            cause_of_loss = row["loss_type"] if row else "Water Damage"
            cur.execute(
                """
                INSERT INTO adjuster_findings (
                    claim_id, adjuster_name, cause_of_loss, coverage_confirmed,
                    fraud_risk, fraud_risk_score, repair_vs_replace, adjusted_reserve
                ) VALUES (
                    'CLM-2026-1001', 'Auto-Seed', %s, 'Yes', 'Low', 10, 'TBD', 5000
                )
                """,
                (cause_of_loss,),
            )

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized (shared) at:", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
        "PolicyholderAgents", "data", "policyholder.db"
    ))
