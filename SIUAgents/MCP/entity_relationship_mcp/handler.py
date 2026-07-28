"""
handler.py — Entity Relationship
──────────────────────────────────
Builds and traverses the entity relationship graph, linking claimants,
vendors, adjusters, and addresses across claims to detect suspicious
connections.
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


def get_fraud_network_graph(entity_id: str) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM fraud_network_graph WHERE entity_id = %s OR connected_entity_id = %s",
            (entity_id, entity_id),
        )
        return row_to_dict(cur.fetchall()) or []
    finally:
        conn.close()


def build_entity_graph(claim_id: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
        claim = row_to_dict(cur.fetchone())
        if not claim:
            return {"error": f"claim_id {claim_id} not found"}

        claimant = claim.get("claimant_name") or claim.get("policy_holder_name", "")
        vendor_id = claim.get("vendor_id", "")
        adjuster = claim.get("assigned_adjuster", "")
        address = claim.get("loss_location") or claim.get("address", "")

        cur.execute(
            "SELECT * FROM fraud_network_graph WHERE entity_id = %s OR connected_entity_id = %s",
            (claimant, claimant),
        )
        existing_edges = row_to_dict(cur.fetchall()) or []

        shared_claimant_claims = []
        if claimant:
            cur.execute(
                "SELECT claim_id, loss_type, loss_amount FROM claims WHERE (claimant_name = %s OR policy_holder_name = %s) AND claim_id != %s",
                (claimant, claimant, claim_id),
            )
            shared_claimant_claims = row_to_dict(cur.fetchall()) or []

        shared_vendor_claims = []
        if vendor_id:
            cur.execute(
                "SELECT claim_id, loss_type FROM claims WHERE vendor_id = %s AND claim_id != %s",
                (vendor_id, claim_id),
            )
            shared_vendor_claims = row_to_dict(cur.fetchall()) or []

    finally:
        conn.close()

    nodes = [
        {"type": "claimant", "id": claimant},
        {"type": "claim", "id": claim_id},
    ]
    edges = []
    if vendor_id:
        nodes.append({"type": "vendor", "id": vendor_id})
        edges.append({"from": claim_id, "to": vendor_id, "relationship": "serviced_by"})
    if adjuster:
        nodes.append({"type": "adjuster", "id": adjuster})
        edges.append({"from": claim_id, "to": adjuster, "relationship": "handled_by"})
    for sc in shared_claimant_claims:
        edges.append({"from": claimant, "to": sc["claim_id"], "relationship": "also_filed"})
    for sv in shared_vendor_claims:
        edges.append({"from": vendor_id, "to": sv["claim_id"], "relationship": "also_serviced"})

    graph_data = {"nodes": nodes, "edges": edges}

    try:
        client = _get_openai_client()
        prompt = (
            "You are an SIU entity relationship analyst. Examine the entity graph below "
            "for suspicious connections (shared claimants/vendors across multiple claims, "
            "unusual network density). Respond with JSON: "
            '{"risk_score": 0-100, "suspicious_connections": ["..."], '
            '"network_density": "Low|Medium|High", "finding": "..."}.\n\n'
            f"Claim: {claim_id}\nClaimant: {claimant}\n"
            f"Graph: {json.dumps(graph_data, default=str)}\n"
            f"Shared claimant claims count: {len(shared_claimant_claims)}\n"
            f"Shared vendor claims count: {len(shared_vendor_claims)}\n"
            f"Existing fraud graph edges: {len(existing_edges)}"
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        llm_result = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.warning("LLM entity graph analysis failed: %s", e)
        llm_result = {
            "risk_score": 0,
            "suspicious_connections": [],
            "network_density": "Low",
            "finding": "Automated entity graph analysis failed; manual review needed",
        }

    conn2 = get_db_connection()
    try:
        cur2 = conn2.cursor()
        for edge in edges:
            try:
                cur2.execute(
                    """
                    INSERT INTO fraud_network_graph
                      (claim_id, entity_id, connected_entity_id, relationship_type, risk_score, detected_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        claim_id,
                        edge["from"],
                        edge["to"],
                        edge["relationship"],
                        llm_result.get("risk_score", 0),
                        datetime.utcnow().isoformat(),
                    ),
                )
            except Exception:
                pass
        conn2.commit()
    except Exception as e:
        conn2.rollback()
        log.warning("Could not write fraud_network_graph edges: %s", e)
    finally:
        conn2.close()

    return {
        "claim_id": claim_id,
        "claimant": claimant,
        "graph": graph_data,
        "shared_claimant_claims": len(shared_claimant_claims),
        "shared_vendor_claims": len(shared_vendor_claims),
        **llm_result,
    }
