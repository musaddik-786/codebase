"""
handler.py — Vendor Cost Benchmark
─────────────────────────────────────
Records vendor cost data and computes cost variance against benchmarks.
"""

import logging
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)


def get_vendor_benchmark(vendor_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM vendor_benchmarks WHERE vendor_id = %s", (vendor_id,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_vendor_cost_inputs(vendor_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM vendor_cost_input WHERE vendor_id = %s ORDER BY id DESC", (vendor_id,))
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def record_vendor_cost(vendor_id: str, claim_id: str, estimated_cost: float,
                        actual_cost: Optional[float] = None) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO vendor_cost_input (vendor_id, claim_id, estimated_cost, actual_cost) VALUES (%s,%s,%s,%s)",
            (vendor_id, claim_id, estimated_cost, actual_cost),
        )
        conn.commit()
        return {
            "id": cur.lastrowid, "vendor_id": vendor_id, "claim_id": claim_id,
            "estimated_cost": estimated_cost, "actual_cost": actual_cost,
        }
    finally:
        conn.close()


def compute_cost_variance(vendor_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT estimated_cost, actual_cost FROM vendor_cost_input WHERE vendor_id = %s AND actual_cost IS NOT NULL",
            (vendor_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return {
                "vendor_id": vendor_id,
                "status": "no_data",
                "note": "No vendor_cost_input rows with actual_cost found for this vendor.",
            }

        avg_estimate = sum(r["estimated_cost"] for r in rows) / len(rows)
        avg_actual = sum(r["actual_cost"] for r in rows) / len(rows)
        variance = ((avg_actual - avg_estimate) / avg_estimate * 100) if avg_estimate else 0.0

        cur.execute("DELETE FROM cost_variance_output WHERE vendor_id = %s", (vendor_id,))
        cur.execute(
            "INSERT INTO cost_variance_output (vendor_id, avg_estimate, avg_actual, variance) VALUES (%s,%s,%s,%s)",
            (vendor_id, avg_estimate, avg_actual, variance),
        )
        conn.commit()

        cur.execute("SELECT avg_repair_cost FROM vendor_benchmarks WHERE vendor_id = %s", (vendor_id,))
        bench = cur.fetchone()
        benchmark_comparison = None
        if bench and bench["avg_repair_cost"]:
            diff_pct = (avg_actual - bench["avg_repair_cost"]) / bench["avg_repair_cost"] * 100
            benchmark_comparison = {
                "benchmark_avg_repair_cost": bench["avg_repair_cost"],
                "actual_vs_benchmark_pct": round(diff_pct, 2),
                "direction": "above" if diff_pct > 0 else ("below" if diff_pct < 0 else "at"),
            }

        return {
            "vendor_id": vendor_id,
            "avg_estimate": round(avg_estimate, 2),
            "avg_actual": round(avg_actual, 2),
            "variance_pct": round(variance, 2),
            "benchmark_comparison": benchmark_comparison,
            "sample_size": len(rows),
        }
    finally:
        conn.close()
