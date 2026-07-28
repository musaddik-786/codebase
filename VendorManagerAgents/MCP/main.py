"""
main.py
───────
MCP server entry point for the Vendor Manager Agents platform — hosts 10
agent MCP sub-apps on a single FastAPI app (port 9100), backed by the SQLite
database SHARED with PolicyholderAgents
(`PolicyholderAgents/data/policyholder.db`).

Registered sub-apps:
  /api/v1/vendor_onboarding     — Vendor Onboarding       [FULL]
  /api/v1/vendor_matching        — Vendor Matching         [FULL]
  /api/v1/vendor_qualification     — Vendor Qualification    [PLACEHOLDER]
  /api/v1/vendor_capacity            — Vendor Capacity Mgmt    [PLACEHOLDER]
  /api/v1/vendor_cost_benchmark        — Vendor Cost Benchmark   [FULL]
  /api/v1/dispatch                       — Dispatch                [FULL]
  /api/v1/vendor_performance               — Vendor Performance     [FULL]
  /api/v1/sla_compliance                     — SLA Compliance         [FULL]
  /api/v1/vendor_escalation                    — Vendor Escalation      [FULL]
  /api/v1/eta_prediction                         — ETA Prediction         [FULL]

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

from vendor_onboarding_router import router as vendor_onboarding_router
from vendor_matching_router import router as vendor_matching_router
from vendor_qualification_router import router as vendor_qualification_router
from vendor_capacity_router import router as vendor_capacity_router
from vendor_cost_benchmark_router import router as vendor_cost_benchmark_router
from dispatch_router import router as dispatch_router
from vendor_performance_router import router as vendor_performance_router
from sla_compliance_router import router as sla_compliance_router
from vendor_escalation_router import router as vendor_escalation_router
from eta_prediction_router import router as eta_prediction_router

import uvicorn


app = FastAPI(docs_url="/docs", title="Jarvis Vendor Manager Agents MCP Server")

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


# ── Sub-app: vendor_onboarding (FULL) ──────────────────────────────────────

vendor_onboarding_app = _make_cors_app(
    title="vendor_onboarding_agent_mcps",
    description="MCP tools for reviewing and processing vendor applications.",
)
vendor_onboarding_app.include_router(vendor_onboarding_router)
FastApiMCP(
    vendor_onboarding_app,
    include_operations=[
        "list_vendor_applications",
        "get_vendor_application",
        "submit_vendor_application",
        "approve_vendor_application",
        "reject_vendor_application",
    ],
).mount_http()
app.mount("/api/v1/vendor_onboarding", vendor_onboarding_app)


# ── Sub-app: vendor_matching (FULL) ─────────────────────────────────────────

vendor_matching_app = _make_cors_app(
    title="vendor_matching_agent_mcps",
    description="MCP tools for matching and assigning vendors to claims.",
)
vendor_matching_app.include_router(vendor_matching_router)
FastApiMCP(
    vendor_matching_app,
    include_operations=[
        "get_vendors",
        "get_vendor_master",
        "match_vendor_for_claim",
        "assign_vendor_to_claim",
    ],
).mount_http()
app.mount("/api/v1/vendor_matching", vendor_matching_app)


# ── Sub-app: vendor_qualification (PLACEHOLDER) ─────────────────────────────

vendor_qualification_app = _make_cors_app(
    title="vendor_qualification_agent_mcps",
    description="[PLACEHOLDER] MCP tools for vendor qualification/compliance scoring.",
)
vendor_qualification_app.include_router(vendor_qualification_router)
FastApiMCP(
    vendor_qualification_app,
    include_operations=["get_vendor_master"],
).mount_http()
app.mount("/api/v1/vendor_qualification", vendor_qualification_app)


# ── Sub-app: vendor_capacity (PLACEHOLDER) ──────────────────────────────────

vendor_capacity_app = _make_cors_app(
    title="vendor_capacity_agent_mcps",
    description="[PLACEHOLDER] MCP tools for vendor capacity/workload management.",
)
vendor_capacity_app.include_router(vendor_capacity_router)
FastApiMCP(
    vendor_capacity_app,
    include_operations=["get_vendor_active_jobs"],
).mount_http()
app.mount("/api/v1/vendor_capacity", vendor_capacity_app)


# ── Sub-app: vendor_cost_benchmark (FULL) ───────────────────────────────────

vendor_cost_benchmark_app = _make_cors_app(
    title="vendor_cost_benchmark_agent_mcps",
    description="MCP tools for vendor cost benchmarking and variance analysis.",
)
vendor_cost_benchmark_app.include_router(vendor_cost_benchmark_router)
FastApiMCP(
    vendor_cost_benchmark_app,
    include_operations=[
        "get_vendor_benchmark",
        "get_vendor_cost_inputs",
        "record_vendor_cost",
        "compute_cost_variance",
    ],
).mount_http()
app.mount("/api/v1/vendor_cost_benchmark", vendor_cost_benchmark_app)


# ── Sub-app: dispatch (FULL) ────────────────────────────────────────────────

dispatch_app = _make_cors_app(
    title="dispatch_agent_mcps",
    description="MCP tools for creating and tracking vendor/expert work orders.",
)
dispatch_app.include_router(dispatch_router)
FastApiMCP(
    dispatch_app,
    include_operations=[
        "create_work_order",
        "get_work_order",
        "list_work_orders",
        "update_work_order_status",
        "get_dispatch_logs",
    ],
).mount_http()
app.mount("/api/v1/dispatch", dispatch_app)


# ── Sub-app: vendor_performance (FULL) ──────────────────────────────────────

vendor_performance_app = _make_cors_app(
    title="vendor_performance_agent_mcps",
    description="MCP tools for computing the Vendor Intelligence Score (VIS).",
)
vendor_performance_app.include_router(vendor_performance_router)
FastApiMCP(
    vendor_performance_app,
    include_operations=[
        "get_vendor_jobs",
        "record_vendor_rating",
        "compute_vendor_performance_score",
    ],
).mount_http()
app.mount("/api/v1/vendor_performance", vendor_performance_app)


# ── Sub-app: sla_compliance (FULL) ──────────────────────────────────────────

sla_compliance_app = _make_cors_app(
    title="sla_compliance_agent_mcps",
    description="MCP tools for tracking vendor SLA compliance.",
)
sla_compliance_app.include_router(sla_compliance_router)
FastApiMCP(
    sla_compliance_app,
    include_operations=[
        "get_vendor_jobs_sla",
        "compute_sla_compliance",
        "get_sla_tracker",
    ],
).mount_http()
app.mount("/api/v1/sla_compliance", sla_compliance_app)


# ── Sub-app: vendor_escalation (FULL) ───────────────────────────────────────

vendor_escalation_app = _make_cors_app(
    title="vendor_escalation_agent_mcps",
    description="MCP tools for escalating overdue vendor jobs.",
)
vendor_escalation_app.include_router(vendor_escalation_router)
FastApiMCP(
    vendor_escalation_app,
    include_operations=[
        "create_vendor_escalation",
        "get_vendor_escalations",
        "escalate_overdue_jobs",
    ],
).mount_http()
app.mount("/api/v1/vendor_escalation", vendor_escalation_app)


# ── Sub-app: eta_prediction (FULL) ──────────────────────────────────────────

eta_prediction_app = _make_cors_app(
    title="eta_prediction_agent_mcps",
    description="MCP tools for predicting vendor work ETA for a claim.",
)
eta_prediction_app.include_router(eta_prediction_router)
FastApiMCP(
    eta_prediction_app,
    include_operations=[
        "get_eta_prediction",
        "predict_eta",
    ],
).mount_http()
app.mount("/api/v1/eta_prediction", eta_prediction_app)


# ── Health ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "jarvis_vendor_manager_agents_mcp",
        "sub_apps": [
            "vendor_onboarding",
            "vendor_matching",
            "vendor_qualification",
            "vendor_capacity",
            "vendor_cost_benchmark",
            "dispatch",
            "vendor_performance",
            "sla_compliance",
            "vendor_escalation",
            "eta_prediction",
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9100)
