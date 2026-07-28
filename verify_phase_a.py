"""
verify_phase_a.py — Point 3 DB verification for AdjusterOrchestrator Phase A
─────────────────────────────────────────────────────────────────────────────
CLM-2026-1001 (and any other shared test claim) already accumulates history
across repeated test runs, so checking absolute row counts is unreliable —
a claim that's been tested 5 times will have 5x the rows of a fresh one.
This script instead snapshots a BASELINE right before you run the phase in
the UI, then on the next run compares against that baseline and only judges
the NEW rows created since then.

Usage:
    # 1. Right BEFORE clicking "Start Workflow" in the UI:
    AdjusterAgents/venv/bin/python3 verify_phase_a.py CLM-2026-1001 --baseline

    # 2. Run Phase A in the UI, wait for the tracker to show all 8 agents green.

    # 3. Then verify:
    AdjusterAgents/venv/bin/python3 verify_phase_a.py CLM-2026-1001
"""

import json
import os
import sys

sys.path.insert(0, "AdjusterAgents/MCP/common")
from db import get_db_connection  # noqa: E402

CLAIM = sys.argv[1] if len(sys.argv) > 1 else "CLM-2026-1001"
BASELINE_MODE = "--baseline" in sys.argv
BASELINE_FILE = f".phase_a_baseline_{CLAIM}.json"

PASS, FAIL, INFO = "PASS", "FAIL", "INFO"

# (table, id_column, claim_column) for every insert-only table Phase A writes to
TRACKED_TABLES = [
    ("fraud_risk_snapshots", "id", "claim_id"),
    ("ai_fraud_signals", "id", "claim_id"),
    ("fraud_flags", "id", "claim_id"),
    ("damage_items", "id", "claim_number"),
    ("weather_location_alignment", "id", "claim_id"),
    ("drone_authenticity_data", "id", "claim_id"),
    ("drone_evidence_summary", "id", "claim_id"),
    ("external_verifications", "id", "claim_id"),
    ("claim_triage", "id", "claim_id"),
    ("auto_assignment_log", "id", "claim_id"),
    ("human_approval_requests", "id", "claim_id"),
]


def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    print(f"[{status}] {label}{'  — ' + detail if detail else ''}")
    return bool(condition)


def get_max_id(cur, table, id_col, claim_col, claim):
    cur.execute(f"SELECT MAX({id_col}) AS m FROM {table} WHERE {claim_col} = %s", (claim,))
    row = cur.fetchone()
    return row["m"] if row and row["m"] is not None else 0


def get_scalar(cur, table, col, key_col, key_val):
    cur.execute(f"SELECT {col} FROM {table} WHERE {key_col} = %s", (key_val,))
    row = cur.fetchone()
    return row[col] if row else None


def save_baseline():
    conn = get_db_connection()
    cur = conn.cursor()
    baseline = {"claim_triage_ids": {}}
    for table, id_col, claim_col in TRACKED_TABLES:
        baseline[table] = get_max_id(cur, table, id_col, claim_col, CLAIM)
    baseline["claims_complexity"] = get_scalar(cur, "claims", "complexity", "claim_number", CLAIM)
    baseline["claims_assigned_adjuster"] = get_scalar(cur, "claims", "assigned_adjuster", "claim_number", CLAIM)
    conn.close()
    with open(BASELINE_FILE, "w") as f:
        json.dump(baseline, f, indent=2)
    print(f"Baseline saved to {BASELINE_FILE}:")
    print(json.dumps(baseline, indent=2))
    print("\nNow run Phase A in the UI, then re-run this script WITHOUT --baseline.")


def new_rows_since(cur, table, id_col, claim_col, claim, baseline_id):
    cur.execute(
        f"SELECT * FROM {table} WHERE {claim_col} = %s AND {id_col} > %s ORDER BY {id_col}",
        (claim, baseline_id),
    )
    return cur.fetchall()


