"""
init_db.py
──────────
Creates all PostgreSQL tables needed by the Orchestrator (Brain) Agent in the
Azure PostgreSQL claims database and seeds
reference/sample data. Safe to re-run (idempotent). Uses
CREATE TABLE IF NOT EXISTS everywhere so it never clobbers tables already
created by the other personas' init_db scripts, and is safe to run
before or after those (though it should be run LAST since it depends on
the `claims` table existing for the seed row's claim_id reference).

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
-- script is safe to run on a fresh db too).
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

-- ── New tables for the Orchestrator (Brain) Agent ──────────────────────────

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

        # Seed claim_orchestration_state for CLM-2026-1001
        cur.execute("SELECT COUNT(*) FROM claim_orchestration_state WHERE claim_id = 'CLM-2026-1001'")
        if cur.fetchone()["count"] == 0:
            cur.execute(
                """
                INSERT INTO claim_orchestration_state (claim_id, current_stage, status, last_action)
                VALUES ('CLM-2026-1001', 'Open', 'Open', 'Seeded initial orchestration state')
                """
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
