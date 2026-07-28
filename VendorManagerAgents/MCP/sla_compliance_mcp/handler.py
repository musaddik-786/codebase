"""
handler.py — SLA Compliance
───────────────────────────────
Computes SLA compliance percentage and avg response/completion times for a
vendor.
"""

import logging
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)


def get_vendor_jobs_sla(vendor_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM vendor_jobs_input WHERE vendor_id = %s ORDER BY id DESC", (vendor_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def compute_sla_compliance(vendor_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT sla_status FROM vendor_jobs_input WHERE vendor_id = %s AND sla_status IS NOT NULL",
            (vendor_id,),
        )
        rows = cur.fetchall()
        if rows:
            met = sum(1 for r in rows if r["sla_status"] != "Overdue")
            sla_compliance = (met / len(rows)) * 100
        else:
            sla_compliance = None

        cur.execute("SELECT avg_turnaround_days FROM vendors v JOIN vendor_master_input m ON m.name = v.name WHERE m.vendor_id = %s", (vendor_id,))
        row = cur.fetchone()
        avg_turnaround = row["avg_turnaround_days"] if row else None

        avg_response_time = f"{avg_turnaround} days" if avg_turnaround is not None else "N/A"
        avg_completion_time = f"{avg_turnaround} days" if avg_turnaround is not None else "N/A"

        cur.execute("DELETE FROM sla_tracker_output WHERE vendor_id = %s", (vendor_id,))
        cur.execute(
            """
            INSERT INTO sla_tracker_output (vendor_id, avg_response_time, avg_completion_time, sla_compliance)
            VALUES (%s,%s,%s,%s)
            """,
            (vendor_id, avg_response_time, avg_completion_time, sla_compliance),
        )
        conn.commit()

        return {
            "vendor_id": vendor_id,
            "sla_compliance_pct": round(sla_compliance, 2) if sla_compliance is not None else None,
            "avg_response_time": avg_response_time,
            "avg_completion_time": avg_completion_time,
            "job_count": len(rows),
        }
    finally:
        conn.close()


def get_sla_tracker(vendor_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM sla_tracker_output WHERE vendor_id = %s", (vendor_id,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()
