"""
handler.py — Vendor Matching
───────────────────────────────
Matches vendors to claims based on specialty/loss type and location, ranks
candidates, and records vendor assignments.
"""

import logging
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)

LOSS_TYPE_TO_SPECIALTY = {
    "water damage": "Plumbing",
    "fire": "Roofing",
    "structural": "Contractor",
    "motor": "Auto Body",
    "auto": "Auto Body",
    "electrical": "Electrical",
}


def get_vendors(specialty: Optional[str] = None, city: Optional[str] = None) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query = "SELECT * FROM vendors WHERE 1=1"
        params = []
        if specialty:
            query += " AND specialty = %s"
            params.append(specialty)
        if city:
            query += " AND city = %s"
            params.append(city)
        query += " ORDER BY rating DESC, avg_turnaround_days ASC"
        cur.execute(query, params)
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def get_vendor_master(vendor_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM vendor_master_input WHERE vendor_id = %s", (vendor_id,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def _get_claim(claim_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM claims WHERE claim_number = %s", (claim_id,))
        row = cur.fetchone()
        if row:
            return row_to_dict(row)
        if claim_id.isdigit():
            cur.execute("SELECT * FROM claims WHERE id = %s", (int(claim_id),))
            return row_to_dict(cur.fetchone())
        return None
    finally:
        conn.close()


def _map_loss_type_to_specialty(loss_type: Optional[str]) -> Optional[str]:
    if not loss_type:
        return None
    return LOSS_TYPE_TO_SPECIALTY.get(loss_type.strip().lower())


def match_vendor_for_claim(claim_id: str) -> dict:
    claim = _get_claim(claim_id)
    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    loss_type = claim.get("loss_type")
    specialty = _map_loss_type_to_specialty(loss_type)

    location = claim.get("location") or ""
    city = None
    if "," in location:
        # e.g. "123 Main St, Springfield" -> take last comma-separated token's
        # leading part before any state/zip as the city.
        city = location.split(",")[-1].strip().split(" ")[0] if location.split(",")[-1].strip() else None
        # fall back: try second-to-last token as the city name itself
        parts = [p.strip() for p in location.split(",")]
        if len(parts) >= 2:
            city = parts[-1]

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if specialty:
            cur.execute(
                "SELECT * FROM vendors WHERE specialty = %s ORDER BY rating DESC, avg_turnaround_days ASC",
                (specialty,),
            )
        else:
            cur.execute("SELECT * FROM vendors ORDER BY rating DESC, avg_turnaround_days ASC")
        candidates = row_to_dict(cur.fetchall())

        results = []
        for v in candidates[:3]:
            cur.execute("SELECT vendor_id FROM vendor_master_input WHERE name = %s LIMIT 1", (v["name"],))
            master = cur.fetchone()
            v["vendor_id"] = master["vendor_id"] if master else f"VEN-00{v['id']}"
            results.append(v)

        return {
            "claim_id": claim_id,
            "loss_type": loss_type,
            "matched_specialty": specialty or "Any",
            "location_hint": city,
            "candidates": results,
        }
    finally:
        conn.close()


def assign_vendor_to_claim(claim_id: str, vendor_id: str, vendor_type: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM vendor_assignment WHERE claim_id = %s AND vendor_id = %s", (claim_id, vendor_id))
        existing = cur.fetchone()
        if existing:
            cur.execute(
                """
                UPDATE vendor_assignment
                SET vendor_type = %s, assignment_status = 'Assigned', sla_status = 'On Track'
                WHERE id = %s
                """,
                (vendor_type, existing["id"]),
            )
        else:
            cur.execute(
                """
                INSERT INTO vendor_assignment (claim_id, vendor_id, vendor_type, assignment_status, sla_status)
                VALUES (%s,%s,%s, 'Assigned', 'On Track')
                """,
                (claim_id, vendor_id, vendor_type),
            )
        conn.commit()
        return {
            "claim_id": claim_id, "vendor_id": vendor_id, "vendor_type": vendor_type,
            "assignment_status": "Assigned", "sla_status": "On Track",
        }
    finally:
        conn.close()
