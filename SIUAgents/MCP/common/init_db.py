"""
init_db.py
──────────
Creates all PostgreSQL tables needed by the SIU Agents platform in the
Azure PostgreSQL claims database and seeds
reference/sample data. Safe to re-run (idempotent). Uses
CREATE TABLE IF NOT EXISTS everywhere so it never clobbers tables already
created by PolicyholderAgents' or AdjusterAgents' init_db, and is safe to
run before or after those.

Run:
    py -3 MCP/common/init_db.py  (against Azure PostgreSQL)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import get_db_connection  # noqa: E402

SCHEMA_SQL = """
-- Minimal re-declaration of shared tables (already created by
-- PolicyholderAgents'/AdjusterAgents' init_db, but declared here
-- defensively so this script is safe to run first on a fresh db).
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

-- ── Re-declared shared fraud tables (created by AdjusterAgents) ──────────

CREATE TABLE IF NOT EXISTS fraud_risk_snapshots (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    fraud_score INTEGER,
    red_flag_count INTEGER DEFAULT 0,
    prior_claims TEXT DEFAULT 'Low',
    vendor_risk TEXT DEFAULT 'Low',
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_fraud_signals (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    fraud_score INTEGER,
    indicator TEXT,
    value TEXT,
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

CREATE TABLE IF NOT EXISTS investigation_notes (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    notes TEXT,
    risk_flag TEXT
);

-- ── New tables for the SIU persona ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS siu_escalation_records (
    id SERIAL PRIMARY KEY,
    siu_id TEXT UNIQUE,
    claim_id TEXT,
    escalation_reason TEXT,
    fraud_score INTEGER,
    evidence_notes TEXT,
    escalated_by TEXT,
    status TEXT DEFAULT 'Under Review',
    escalation_date TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS siu_case_master (
    id SERIAL PRIMARY KEY,
    siu_case_id TEXT,
    claim_id TEXT,
    status TEXT,
    assigned_investigator TEXT,
    created_date TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS siu_claim_master (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    stage TEXT,
    status TEXT,
    policy_id TEXT,
    loss_type TEXT,
    fnol_complete TEXT DEFAULT 'Yes',
    fraud_flag INTEGER DEFAULT 0,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS siu_decision (
    id SERIAL PRIMARY KEY,
    siu_case_id TEXT,
    claim_id TEXT,
    decision TEXT,
    confidence REAL,
    closed_date TEXT,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS siu_timeline_events (
    id SERIAL PRIMARY KEY,
    event_id TEXT,
    siu_case_id TEXT,
    claim_id TEXT,
    event_type TEXT,
    status TEXT,
    timestamp TEXT
);

CREATE TABLE IF NOT EXISTS siu_activity_log (
    id SERIAL PRIMARY KEY,
    activity_id TEXT,
    siu_case_id TEXT,
    claim_id TEXT,
    activity TEXT,
    status TEXT,
    owner TEXT,
    timestamp TEXT
);

CREATE TABLE IF NOT EXISTS siu_progress_tracker (
    id SERIAL PRIMARY KEY,
    siu_case_id TEXT,
    claim_id TEXT,
    stage TEXT,
    progress_percent REAL,
    estimated_duration TEXT,
    days_elapsed INTEGER
);

CREATE TABLE IF NOT EXISTS fraud_network_graph (
    id SERIAL PRIMARY KEY,
    entity_id TEXT,
    related_claim TEXT,
    relationship_type TEXT,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vendor_red_flags (
    id SERIAL PRIMARY KEY,
    vendor_id TEXT,
    alert_type TEXT,
    severity TEXT,
    title TEXT,
    explanation TEXT,
    triggering_logic TEXT,
    related_claim_ids TEXT,
    is_reviewed INTEGER DEFAULT 0,
    is_escalated INTEGER DEFAULT 0,
    reviewed_by TEXT,
    reviewed_at TEXT,
    escalated_at TEXT,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vendor_network_signals (
    id SERIAL PRIMARY KEY,
    vendor_id TEXT,
    signal_type TEXT,
    related_entity TEXT,
    related_entity_type TEXT,
    occurrence_count INTEGER DEFAULT 1,
    first_occurrence TEXT,
    last_occurrence TEXT,
    risk_narrative TEXT,
    severity TEXT DEFAULT 'Low',
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_risk_flags_output (
    id SERIAL PRIMARY KEY,
    vendor_id TEXT,
    risk_flag TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS legal_escalations (
    id SERIAL PRIMARY KEY,
    escalation_id TEXT UNIQUE,
    siu_case_id TEXT,
    claim_id TEXT,
    reason TEXT,
    fraud_score INTEGER,
    status TEXT DEFAULT 'Pending Review',
    referred_by TEXT,
    referred_at TEXT DEFAULT NOW(),
    outcome TEXT
);

CREATE TABLE IF NOT EXISTS fraud_watchlist (
    id SERIAL PRIMARY KEY,
    watchlist_id TEXT UNIQUE,
    entity_type TEXT,
    entity_id TEXT,
    entity_name TEXT,
    reason TEXT,
    severity TEXT,
    added_by TEXT,
    status TEXT DEFAULT 'Active',
    added_at TEXT DEFAULT NOW()
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
        ]
        for _m in _migrations:
            cur.execute(_m)

        # Seed siu_case_master for CLM-2026-1001
        cur.execute("SELECT COUNT(*) FROM siu_case_master WHERE claim_id = 'CLM-2026-1001'")
        if cur.fetchone()["count"] == 0:
            cur.execute(
                """
                INSERT INTO siu_case_master (siu_case_id, claim_id, status, assigned_investigator)
                VALUES ('SIU-2026-0001', 'CLM-2026-1001', 'Open', 'Unassigned')
                """
            )

        # Seed siu_claim_master for CLM-2026-1001
        cur.execute("SELECT COUNT(*) FROM siu_claim_master WHERE claim_id = 'CLM-2026-1001'")
        if cur.fetchone()["count"] == 0:
            cur.execute("SELECT loss_type FROM claims WHERE claim_number = 'CLM-2026-1001'")
            row = cur.fetchone()
            loss_type = row["loss_type"] if row else "Water Damage"
            cur.execute(
                """
                INSERT INTO siu_claim_master (claim_id, stage, status, policy_id, loss_type, fnol_complete, fraud_flag)
                VALUES ('CLM-2026-1001', 'Investigation', 'Open', 'POL-1001', %s, 'Yes', 0)
                """,
                (loss_type,),
            )

        # Seed siu_progress_tracker
        cur.execute("SELECT COUNT(*) FROM siu_progress_tracker WHERE siu_case_id = 'SIU-2026-0001'")
        if cur.fetchone()["count"] == 0:
            cur.execute(
                """
                INSERT INTO siu_progress_tracker (siu_case_id, claim_id, stage, progress_percent, estimated_duration, days_elapsed)
                VALUES ('SIU-2026-0001', 'CLM-2026-1001', 'Initial Review', 10.0, '5-7 days', 1)
                """
            )

        # Seed investigation_notes
        cur.execute("SELECT COUNT(*) FROM investigation_notes WHERE claim_id = 'CLM-2026-1001'")
        if cur.fetchone()["count"] == 0:
            cur.executemany(
                "INSERT INTO investigation_notes (claim_id, notes, risk_flag) VALUES (%s,%s,%s)",
                [
                    ("CLM-2026-1001", "Initial review: claim documentation appears consistent with reported loss.", "Low"),
                    ("CLM-2026-1001", "Vendor estimate slightly above regional average; recommend cost comparison.", "Medium"),
                ],
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
