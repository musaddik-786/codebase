"""
handler.py — Network Analysis
───────────────────────────────
Runs graph-based collusion and fraud-ring detection by cross-referencing
fraud_network_graph edges with vendor_network_signals.
"""

import json
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from db import get_db_connection, row_to_dict  # noqa: E402
from dotenv import load_dotenv, find_dotenv
from openai import AzureOpenAI

load_dotenv(find_dotenv())

log = logging.getLogger(__name__)

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-11-13")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5.1")


def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )


def get_vendor_network_signals(vendor_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM vendor_network_signals WHERE vendor_id = %s ORDER BY signal_date DESC",
            (vendor_id,),
        )
        return row_to_dict(cur.fetchall()) or []
    finally:
        conn.close()


def detect_fraud_rings(claim_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
        claim = row_to_dict(cur.fetchone())
        if not claim:
            return {"error": f"claim_id {claim_id} not found"}

        cur.execute(
            "SELECT * FROM fraud_network_graph WHERE claim_id = %s",
            (claim_id,),
        )
        network_edges = row_to_dict(cur.fetchall()) or []

        vendor_ids = list({e.get("connected_entity_id") for e in network_edges
                          if e.get("relationship_type") == "serviced_by" and e.get("connected_entity_id")})

        vendor_signals = []
        for vid in vendor_ids[:5]:
            cur.execute(
                "SELECT * FROM vendor_network_signals WHERE vendor_id = %s ORDER BY signal_date DESC LIMIT 10",
                (vid,),
            )
            rows = row_to_dict(cur.fetchall()) or []
            vendor_signals.extend(rows)

        connected_claims = list({e.get("connected_entity_id") for e in network_edges
                                 if e.get("relationship_type") in ("also_filed", "also_serviced")})

        cluster_size = len(connected_claims) + 1
        unique_vendor_count = len(vendor_ids)

    finally:
        conn.close()

    try:
        client = _get_openai_client()
        prompt = (
            "You are an SIU network analyst specializing in fraud ring detection. "
            "Analyze the network graph and vendor signals for collusion or ring patterns. "
            "Respond with JSON: "
            '{"ring_detected": true/false, "ring_risk_score": 0-100, '
            '"ring_members": ["..."], "collusion_pattern": "...", '
            '"recommendation": "Escalate|Monitor|Close"}.\n\n'
            f"Claim: {claim_id}\n"
            f"Network edges count: {len(network_edges)}\n"
            f"Connected claims: {connected_claims}\n"
            f"Vendor IDs involved: {vendor_ids}\n"
            f"Vendor signal count: {len(vendor_signals)}\n"
            f"Cluster size: {cluster_size}\n"
            f"Vendor signals sample: {json.dumps(vendor_signals[:5], default=str)}"
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        llm_result = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.warning("LLM network analysis failed: %s", e)
        llm_result = {
            "ring_detected": cluster_size >= 3,
            "ring_risk_score": min(cluster_size * 10, 100),
            "ring_members": connected_claims,
            "collusion_pattern": "Automated analysis failed; manual review needed",
            "recommendation": "Monitor",
        }

    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        cur2.execute(
            """
            INSERT INTO siu_network_analysis_results
              (claim_id, ring_detected, ring_risk_score, ring_members,
               collusion_pattern, recommendation, analyzed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (claim_id) DO UPDATE SET
              ring_detected = EXCLUDED.ring_detected,
              ring_risk_score = EXCLUDED.ring_risk_score,
              ring_members = EXCLUDED.ring_members,
              collusion_pattern = EXCLUDED.collusion_pattern,
              recommendation = EXCLUDED.recommendation,
              analyzed_at = EXCLUDED.analyzed_at
            """,
            (
                claim_id,
                1 if llm_result.get("ring_detected") else 0,
                llm_result.get("ring_risk_score", 0),
                json.dumps(llm_result.get("ring_members", [])),
                llm_result.get("collusion_pattern"),
                llm_result.get("recommendation"),
                datetime.utcnow().isoformat(),
            ),
        )
        conn2.commit()
    except Exception as e:
        conn2.rollback()
        log.warning("Could not write siu_network_analysis_results: %s", e)
    finally:
        conn2.close()

    return {
        "claim_id": claim_id,
        "network_edge_count": len(network_edges),
        "cluster_size": cluster_size,
        "vendor_ids_involved": vendor_ids,
        **llm_result,
    }
