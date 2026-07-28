"""
handler.py — Dispatch
────────────────────────
Creates and tracks work orders for vendor/expert dispatch, with a
dispatch_logs audit trail.
"""

import logging
import os
import random
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)


def _rand_suffix(n: int) -> str:
    return "".join(random.choices("0123456789", k=n))


def create_work_order(claim_id: str, claim_number: str, expert_id: str, expert_name: str,
                       expert_type: str, scheduled_date: str, scheduled_time: str,
                       customer_address: str, assigned_by: str,
                       estimated_arrival: Optional[str] = None,
                       estimated_cost: Optional[float] = None,
                       priority: str = "Normal",
                       notes_to_expert: Optional[str] = None,
                       customer_phone: Optional[str] = None,
                       customer_email: Optional[str] = None) -> dict:
    work_order_id = f"WO-{_rand_suffix(6)}"
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO work_orders (work_order_id, claim_id, claim_number, expert_id, expert_name,
                                      expert_type, scheduled_date, scheduled_time, estimated_arrival,
                                      estimated_cost, status, priority, notes_to_expert,
                                      customer_address, customer_phone, customer_email, assigned_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, 'Scheduled', %s, %s, %s, %s, %s, %s)
            """,
            (work_order_id, claim_id, claim_number, expert_id, expert_name, expert_type,
             scheduled_date, scheduled_time, estimated_arrival, estimated_cost, priority,
             notes_to_expert, customer_address, customer_phone, customer_email, assigned_by),
        )

        log_id = f"LOG-{_rand_suffix(6)}"
        cur.execute(
            """
            INSERT INTO dispatch_logs (log_id, work_order_id, claim_id, action, action_by, details,
                                        previous_status, new_status)
            VALUES (%s,%s,%s, 'Created', %s, %s, NULL, 'Scheduled')
            """,
            (log_id, work_order_id, claim_id, assigned_by,
             f"Work order created for {expert_name} ({expert_type}) on {scheduled_date} {scheduled_time}"),
        )
        conn.commit()

        cur.execute("SELECT * FROM work_orders WHERE work_order_id = %s", (work_order_id,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_work_order(work_order_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM work_orders WHERE work_order_id = %s", (work_order_id,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def list_work_orders(claim_id: Optional[str] = None, status: Optional[str] = None) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query = "SELECT * FROM work_orders WHERE 1=1"
        params = []
        if claim_id:
            query += " AND claim_id = %s"
            params.append(claim_id)
        if status:
            query += " AND status = %s"
            params.append(status)
        query += " ORDER BY id DESC"
        cur.execute(query, params)
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def update_work_order_status(work_order_id: str, status: str, action_by: str,
                              details: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM work_orders WHERE work_order_id = %s", (work_order_id,))
        wo = row_to_dict(cur.fetchone())
        if not wo:
            raise ValueError(f"Work order {work_order_id} not found")

        previous_status = wo["status"]
        now = datetime.now().isoformat()

        updates = ["status = %s"]
        params = [status]
        if status == "In Progress":
            updates.append("started_at = %s")
            params.append(now)
        elif status == "Completed":
            updates.append("completed_at = %s")
            params.append(now)
        elif status == "Canceled":
            updates.append("canceled_at = %s")
            params.append(now)
            if details:
                updates.append("cancel_reason = %s")
                params.append(details)

        params.append(work_order_id)
        cur.execute(f"UPDATE work_orders SET {', '.join(updates)} WHERE work_order_id = %s", params)

        log_id = f"LOG-{_rand_suffix(6)}"
        cur.execute(
            """
            INSERT INTO dispatch_logs (log_id, work_order_id, claim_id, action, action_by, details,
                                        previous_status, new_status)
            VALUES (%s,%s,%s, 'Status Update', %s,%s,%s,%s)
            """,
            (log_id, work_order_id, wo["claim_id"], action_by, details, previous_status, status),
        )
        conn.commit()

        cur.execute("SELECT * FROM work_orders WHERE work_order_id = %s", (work_order_id,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_dispatch_logs(work_order_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM dispatch_logs WHERE work_order_id = %s ORDER BY id ASC", (work_order_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()
