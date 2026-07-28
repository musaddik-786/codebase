"""
init_db.py
──────────
Creates all PostgreSQL tables needed by the Vendor Manager Agents platform in
the Azure PostgreSQL claims database and seeds
reference/sample data. Safe to re-run (idempotent). Uses
CREATE TABLE IF NOT EXISTS everywhere so it never clobbers tables already
created by PolicyholderAgents'/AdjusterAgents'/SIUAgents' init_db, and is
safe to run before or after those.

Run:
    py -3 MCP/common/init_db.py  (against Azure PostgreSQL)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import get_db_connection  # noqa: E402

SCHEMA_SQL = """
-- Minimal re-declaration of shared tables (already created by
-- PolicyholderAgents'/AdjusterAgents'/SIUAgents' init_db, but declared here
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

-- ── New tables for the Vendor Manager persona ─────────────────────────────

CREATE TABLE IF NOT EXISTS vendors (
    id SERIAL PRIMARY KEY,
    name TEXT,
    specialty TEXT,
    license_number TEXT,
    license_valid INTEGER DEFAULT 1,
    rating REAL,
    completed_jobs INTEGER DEFAULT 0,
    avg_turnaround_days REAL,
    avg_cost REAL,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    phone TEXT,
    verified INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS vendor_master_input (
    id SERIAL PRIMARY KEY,
    vendor_id TEXT,
    name TEXT,
    specialty TEXT,
    location TEXT,
    status TEXT,
    assignment_eligible TEXT DEFAULT 'Yes',
    license_number TEXT,
    license_expiry_date TEXT,
    deactivation_reason TEXT,
    deactivation_mode TEXT,
    deactivated_at TEXT,
    vis_score INTEGER
);

CREATE TABLE IF NOT EXISTS vendor_benchmarks (
    id SERIAL PRIMARY KEY,
    vendor_id TEXT UNIQUE,
    vendor_name TEXT,
    specialty TEXT,
    avg_repair_cost REAL,
    avg_replacement_cost REAL,
    eta_days REAL,
    quality_rating REAL,
    license_valid INTEGER DEFAULT 1,
    fraud_score REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS vendor_jobs_input (
    id SERIAL PRIMARY KEY,
    vendor_id TEXT,
    claim_id TEXT,
    assigned_date TEXT,
    completion_date TEXT,
    status TEXT,
    action TEXT,
    sla_status TEXT,
    active TEXT DEFAULT 'Yes'
);

CREATE TABLE IF NOT EXISTS vendor_applications (
    id SERIAL PRIMARY KEY,
    name TEXT,
    specialty TEXT,
    location TEXT,
    license_number TEXT,
    license_expiry_date TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    status TEXT DEFAULT 'Pending',
    submitted_date TEXT,
    rejection_reason TEXT
);

CREATE TABLE IF NOT EXISTS vendor_assignment (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    vendor_id TEXT,
    vendor_type TEXT,
    assignment_status TEXT,
    sla_status TEXT
);

CREATE TABLE IF NOT EXISTS vendor_cost_input (
    id SERIAL PRIMARY KEY,
    vendor_id TEXT,
    claim_id TEXT,
    estimated_cost REAL,
    actual_cost REAL
);

CREATE TABLE IF NOT EXISTS cost_variance_output (
    id SERIAL PRIMARY KEY,
    vendor_id TEXT UNIQUE,
    avg_estimate REAL,
    avg_actual REAL,
    variance REAL
);

CREATE TABLE IF NOT EXISTS vendor_rating_input (
    id SERIAL PRIMARY KEY,
    vendor_id TEXT,
    rating REAL,
    feedback TEXT
);

CREATE TABLE IF NOT EXISTS vendor_performance_score_output (
    id SERIAL PRIMARY KEY,
    vendor_id TEXT UNIQUE,
    vis REAL,
    sla_score REAL,
    cost_efficiency REAL,
    quality REAL
);

CREATE TABLE IF NOT EXISTS sla_tracker_output (
    id SERIAL PRIMARY KEY,
    vendor_id TEXT UNIQUE,
    avg_response_time TEXT,
    avg_completion_time TEXT,
    sla_compliance REAL
);

CREATE TABLE IF NOT EXISTS escalation_log_output (
    id SERIAL PRIMARY KEY,
    escalation_id TEXT UNIQUE,
    claim_id TEXT,
    vendor_id TEXT,
    severity TEXT,
    message TEXT,
    created_by TEXT,
    date TEXT
);

CREATE TABLE IF NOT EXISTS job_status_update_output (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    escalation_flag TEXT,
    priority TEXT
);

CREATE TABLE IF NOT EXISTS work_orders (
    id SERIAL PRIMARY KEY,
    work_order_id TEXT UNIQUE,
    claim_id TEXT,
    claim_number TEXT,
    expert_id TEXT,
    expert_name TEXT,
    expert_type TEXT,
    scheduled_date TEXT,
    scheduled_time TEXT,
    estimated_arrival TEXT,
    travel_time_minutes INTEGER,
    equipment_needed TEXT,
    safety_level TEXT DEFAULT 'Low',
    permit_required INTEGER DEFAULT 0,
    drone_required INTEGER DEFAULT 0,
    drone_dispatch_id TEXT,
    estimated_cost REAL,
    actual_cost REAL,
    status TEXT DEFAULT 'Scheduled',
    priority TEXT DEFAULT 'Normal',
    notes_to_expert TEXT,
    customer_address TEXT,
    customer_phone TEXT,
    customer_email TEXT,
    assigned_by TEXT,
    started_at TEXT,
    completed_at TEXT,
    canceled_at TEXT,
    cancel_reason TEXT,
    created_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dispatch_logs (
    id SERIAL PRIMARY KEY,
    log_id TEXT UNIQUE,
    work_order_id TEXT,
    claim_id TEXT,
    action TEXT,
    action_by TEXT,
    details TEXT,
    previous_status TEXT,
    new_status TEXT,
    timestamp TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS eta_predictions (
    id SERIAL PRIMARY KEY,
    claim_id TEXT,
    vendor_id TEXT,
    predicted_eta_days REAL,
    confidence REAL,
    factors TEXT,
    predicted_at TEXT DEFAULT NOW()
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

        # Seed vendors
        cur.execute("SELECT COUNT(*) FROM vendors")
        if cur.fetchone()["count"] == 0:
            cur.executemany(
                """
                INSERT INTO vendors (name, specialty, license_number, license_valid, rating,
                                      completed_jobs, avg_turnaround_days, avg_cost, city, state,
                                      zip_code, phone, verified)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                [
                    ("Springfield Plumbing Pros", "Plumbing", "LIC-PL-1001", True, 4.6, 124, 3, 850.0, "Springfield", "IL", "62701", "217-555-0101", True),
                    ("Apex Roofing Co", "Roofing", "LIC-RF-2002", True, 4.5, 98, 6, 4200.0, "Springfield", "IL", "62702", "217-555-0102", True),
                    ("Precision Auto Body", "Auto Body", "LIC-AB-3003", True, 4.7, 210, 5, 2100.0, "Chicago", "IL", "60601", "312-555-0103", True),
                    ("Reliable Electric Services", "Electrical", "LIC-EL-4004", True, 4.4, 76, 2, 650.0, "Springfield", "IL", "62703", "217-555-0104", True),
                    ("Midwest General Contractors", "Contractor", "LIC-GC-5005", True, 4.3, 142, 8, 5800.0, "Chicago", "IL", "60602", "312-555-0105", True),
                ],
            )
            conn.commit()

        # Seed vendor_master_input (one per vendor)
        cur.execute("SELECT COUNT(*) FROM vendor_master_input")
        if cur.fetchone()["count"] == 0:
            cur.execute("SELECT id, name, specialty, city, license_number FROM vendors")
            for row in cur.fetchall():
                vendor_id = f"VEN-00{row['id']}"
                cur.execute(
                    """
                    INSERT INTO vendor_master_input (vendor_id, name, specialty, location, status,
                                                       assignment_eligible, license_number,
                                                       license_expiry_date, vis_score)
                    VALUES (%s,%s,%s,%s, 'Active', 'Yes', %s, '2027-12-31', 80)
                    """,
                    (vendor_id, row["name"], row["specialty"], row["city"], row["license_number"]),
                )
            conn.commit()

        # Seed vendor_benchmarks (for first two vendors)
        cur.execute("SELECT COUNT(*) FROM vendor_benchmarks")
        if cur.fetchone()["count"] == 0:
            cur.executemany(
                """
                INSERT INTO vendor_benchmarks (vendor_id, vendor_name, specialty, avg_repair_cost,
                                                 avg_replacement_cost, eta_days, quality_rating,
                                                 license_valid, fraud_score, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                [
                    ("VEN-001", "Springfield Plumbing Pros", "Plumbing", 800.0, 2500.0, 3, 4.6, True, 0.05, "Consistent quality, on-time."),
                    ("VEN-002", "Apex Roofing Co", "Roofing", 4000.0, 12000.0, 6, 4.5, True, 0.04, "Slightly above market on materials cost."),
                ],
            )
            conn.commit()

        # Seed vendor_jobs_input referencing CLM-2026-1001
        cur.execute("SELECT COUNT(*) FROM vendor_jobs_input WHERE claim_id = 'CLM-2026-1001'")
        if cur.fetchone()["count"] == 0:
            cur.executemany(
                """
                INSERT INTO vendor_jobs_input (vendor_id, claim_id, assigned_date, completion_date,
                                                 status, action, sla_status, active)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                [
                    ("VEN-001", "CLM-2026-1001", "2026-05-01", "2026-05-04", "Completed", "Repair", "On Track", "Yes"),
                    ("VEN-002", "CLM-2026-1001", "2026-05-05", None, "In Progress", "Inspection", "On Track", "Yes"),
                ],
            )
            conn.commit()

        # Seed a pending vendor application
        cur.execute("SELECT COUNT(*) FROM vendor_applications")
        if cur.fetchone()["count"] == 0:
            cur.execute(
                """
                INSERT INTO vendor_applications (name, specialty, location, license_number,
                                                   license_expiry_date, contact_email, contact_phone,
                                                   status, submitted_date)
                VALUES ('Hometown Water Mitigation', 'Water Mitigation', 'Springfield, IL', 'LIC-WM-6006',
                        '2027-06-30', 'contact@hometownwater.example', '217-555-0199', 'Pending', '2026-06-10')
                """
            )
            conn.commit()

        # Seed vendor_assignment for CLM-2026-1001
        cur.execute("SELECT COUNT(*) FROM vendor_assignment WHERE claim_id = 'CLM-2026-1001'")
        if cur.fetchone()["count"] == 0:
            cur.execute(
                """
                INSERT INTO vendor_assignment (claim_id, vendor_id, vendor_type, assignment_status, sla_status)
                VALUES ('CLM-2026-1001', 'VEN-001', 'Plumbing', 'Assigned', 'On Track')
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
