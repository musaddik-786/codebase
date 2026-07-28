"""
main.py
───────
MCP server entry point for the SIU (Special Investigation Unit) Agents
platform — hosts 12 agent MCP sub-apps on a single FastAPI app (port 9000),
backed by the SQLite database SHARED with PolicyholderAgents
(`PolicyholderAgents/data/policyholder.db`).

Registered sub-apps:
  /api/v1/fraud_risk_scoring   — Fraud Risk Scoring     [FULL]
  /api/v1/case_assignment       — Case Assignment        [PLACEHOLDER]
  /api/v1/behavioral_analytics    — Behavioral Analytics   [PLACEHOLDER]
  /api/v1/entity_relationship       — Entity Relationship    [PLACEHOLDER]
  /api/v1/fraud_pattern                — Fraud Pattern          [FULL]
  /api/v1/network_analysis               — Network Analysis       [PLACEHOLDER]
  /api/v1/evidence_correlation             — Evidence Correlation   [PLACEHOLDER]
  /api/v1/fraud_escalation                   — Fraud Escalation       [FULL]
  /api/v1/fraud_resolution                     — Fraud Resolution       [FULL]
  /api/v1/legal_escalation                       — Legal Escalation       [FULL]
  /api/v1/watchlist_update                         — Watchlist Update       [FULL]
  /api/v1/siu_closure                                — SIU Closure            [PLACEHOLDER]

Run:
    py -3 main.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "common"))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP

from init_db import init_db

from fraud_risk_scoring_router import router as fraud_risk_scoring_router
from case_assignment_router import router as case_assignment_router
from behavioral_analytics_router import router as behavioral_analytics_router
from entity_relationship_router import router as entity_relationship_router
from fraud_pattern_router import router as fraud_pattern_router
from network_analysis_router import router as network_analysis_router
from evidence_correlation_router import router as evidence_correlation_router
from fraud_escalation_router import router as fraud_escalation_router
from fraud_resolution_router import router as fraud_resolution_router
from legal_escalation_router import router as legal_escalation_router
from watchlist_update_router import router as watchlist_update_router
from siu_closure_router import router as siu_closure_router

import uvicorn


app = FastAPI(docs_url="/docs", title="Jarvis SIU Agents MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _make_cors_app(title: str, description: str = "") -> FastAPI:
    sub = FastAPI(title=title, description=description)
    sub.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return sub


# ── Sub-app: fraud_risk_scoring (FULL) ─────────────────────────────────────

fraud_risk_scoring_app = _make_cors_app(
    title="fraud_risk_scoring_agent_mcps",
    description="MCP tools for aggregate fraud risk score computation.",
)
fraud_risk_scoring_app.include_router(fraud_risk_scoring_router)
FastApiMCP(
    fraud_risk_scoring_app,
    include_operations=[
        "get_fraud_risk_snapshot",
        "get_ai_fraud_signals",
        "get_fraud_flags",
        "recompute_fraud_risk_score",
    ],
).mount_http()
app.mount("/api/v1/fraud_risk_scoring", fraud_risk_scoring_app)


# ── Sub-app: case_assignment (PLACEHOLDER) ──────────────────────────────────

case_assignment_app = _make_cors_app(
    title="case_assignment_agent_mcps",
    description="[PLACEHOLDER] MCP tools for SIU case/investigator assignment.",
)
case_assignment_app.include_router(case_assignment_router)
FastApiMCP(
    case_assignment_app,
    include_operations=["get_siu_case_master"],
).mount_http()
app.mount("/api/v1/case_assignment", case_assignment_app)


# ── Sub-app: behavioral_analytics (PLACEHOLDER) ─────────────────────────────

behavioral_analytics_app = _make_cors_app(
    title="behavioral_analytics_agent_mcps",
    description="[PLACEHOLDER] MCP tools for behavioral pattern analytics.",
)
behavioral_analytics_app.include_router(behavioral_analytics_router)
FastApiMCP(
    behavioral_analytics_app,
    include_operations=["get_siu_activity_log"],
).mount_http()
app.mount("/api/v1/behavioral_analytics", behavioral_analytics_app)


# ── Sub-app: entity_relationship (PLACEHOLDER) ──────────────────────────────

entity_relationship_app = _make_cors_app(
    title="entity_relationship_agent_mcps",
    description="[PLACEHOLDER] MCP tools for entity relationship graph analysis.",
)
entity_relationship_app.include_router(entity_relationship_router)
FastApiMCP(
    entity_relationship_app,
    include_operations=["get_fraud_network_graph"],
).mount_http()
app.mount("/api/v1/entity_relationship", entity_relationship_app)


# ── Sub-app: fraud_pattern (FULL) ───────────────────────────────────────────

fraud_pattern_app = _make_cors_app(
    title="fraud_pattern_agent_mcps",
    description="MCP tools for AI-assisted fraud typology/pattern detection.",
)
fraud_pattern_app.include_router(fraud_pattern_router)
FastApiMCP(
    fraud_pattern_app,
    include_operations=[
        "get_vendor_red_flags",
        "write_vendor_red_flag",
        "get_fraud_risk_flags_output",
        "write_fraud_risk_flag_output",
        "detect_fraud_patterns",
    ],
).mount_http()
app.mount("/api/v1/fraud_pattern", fraud_pattern_app)


# ── Sub-app: network_analysis (PLACEHOLDER) ─────────────────────────────────

network_analysis_app = _make_cors_app(
    title="network_analysis_agent_mcps",
    description="[PLACEHOLDER] MCP tools for vendor network/collusion analysis.",
)
network_analysis_app.include_router(network_analysis_router)
FastApiMCP(
    network_analysis_app,
    include_operations=["get_vendor_network_signals"],
).mount_http()
app.mount("/api/v1/network_analysis", network_analysis_app)


# ── Sub-app: evidence_correlation (PLACEHOLDER) ─────────────────────────────

evidence_correlation_app = _make_cors_app(
    title="evidence_correlation_agent_mcps",
    description="[PLACEHOLDER] MCP tools for cross-referencing investigation evidence.",
)
evidence_correlation_app.include_router(evidence_correlation_router)
FastApiMCP(
    evidence_correlation_app,
    include_operations=["get_investigation_notes"],
).mount_http()
app.mount("/api/v1/evidence_correlation", evidence_correlation_app)


# ── Sub-app: fraud_escalation (FULL) ────────────────────────────────────────

fraud_escalation_app = _make_cors_app(
    title="fraud_escalation_agent_mcps",
    description="MCP tools for escalating claims to SIU.",
)
fraud_escalation_app.include_router(fraud_escalation_router)
FastApiMCP(
    fraud_escalation_app,
    include_operations=[
        "create_siu_escalation",
        "get_siu_escalation",
        "create_siu_case",
        "log_siu_timeline_event",
        "forward_to_siu",
    ],
).mount_http()
app.mount("/api/v1/fraud_escalation", fraud_escalation_app)


# ── Sub-app: fraud_resolution (FULL) ────────────────────────────────────────

fraud_resolution_app = _make_cors_app(
    title="fraud_resolution_agent_mcps",
    description="MCP tools for recording SIU investigation decisions and closing cases.",
)
fraud_resolution_app.include_router(fraud_resolution_router)
FastApiMCP(
    fraud_resolution_app,
    include_operations=[
        "write_siu_decision",
        "get_siu_decision",
        "resolve_siu_case",
    ],
).mount_http()
app.mount("/api/v1/fraud_resolution", fraud_resolution_app)


# ── Sub-app: legal_escalation (FULL) ────────────────────────────────────────

legal_escalation_app = _make_cors_app(
    title="legal_escalation_agent_mcps",
    description="MCP tools for referring confirmed-fraud cases to Legal.",
)
legal_escalation_app.include_router(legal_escalation_router)
FastApiMCP(
    legal_escalation_app,
    include_operations=[
        "create_legal_escalation",
        "get_legal_escalation",
        "update_legal_escalation_outcome",
        "refer_to_legal",
    ],
).mount_http()
app.mount("/api/v1/legal_escalation", legal_escalation_app)


# ── Sub-app: watchlist_update (FULL) ────────────────────────────────────────

watchlist_update_app = _make_cors_app(
    title="watchlist_update_agent_mcps",
    description="MCP tools for maintaining the SIU fraud watchlist.",
)
watchlist_update_app.include_router(watchlist_update_router)
FastApiMCP(
    watchlist_update_app,
    include_operations=[
        "add_to_watchlist",
        "get_watchlist",
        "check_watchlist",
        "remove_from_watchlist",
        "update_watchlist_from_case",
    ],
).mount_http()
app.mount("/api/v1/watchlist_update", watchlist_update_app)


# ── Sub-app: siu_closure (PLACEHOLDER) ──────────────────────────────────────

siu_closure_app = _make_cors_app(
    title="siu_closure_agent_mcps",
    description="[PLACEHOLDER] MCP tools for SIU case closure readiness.",
)
siu_closure_app.include_router(siu_closure_router)
FastApiMCP(
    siu_closure_app,
    include_operations=["get_siu_progress_tracker"],
).mount_http()
app.mount("/api/v1/siu_closure", siu_closure_app)


# ── Health ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "jarvis_siu_agents_mcp",
        "sub_apps": [
            "fraud_risk_scoring",
            "case_assignment",
            "behavioral_analytics",
            "entity_relationship",
            "fraud_pattern",
            "network_analysis",
            "evidence_correlation",
            "fraud_escalation",
            "fraud_resolution",
            "legal_escalation",
            "watchlist_update",
            "siu_closure",
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
