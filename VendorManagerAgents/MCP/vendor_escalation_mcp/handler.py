"""
handler.py — Vendor Escalation
─────────────────────────────────
Logs escalations against vendors/claims and scans for overdue jobs to
escalate automatically.
"""

import logging
import os
import random
import sys
from datetime import date
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)


def _rand_suffix(n: int) -> str:
    return "".join(random.choices("0123456789", k=n))


def create_vendor_escalation(claim_id: str, vendor_id: str, severity: str, message: str,
                              created_by: str = "Vendor Manager") -> dict:
    escalation_id = f"VESC-{_rand_suffix(6)}"
    today = date.today().isoformat()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO escalation_log_output (escalation_id, claim_id, vendor_id, severity, message,
                                                 created_by, date)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (escalation_id, claim_id, vendor_id, severity, message, created_by, today),
        )
        conn.commit()
        return {
            "id": cur.lastrowid, "escalation_id": escalation_id, "claim_id": claim_id,
            "vendor_id": vendor_id, "severity": severity, "message": message,
            "created_by": created_by, "date": today,
        }
    finally:
        conn.close()


def get_vendor_escalations(vendor_id: Optional[str] = None, claim_id: Optional[str] = None) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query = "SELECT * FROM escalation_log_output WHERE 1=1"
        params = []
        if vendor_id:
            query += " AND vendor_id = %s"
            params.append(vendor_id)
        if claim_id:
            query += " AND claim_id = %s"
            params.append(claim_id)
        query += " ORDER BY id DESC"
        cur.execute(query, params)
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def _upsert_job_status_update(conn, claim_id: str, escalation_flag: str, priority: str) -> None:
    cur = conn.cursor()
    cur.execute("SELECT id FROM job_status_update_output WHERE claim_id = %s", (claim_id,))
    existing = cur.fetchone()
    if existing:
        cur.execute(
            "UPDATE job_status_update_output SET escalation_flag = %s, priority = %s WHERE id = %s",
            (escalation_flag, priority, existing["id"]),
        )
    else:
        cur.execute(
            "INSERT INTO job_status_update_output (claim_id, escalation_flag, priority) VALUES (%s,%s,%s)",
            (claim_id, escalation_flag, priority),
        )


def escalate_overdue_jobs(vendor_id: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query = "SELECT * FROM vendor_jobs_input WHERE sla_status = 'Overdue' AND active = 'Yes'"
        params = []
        if vendor_id:
            query += " AND vendor_id = %s"
            params.append(vendor_id)
        cur.execute(query, params)
        overdue_jobs = row_to_dict(cur.fetchall())

        escalations = []
        for job in overdue_jobs:
            esc = create_vendor_escalation(
                claim_id=job["claim_id"],
                vendor_id=job["vendor_id"],
                severity="High",
                message=f"Job for claim {job['claim_id']} with vendor {job['vendor_id']} is overdue",
                created_by="Vendor Manager",
            )
            escalations.append(esc)
            _upsert_job_status_update(conn, job["claim_id"], "Yes", "High")

        conn.commit()
        return {
            "vendor_id": vendor_id,
            "overdue_job_count": len(overdue_jobs),
            "escalations_created": escalations,
        }
    finally:
        conn.close()
