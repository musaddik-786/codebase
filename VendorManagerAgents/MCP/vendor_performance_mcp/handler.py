"""
handler.py — Vendor Performance
───────────────────────────────────
Computes the Vendor Intelligence Score (VIS) from job completion rate,
quality ratings, and cost efficiency.
"""

import logging
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)

DEFAULT_COMPONENT_SCORE = 70.0


def get_vendor_jobs(vendor_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM vendor_jobs_input WHERE vendor_id = %s ORDER BY id DESC", (vendor_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def record_vendor_rating(vendor_id: str, rating: float, feedback: Optional[str] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO vendor_rating_input (vendor_id, rating, feedback) VALUES (%s,%s,%s)",
            (vendor_id, rating, feedback),
        )
        conn.commit()
        return {"id": cur.lastrowid, "vendor_id": vendor_id, "rating": rating, "feedback": feedback}
    finally:
        conn.close()


def compute_vendor_performance_score(vendor_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # SLA score from job completion rate
        cur.execute("SELECT status, sla_status FROM vendor_jobs_input WHERE vendor_id = %s", (vendor_id,))
        jobs = cur.fetchall()
        if jobs:
            completed = sum(1 for j in jobs if j["status"] == "Completed")
            completion_rate = completed / len(jobs)
            sla_score = completion_rate * 100
            if any(j["sla_status"] == "Overdue" for j in jobs):
                sla_score = max(0.0, sla_score - 15)
        else:
            sla_score = DEFAULT_COMPONENT_SCORE

        # Quality from average rating
        cur.execute("SELECT AVG(rating) AS avg_rating FROM vendor_rating_input WHERE vendor_id = %s", (vendor_id,))
        row = cur.fetchone()
        if row and row["avg_rating"] is not None:
            quality = (row["avg_rating"] / 5.0) * 100
        else:
            quality = DEFAULT_COMPONENT_SCORE

        # Cost efficiency from cost_variance_output
        cur.execute("SELECT variance FROM cost_variance_output WHERE vendor_id = %s", (vendor_id,))
        row = cur.fetchone()
        if row and row["variance"] is not None:
            cost_efficiency = max(0.0, 100 - abs(row["variance"]))
        else:
            cost_efficiency = DEFAULT_COMPONENT_SCORE

        vis = (sla_score + quality + cost_efficiency) / 3

        cur.execute("DELETE FROM vendor_performance_score_output WHERE vendor_id = %s", (vendor_id,))
        cur.execute(
            """
            INSERT INTO vendor_performance_score_output (vendor_id, vis, sla_score, cost_efficiency, quality)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (vendor_id, vis, sla_score, cost_efficiency, quality),
        )

        cur.execute(
            "UPDATE vendor_master_input SET vis_score = %s WHERE vendor_id = %s",
            (round(vis), vendor_id),
        )
        conn.commit()

        return {
            "vendor_id": vendor_id,
            "vis": round(vis, 2),
            "sla_score": round(sla_score, 2),
            "cost_efficiency": round(cost_efficiency, 2),
            "quality": round(quality, 2),
            "job_count": len(jobs),
        }
    finally:
        conn.close()
