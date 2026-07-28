"""
seed_test_claims.py
────────────────────
Inserts 3 fresh test claims designed to exercise all 15 AdjusterAgents
through the Adjuster Orchestrator end-to-end.

Claims:
  CLM-2026-7001  Margaret Chen     Storm Damage  Medium  $9,500
  CLM-2026-7002  Robert Garcia     Water Damage  High    $14,750
  CLM-2026-7003  Patricia Williams Fire          High    $22,000

Each claim has:
  - claims row: all mandatory fields (policy_number, loss_type,
      short_description, severity, estimated_cost, location, date_of_loss)
  - policy_details row: matched to the claim's policy_number
  - evidence_items: matching required evidence types for the loss_type
  - adjuster_findings: coverage_confirmed = 'Yes' (needed for
      PaymentEligibilityAgent and PaymentTriggerAgent)

Safe to re-run: skips any claim/policy that already exists.

Run:
    python seed_test_claims.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "AdjusterAgents", "MCP", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

# ── Claim definitions ─────────────────────────────────────────────────────────

CLAIMS = [
    {
        "claim_number":       "CLM-2026-7001",
        "policyholder_name":  "Margaret Chen",
        "policy_number":      "POL-7001",
        "loss_type":          "Storm",
        "short_description":  (
            "Severe thunderstorm with 60 mph winds tore off sections of the "
            "roof and shattered two second-floor windows on 2026-07-10. "
            "Rain water entered through the damaged roof causing soaking damage "
            "to the master bedroom ceiling, drywall, and carpet. Gutters are "
            "detached on the north side. Storm was confirmed by NOAA local "
            "event log for Nashville, TN on that date."
        ),
        "severity":           "Medium",
        "estimated_cost":     9500.00,
        "location":           "12 Oak Ridge Lane, Nashville, TN 37201",
        "date_of_loss":       "2026-07-10",
        # Evidence types required for Storm: Photos, Weather Report, Repair Estimate
        "evidence_items": [
            ("Photos",          "Post-storm roof and window damage photographs"),
            ("Weather Report",  "NOAA storm event log confirming severe thunderstorm"),
            ("Repair Estimate", "Contractor estimate for roof repair and window replacement"),
        ],
        # Policy
        "policy": {
            "coverage_type":         "Homeowners",
            "deductible":            1000.00,
            "coverage_limit":        200000.00,
            "remaining_coverage_limit": 200000.00,
            "policyholder_name":     "Margaret Chen",
            "policy_address":        "12 Oak Ridge Lane, Nashville, TN 37201",
            "state":                 "Tennessee",
            "city":                  "Nashville",
            "country":               "US",
            "postal_code":           "37201",
            "term_type":             "Annual",
            "effective_date":        "2025-08-01",
            "expiration_date":       "2026-08-01",
        },
    },
    {
        "claim_number":       "CLM-2026-7002",
        "policyholder_name":  "Robert Garcia",
        "policy_number":      "POL-7002",
        "loss_type":          "Water Damage",
        "short_description":  (
            "A copper supply pipe behind the second-floor bathroom wall burst "
            "on 2026-07-11 releasing water for approximately 4 hours before "
            "discovered. Flooding saturated bathroom flooring, spread to the "
            "hallway, and leaked through the ceiling into the downstairs "
            "living room. Drywall, insulation, hardwood flooring, and "
            "baseboards are all water-damaged. A licensed plumber has "
            "confirmed the pipe failure and capped the line."
        ),
        "severity":           "High",
        "estimated_cost":     14750.00,
        "location":           "340 Riverside Drive, Portland, OR 97201",
        "date_of_loss":       "2026-07-11",
        # Evidence types required for Water Damage: Photos, Plumber Report, Repair Estimate
        "evidence_items": [
            ("Photos",          "Photographs of damaged bathroom, hallway, and living room ceiling"),
            ("Plumber Report",  "Licensed plumber diagnosis confirming pipe failure and repairs made"),
            ("Repair Estimate", "General contractor estimate for drywall, flooring, and insulation replacement"),
        ],
        # Policy
        "policy": {
            "coverage_type":         "Homeowners",
            "deductible":            1500.00,
            "coverage_limit":        300000.00,
            "remaining_coverage_limit": 300000.00,
            "policyholder_name":     "Robert Garcia",
            "policy_address":        "340 Riverside Drive, Portland, OR 97201",
            "state":                 "Oregon",
            "city":                  "Portland",
            "country":               "US",
            "postal_code":           "97201",
            "term_type":             "Annual",
            "effective_date":        "2025-09-15",
            "expiration_date":       "2026-09-15",
        },
    },
    {
        "claim_number":       "CLM-2026-7003",
        "policyholder_name":  "Patricia Williams",
        "policy_number":      "POL-7003",
        "loss_type":          "Fire",
        "short_description":  (
            "An unattended stove ignited cooking grease on 2026-07-13 starting "
            "a kitchen fire that spread to the adjacent dining room cabinets "
            "and ceiling before the fire department arrived. Fire and smoke "
            "damage is extensive across the kitchen and dining room. Smoke "
            "permeated the entire home. Fire department report confirms "
            "accidental cause; no arson indicators noted. The kitchen is "
            "completely uninhabitable and the HVAC system circulated smoke "
            "throughout the property."
        ),
        "severity":           "High",
        "estimated_cost":     22000.00,
        "location":           "78 Elm Street, Phoenix, AZ 85001",
        "date_of_loss":       "2026-07-13",
        # Evidence types required for Fire: Photos, Fire Report, Repair Estimate
        "evidence_items": [
            ("Photos",          "Fire and smoke damage photographs of kitchen, dining room, and living areas"),
            ("Fire Report",     "Fire department incident report confirming accidental kitchen fire"),
            ("Repair Estimate", "Restoration contractor estimate for fire and smoke remediation"),
        ],
        # Policy
        "policy": {
            "coverage_type":         "Homeowners",
            "deductible":            2000.00,
            "coverage_limit":        350000.00,
            "remaining_coverage_limit": 350000.00,
            "policyholder_name":     "Patricia Williams",
            "policy_address":        "78 Elm Street, Phoenix, AZ 85001",
            "state":                 "Arizona",
            "city":                  "Phoenix",
            "country":               "US",
            "postal_code":           "85001",
            "term_type":             "Annual",
            "effective_date":        "2025-10-01",
            "expiration_date":       "2026-10-01",
        },
    },
]


# ── Insertion helpers ─────────────────────────────────────────────────────────

def _claim_exists(cur, claim_number: str) -> bool:
    cur.execute("SELECT 1 FROM claims WHERE claim_number = %s", (claim_number,))
    return cur.fetchone() is not None


def _policy_exists(cur, policy_number: str) -> bool:
    cur.execute("SELECT 1 FROM policy_details WHERE policy_number = %s", (policy_number,))
    return cur.fetchone() is not None


def _adjuster_findings_exist(cur, claim_id: str) -> bool:
    cur.execute("SELECT 1 FROM adjuster_findings WHERE claim_id = %s", (claim_id,))
    return cur.fetchone() is not None


def insert_claim(cur, c: dict) -> int:
    cur.execute(
        """
        INSERT INTO claims (
            claim_number, policyholder_name, policy_number,
            loss_type, short_description, severity, estimated_cost,
            status, location, date_of_loss
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,'Open',%s,%s)
        RETURNING id
        """,
        (
            c["claim_number"], c["policyholder_name"], c["policy_number"],
            c["loss_type"], c["short_description"], c["severity"],
            c["estimated_cost"], c["location"], c["date_of_loss"],
        ),
    )
    row = cur.fetchone()
    return row["id"]


def insert_policy(cur, policy_number: str, p: dict):
    cur.execute(
        """
        INSERT INTO policy_details (
            policy_number, status, coverage_type, deductible,
            coverage_limit, remaining_coverage_limit,
            policyholder_name, policy_address, state, city,
            country, postal_code, term_type,
            effective_date, expiration_date
        ) VALUES (%s,'Active',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            policy_number,
            p["coverage_type"], p["deductible"],
            p["coverage_limit"], p["remaining_coverage_limit"],
            p["policyholder_name"], p["policy_address"],
            p["state"], p["city"], p["country"], p["postal_code"],
            p["term_type"], p["effective_date"], p["expiration_date"],
        ),
    )


