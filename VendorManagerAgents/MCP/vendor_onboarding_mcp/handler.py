"""
handler.py — Vendor Onboarding
───────────────────────────────
Manages vendor applications: listing, submission, approval (provisioning a
new vendor + master record), and rejection.
"""

import logging
import os
import sys
from datetime import datetime, date
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402

log = logging.getLogger(__name__)


def list_vendor_applications(status: Optional[str] = None) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if status:
            cur.execute("SELECT * FROM vendor_applications WHERE status = %s ORDER BY id DESC", (status,))
        else:
            cur.execute("SELECT * FROM vendor_applications ORDER BY id DESC")
        return row_to_dict(cur.fetchall())
    finally:
        conn.close()


def get_vendor_application(application_id: int) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM vendor_applications WHERE id = %s", (application_id,))
        return row_to_dict(cur.fetchone())
    finally:
        conn.close()


def submit_vendor_application(name: str, specialty: str, location: str,
                               license_number: Optional[str] = None,
                               license_expiry_date: Optional[str] = None,
                               contact_email: Optional[str] = None,
                               contact_phone: Optional[str] = None,
                               submitted_date: Optional[str] = None) -> dict:
    submitted_date = submitted_date or date.today().isoformat()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO vendor_applications (name, specialty, location, license_number,
                                              license_expiry_date, contact_email, contact_phone,
                                              status, submitted_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s, 'Pending', %s)
            """,
            (name, specialty, location, license_number, license_expiry_date, contact_email,
             contact_phone, submitted_date),
        )
        conn.commit()
        return {
            "id": cur.lastrowid, "name": name, "specialty": specialty, "location": location,
            "license_number": license_number, "license_expiry_date": license_expiry_date,
            "contact_email": contact_email, "contact_phone": contact_phone,
            "status": "Pending", "submitted_date": submitted_date,
        }
    finally:
        conn.close()


def _derive_city_state(location: str):
    if not location:
        return None, None
    parts = [p.strip() for p in location.split(",")]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return parts[0], None


def approve_vendor_application(application_id: int) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM vendor_applications WHERE id = %s", (application_id,))
        app = row_to_dict(cur.fetchone())
        if not app:
            raise ValueError(f"Vendor application {application_id} not found")
        if app["status"] != "Pending":
            raise ValueError(f"Vendor application {application_id} is not Pending (status={app['status']})")

        cur.execute("UPDATE vendor_applications SET status = 'Approved' WHERE id = %s", (application_id,))

        city, state = _derive_city_state(app.get("location"))

        license_valid = 1
        expiry = app.get("license_expiry_date")
        if expiry:
            try:
                license_valid = 1 if datetime.fromisoformat(expiry) >= datetime.now() else 0
            except ValueError:
                license_valid = 1

        cur.execute(
            """
            INSERT INTO vendors (name, specialty, license_number, license_valid, rating,
                                  completed_jobs, avg_turnaround_days, avg_cost, city, state,
                                  zip_code, phone, verified)
            VALUES (%s,%s,%s,%s,4.0,0,5,1000.0,%s,%s,NULL,%s,1)
            """,
            (app["name"], app["specialty"], app.get("license_number"), license_valid,
             city, state, app.get("contact_phone")),
        )
        new_vendor_db_id = cur.lastrowid
        vendor_id = f"VEN-00{new_vendor_db_id}"

        cur.execute(
            """
            INSERT INTO vendor_master_input (vendor_id, name, specialty, location, status,
                                              assignment_eligible, license_number,
                                              license_expiry_date, vis_score)
            VALUES (%s,%s,%s,%s, 'Active', 'Yes', %s, %s, 70)
            """,
            (vendor_id, app["name"], app["specialty"], app.get("location"),
             app.get("license_number"), app.get("license_expiry_date")),
        )

        conn.commit()
        return {
            "application_id": application_id,
            "status": "Approved",
            "vendor_db_id": new_vendor_db_id,
            "vendor_id": vendor_id,
            "name": app["name"],
            "specialty": app["specialty"],
        }
    finally:
        conn.close()


def reject_vendor_application(application_id: int, reason: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM vendor_applications WHERE id = %s", (application_id,))
        app = row_to_dict(cur.fetchone())
        if not app:
            raise ValueError(f"Vendor application {application_id} not found")
        cur.execute(
            "UPDATE vendor_applications SET status = 'Rejected', rejection_reason = %s WHERE id = %s",
            (reason, application_id),
        )
        conn.commit()
        return {"application_id": application_id, "status": "Rejected", "rejection_reason": reason}
    finally:
        conn.close()