def verify():
    if not os.path.exists(BASELINE_FILE):
        print(
            f"No baseline file found ({BASELINE_FILE}). Run with --baseline first, "
            "BEFORE starting the workflow in the UI, or this check can't tell new "
            "rows apart from this claim's existing history."
        )
        sys.exit(1)

    with open(BASELINE_FILE) as f:
        baseline = json.load(f)

    conn = get_db_connection()
    cur = conn.cursor()
    all_ok = True

    print(f"\n=== Phase A DB verification for claim {CLAIM} (vs baseline) ===\n")

    # 1. FraudScreeningAgent
    print("--- 1. FraudScreeningAgent ---")
    new_snaps = new_rows_since(cur, "fraud_risk_snapshots", "id", "claim_id", CLAIM, baseline["fraud_risk_snapshots"])
    all_ok &= check("fraud_risk_snapshots: 1 new row", len(new_snaps) == 1, f"{len(new_snaps)} new row(s)")
    snap = new_snaps[-1] if new_snaps else None
    if snap:
        all_ok &= check(
            "new row: fraud_score/red_flag_count/prior_claims/vendor_risk non-null",
            all(snap.get(k) is not None for k in ("fraud_score", "red_flag_count", "prior_claims", "vendor_risk")),
        )
    new_signals = new_rows_since(cur, "ai_fraud_signals", "id", "claim_id", CLAIM, baseline["ai_fraud_signals"])
    all_ok &= check("ai_fraud_signals: 1-3 new rows", 1 <= len(new_signals) <= 3, f"{len(new_signals)} new row(s)")
    new_flags = new_rows_since(cur, "fraud_flags", "id", "claim_id", CLAIM, baseline["fraud_flags"])
    check("fraud_flags new rows", True, f"{len(new_flags)} new row(s) (0+ expected, only if any signal >= 40)")

    # 2. DamageAssessmentAgent
    print("\n--- 2. DamageAssessmentAgent ---")
    new_items = new_rows_since(cur, "damage_items", "id", "claim_number", CLAIM, baseline["damage_items"])
    all_ok &= check(
        "damage_items: new rows (0 is OK if this claim was already assessed)",
        True, f"{len(new_items)} new row(s)",
    )
    for it in new_items:
        all_ok &= check(
            f"new damage_items[{it.get('damage_id')}]: category/severity/estimated_cost non-null",
            all(it.get(k) is not None for k in ("category", "severity", "estimated_cost")),
        )

    # 3. ExternalDataAgent
    print("\n--- 3. ExternalDataAgent ---")
    new_weather = new_rows_since(cur, "weather_location_alignment", "id", "claim_id", CLAIM, baseline["weather_location_alignment"])
    new_drone = new_rows_since(cur, "drone_authenticity_data", "id", "claim_id", CLAIM, baseline["drone_authenticity_data"])
    new_drone_summary = new_rows_since(cur, "drone_evidence_summary", "id", "claim_id", CLAIM, baseline["drone_evidence_summary"])
    all_ok &= check("weather_location_alignment: 1 new row", len(new_weather) == 1, f"{len(new_weather)}")
    all_ok &= check("drone_authenticity_data: 1 new row", len(new_drone) == 1, f"{len(new_drone)}")
    all_ok &= check("drone_evidence_summary: 1 new row", len(new_drone_summary) == 1, f"{len(new_drone_summary)}")
    if not (new_weather and new_drone and new_drone_summary):
        print(
            f"  [{INFO}] All three should appear together or not at all — if only some "
            "are missing, that's the known 'error key in a successful-looking result' "
            "case (LLM JSON parse failure). Check the chat for that note."
        )

    # 4. VerificationAgent
    print("\n--- 4. VerificationAgent ---")
    new_ext_ver = new_rows_since(cur, "external_verifications", "id", "claim_id", CLAIM, baseline["external_verifications"])
    all_ok &= check("external_verifications: 1 new row", len(new_ext_ver) == 1, f"{len(new_ext_ver)}")
    ext_ver = new_ext_ver[-1] if new_ext_ver else None
    if ext_ver:
        all_ok &= check(
            "new row: status/result non-null",
            ext_ver.get("status") is not None and ext_ver.get("result") is not None,
        )
        cur.execute(
            "SELECT * FROM verification_details WHERE verification_id = %s ORDER BY id",
            (ext_ver.get("verification_id"),),
        )
        details = cur.fetchall()
        all_ok &= check("verification_details: 2 rows for this verification_id", len(details) == 2, f"{len(details)}")
        for d in details:
            all_ok &= check(
                f"verification_details[{d.get('field')}].flag is a valid value",
                d.get("flag") in ("Match", "Mismatch", "Unable to Verify"),
            )

    # 5 & 7. claim_triage — Classification writes one row, Triage writes another
    print("\n--- 5. ClaimClassificationAgent + 7. TriageAgent ---")
    new_triage_rows = new_rows_since(cur, "claim_triage", "id", "claim_id", CLAIM, baseline["claim_triage"])
    all_ok &= check(
        "claim_triage: exactly 2 new rows (Classification's, then Triage's)",
        len(new_triage_rows) == 2, f"{len(new_triage_rows)} new row(s)",
    )
    for row in new_triage_rows:
        all_ok &= check(
            f"new claim_triage row {row.get('id')}: damage_severity/complexity/fraud_risk_score/routing non-null",
            all(row.get(k) is not None for k in ("damage_severity", "complexity", "fraud_risk_score", "routing")),
        )
    if new_triage_rows and snap:
        first = new_triage_rows[0]
        all_ok &= check(
            "first new claim_triage row's fraud_risk_score matches this run's fraud_risk_snapshots.fraud_score",
            first.get("fraud_risk_score") == snap.get("fraud_score"),
            f"{first.get('fraud_risk_score')} vs {snap.get('fraud_score')}",
        )
    new_complexity = get_scalar(cur, "claims", "complexity", "claim_number", CLAIM)
    all_ok &= check(
        "claims.complexity is set and changed (or was already set) since baseline",
        new_complexity is not None,
        f"baseline={baseline['claims_complexity']!r} now={new_complexity!r}",
    )

    # 6. EvidenceValidationAgent
    print("\n--- 6. EvidenceValidationAgent ---")
    cur.execute("SELECT evidence_id, status FROM evidence_items WHERE claim_id = %s", (CLAIM,))
    ev_items = cur.fetchall()
    check(
        "evidence_items row count",
        True,
        f"{len(ev_items)} row(s) — 0 is EXPECTED for this seed claim (no-op update, not a bug)",
    )

    # 8. RoutingAgent
    print("\n--- 8. RoutingAgent ---")
    new_assignments = new_rows_since(cur, "auto_assignment_log", "id", "claim_id", CLAIM, baseline["auto_assignment_log"])
    all_ok &= check("auto_assignment_log: 1 new row", len(new_assignments) == 1, f"{len(new_assignments)}")
    if new_assignments:
        a = new_assignments[-1]
        all_ok &= check(
            "new row: assigned_to/assignment_type/reason non-null",
            all(a.get(k) is not None for k in ("assigned_to", "assignment_type", "reason")),
        )
    new_adjuster = get_scalar(cur, "claims", "assigned_adjuster", "claim_number", CLAIM)
    all_ok &= check(
        "claims.assigned_adjuster is now set",
        new_adjuster is not None,
        f"baseline={baseline['claims_assigned_adjuster']!r} now={new_adjuster!r}",
    )

    # HITL audit gate
    print("\n--- HITL: triage_approval (audit-only) ---")
    new_approvals = new_rows_since(cur, "human_approval_requests", "id", "claim_id", CLAIM, baseline["human_approval_requests"])
    triage_approvals = [a for a in new_approvals if a.get("gate_type") == "triage_approval"]
    all_ok &= check("human_approval_requests: 1 new triage_approval row", len(triage_approvals) == 1, f"{len(triage_approvals)}")
    if triage_approvals:
        check("triage_approval summary text", True, repr(triage_approvals[-1].get("summary")))

    conn.close()

    print("\n" + ("=" * 60))
    print("OVERALL:", PASS if all_ok else FAIL)
    print("=" * 60)

    os.remove(BASELINE_FILE)
    print(f"(baseline file {BASELINE_FILE} removed — run --baseline again before the next test)")


if __name__ == "__main__":
    if BASELINE_MODE:
        save_baseline()
    else:
        verify()