def insert_evidence_items(cur, claim_number: str, items: list):
    import random
    for evidence_type, notes in items:
        evidence_id = f"EVD-{claim_number}-{random.randint(1000, 9999)}"
        cur.execute(
            """
            INSERT INTO evidence_items
                (evidence_id, claim_id, evidence_type, notes, status)
            VALUES (%s,%s,%s,%s,'Pending')
            """,
            (evidence_id, claim_number, evidence_type, notes),
        )


def insert_adjuster_findings(cur, claim_number: str, loss_type: str):
    cur.execute(
        """
        INSERT INTO adjuster_findings (
            claim_id, adjuster_name, cause_of_loss, coverage_confirmed,
            fraud_risk, fraud_risk_score, repair_vs_replace, adjusted_reserve
        ) VALUES (%s,'Auto-Seed',%s,'Yes','Low',10,'TBD',0)
        """,
        (claim_number, loss_type),
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        inserted = []
        skipped = []

        for c in CLAIMS:
            cn = c["claim_number"]
            pn = c["policy_number"]

            if _claim_exists(cur, cn):
                skipped.append(cn)
                print(f"  SKIP  {cn} — already exists in claims table")
                continue

            # 1. Claim
            claim_id = insert_claim(cur, c)
            print(f"  INSERT claim  {cn}  (id={claim_id}, {c['loss_type']}, ${c['estimated_cost']:,.0f})")

            # 2. Policy
            if not _policy_exists(cur, pn):
                insert_policy(cur, pn, c["policy"])
                print(f"  INSERT policy {pn}")
            else:
                print(f"  SKIP   policy {pn} — already exists")

            # 3. Evidence items
            insert_evidence_items(cur, cn, c["evidence_items"])
            print(f"  INSERT {len(c['evidence_items'])} evidence_items for {cn}")

            # 4. Adjuster findings (coverage_confirmed = 'Yes')
            if not _adjuster_findings_exist(cur, cn):
                insert_adjuster_findings(cur, cn, c["loss_type"])
                print(f"  INSERT adjuster_findings for {cn} (coverage_confirmed=Yes)")

            inserted.append(cn)

        conn.commit()
        print()
        print("=" * 60)
        print(f"Done. Inserted: {inserted or 'none'}")
        print(f"      Skipped:  {skipped or 'none'}")
        print()
        print("Ready to test Adjuster Orchestrator with:")
        for c in CLAIMS:
            cn = c["claim_number"]
            print(f"  '{cn}' — {c['loss_type']}, severity={c['severity']}, "
                  f"cost=${c['estimated_cost']:,.0f}, policyholder={c['policyholder_name']}")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
