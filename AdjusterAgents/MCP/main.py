"""
main.py
───────
MCP server entry point for the Adjuster Agents platform — hosts 15 agent
MCP sub-apps on a single FastAPI app (port 8900), backed by the SQLite
database SHARED with PolicyholderAgents
(`PolicyholderAgents/data/policyholder.db`).

Registered sub-apps:
  /api/v1/claim_classification     — Claim Classification              [FULL]
  /api/v1/triage                    — Triage                            [PLACEHOLDER]
  /api/v1/fraud_screening            — Fraud Screening                   [FULL]
  /api/v1/routing                     — Routing                          [PLACEHOLDER]
  /api/v1/evidence_validation          — Evidence Validation              [FULL]
  /api/v1/external_data                 — External Data (Weather/Drone)   [FULL]
  /api/v1/damage_assessment              — Damage Assessment              [FULL]
  /api/v1/verification                    — Verification                  [FULL]
  /api/v1/loss_assessment                  — Loss Assessment              [FULL]
  /api/v1/reserve_recommendation            — Reserve Recommendation       [PLACEHOLDER]
  /api/v1/financial_leakage                  — Financial Leakage           [PLACEHOLDER]
  /api/v1/repair_vs_replacement               — Repair vs Replacement      [FULL]
  /api/v1/settlement_recommendation            — Settlement Recommendation [PLACEHOLDER]
  /api/v1/payment_eligibility                   — Payment Eligibility      [FULL]
  /api/v1/payment_trigger                        — Payment Trigger         [FULL]

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

from claim_classification_router import router as claim_classification_router
from triage_router import router as triage_router
from fraud_screening_router import router as fraud_screening_router
from routing_router import router as routing_router
from evidence_validation_router import router as evidence_validation_router
from external_data_router import router as external_data_router
from damage_assessment_router import router as damage_assessment_router
from verification_router import router as verification_router
from loss_assessment_router import router as loss_assessment_router
from reserve_recommendation_router import router as reserve_recommendation_router
from financial_leakage_router import router as financial_leakage_router
from repair_vs_replacement_router import router as repair_vs_replacement_router
from settlement_recommendation_router import router as settlement_recommendation_router
from payment_eligibility_router import router as payment_eligibility_router
from payment_trigger_router import router as payment_trigger_router
from orchestration_router import router as orchestration_router

import uvicorn


app = FastAPI(docs_url="/docs", title="Jarvis Adjuster Agents MCP Server")

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


# ── Sub-app: claim_classification (FULL) ──────────────────────────────────────

claim_classification_app = _make_cors_app(
    title="claim_classification_agent_mcps",
    description="MCP tools for claim complexity classification and routing recommendations.",
)
claim_classification_app.include_router(claim_classification_router)
FastApiMCP(
    claim_classification_app,
    include_operations=[
        "get_claim_details",
        "classify_claim",
        "save_classification",
        "get_claim_classification",
        "run_intake_validation",
        "compute_stp_score",
        "get_stp_result",
        "get_intake_validation_result",
    ],
).mount_http()
app.mount("/api/v1/claim_classification", claim_classification_app)


# ── Sub-app: triage (PLACEHOLDER) ──────────────────────────────────────────────

triage_app = _make_cors_app(
    title="triage_agent_mcps",
    description="[PLACEHOLDER] MCP tools for claim triage / prioritization.",
)
triage_app.include_router(triage_router)
FastApiMCP(
    triage_app,
    include_operations=["get_claim_triage", "run_triage"],
).mount_http()
app.mount("/api/v1/triage", triage_app)


# ── Sub-app: fraud_screening (FULL) ────────────────────────────────────────────

fraud_screening_app = _make_cors_app(
    title="fraud_screening_agent_mcps",
    description="MCP tools for AI-assisted fraud screening and risk scoring.",
)
fraud_screening_app.include_router(fraud_screening_router)
FastApiMCP(
    fraud_screening_app,
    include_operations=[
        "get_fraud_flags",
        "write_fraud_flag",
        "get_ai_fraud_signals",
        "write_ai_fraud_signal",
        "get_fraud_risk_snapshot",
        "write_fraud_risk_snapshot",
        "run_fraud_screening",
    ],
).mount_http()
app.mount("/api/v1/fraud_screening", fraud_screening_app)


# ── Sub-app: routing (PLACEHOLDER) ─────────────────────────────────────────────

routing_app = _make_cors_app(
    title="routing_agent_mcps",
    description="[PLACEHOLDER] MCP tools for adjuster/team assignment routing.",
)
routing_app.include_router(routing_router)
FastApiMCP(
    routing_app,
    include_operations=["get_auto_assignment_log","assign_claim"],
).mount_http()
app.mount("/api/v1/routing", routing_app)


# ── Sub-app: evidence_validation (FULL) ────────────────────────────────────────

evidence_validation_app = _make_cors_app(
    title="evidence_validation_agent_mcps",
    description="MCP tools for evidence completeness/authenticity validation.",
)
evidence_validation_app.include_router(evidence_validation_router)
FastApiMCP(
    evidence_validation_app,
    include_operations=[
        "get_evidence_items",
        "get_claim_documents",
        "get_damage_items",
        "get_active_fraud_flags",
        "run_evidence_validation",
        "save_validation_result",
    ],
).mount_http()
app.mount("/api/v1/evidence_validation", evidence_validation_app)


# ── Sub-app: external_data (FULL) ──────────────────────────────────────────────

external_data_app = _make_cors_app(
    title="external_data_agent_mcps",
    description="MCP tools for (simulated) external weather and drone data verification.",
)
external_data_app.include_router(external_data_router)
FastApiMCP(
    external_data_app,
    include_operations=[
        "get_weather_alignment",
        "get_drone_authenticity",
        "get_drone_evidence_summary",
        "get_authority_incident_log",
        "run_external_data_checks",
    ],
).mount_http()
app.mount("/api/v1/external_data", external_data_app)


# ── Sub-app: damage_assessment (FULL) ──────────────────────────────────────────

damage_assessment_app = _make_cors_app(
    title="damage_assessment_agent_mcps",
    description="MCP tools for AI-assisted damage item identification and condition assessment.",
)
damage_assessment_app.include_router(damage_assessment_router)
FastApiMCP(
    damage_assessment_app,
    include_operations=[
        "get_claim_details",
        "get_damage_items",
        "write_damage_item",
        "analyze_damage_from_description",
        "get_repair_costs",
        "write_repair_cost",
        "get_replacement_costs",
        "write_replacement_cost",
        "compute_and_save_repair_replacement",
    ],
).mount_http()
app.mount("/api/v1/damage_assessment", damage_assessment_app)


# ── Sub-app: verification (FULL) ───────────────────────────────────────────────

verification_app = _make_cors_app(
    title="verification_agent_mcps",
    description="MCP tools for cross-checking claim facts against policy details.",
)
verification_app.include_router(verification_router)
FastApiMCP(
    verification_app,
    include_operations=[
        "get_external_verifications",
        "create_verification",
        "get_verification_details",
        "write_verification_detail",
        "run_verification",
    ],
).mount_http()
app.mount("/api/v1/verification", verification_app)


# ── Sub-app: loss_assessment (FULL) ────────────────────────────────────────────

loss_assessment_app = _make_cors_app(
    title="loss_assessment_agent_mcps",
    description="MCP tools for estimating total loss, deductible, and net payable.",
)
loss_assessment_app.include_router(loss_assessment_router)
FastApiMCP(
    loss_assessment_app,
    include_operations=[
        "get_loss_assessment",
        "write_loss_assessment",
        "get_loss_estimation",
        "write_loss_estimation",
        "run_loss_assessment",
    ],
).mount_http()
app.mount("/api/v1/loss_assessment", loss_assessment_app)


# ── Sub-app: reserve_recommendation (PLACEHOLDER) ──────────────────────────────

# reserve_recommendation_app = _make_cors_app(
#     title="reserve_recommendation_agent_mcps",
#     description="[PLACEHOLDER] MCP tools for reserve recommendation.",
# )
# reserve_recommendation_app.include_router(reserve_recommendation_router)
# FastApiMCP(
#     reserve_recommendation_app,
#     include_operations=["recommend_reserve", "get_adjuster_findings"],
# ).mount_http()
# app.mount("/api/v1/reserve_recommendation", reserve_recommendation_app)




# ── Sub-app: reserve_recommendation (PLACEHOLDER) ──────────────────────────────

reserve_recommendation_app = _make_cors_app(
    title="reserve_recommendation_agent_mcps",
    description="[PLACEHOLDER] MCP tools for reserve recommendation.",
)
reserve_recommendation_app.include_router(reserve_recommendation_router)
FastApiMCP(
    reserve_recommendation_app,
    include_operations=["recommend_reserve", "get_adjuster_findings"],
).mount_http()
app.mount("/api/v1/reserve_recommendation", reserve_recommendation_app)


# ── Sub-app: financial_leakage (PLACEHOLDER) ───────────────────────────────────

financial_leakage_app = _make_cors_app(
    title="financial_leakage_agent_mcps",
    description="[PLACEHOLDER] MCP tools for financial leakage / overpayment risk scoring.",
)
financial_leakage_app.include_router(financial_leakage_router)
FastApiMCP(
    financial_leakage_app,
    include_operations=["get_cost_variance", "score_leakage"],
).mount_http()
app.mount("/api/v1/financial_leakage", financial_leakage_app)


# ── Sub-app: repair_vs_replacement (FULL) ──────────────────────────────────────

repair_vs_replacement_app = _make_cors_app(
    title="repair_vs_replacement_agent_mcps",
    description="MCP tools for repair-vs-replacement cost comparison and recommendations.",
)
repair_vs_replacement_app.include_router(repair_vs_replacement_router)
FastApiMCP(
    repair_vs_replacement_app,
    include_operations=[
        # "get_estimates",
        # "write_estimate",
        # "get_repair_cost_detail",
        # "write_repair_cost",
        # "get_replacement_cost_detail",
        # "write_replacement_cost",
        # "compare_repair_vs_replace",




        # "get_estimates",
        # "write_estimate",
        # "get_repair_cost_detail",
        # "write_repair_cost",
        # "get_replacement_cost_detail",
        # "write_replacement_cost",
        "compare_repair_vs_replace",
        "write_repair_vs_replacement_decision",
        "update_repair_vs_replacement_decision",
    ],
).mount_http()
app.mount("/api/v1/repair_vs_replacement", repair_vs_replacement_app)


# ── Sub-app: settlement_recommendation (PLACEHOLDER) ───────────────────────────

# settlement_recommendation_app = _make_cors_app(
#     title="settlement_recommendation_agent_mcps",
#     description="[PLACEHOLDER] MCP tools for settlement amount recommendation.",
# )
# settlement_recommendation_app.include_router(settlement_recommendation_router)
# FastApiMCP(
#     settlement_recommendation_app,
#     include_operations=["recommend_settlement", "get_ai_decision_recommendation"],
# ).mount_http()
# app.mount("/api/v1/settlement_recommendation", settlement_recommendation_app)




# ── Sub-app: settlement_recommendation (PLACEHOLDER) ───────────────────────────

settlement_recommendation_app = _make_cors_app(
    title="settlement_recommendation_agent_mcps",
    description="[PLACEHOLDER] MCP tools for settlement amount recommendation.",
)
settlement_recommendation_app.include_router(settlement_recommendation_router)
FastApiMCP(
    settlement_recommendation_app,
    include_operations=["recommend_settlement", "get_ai_decision_recommendation"],
).mount_http()
app.mount("/api/v1/settlement_recommendation", settlement_recommendation_app)


# ── Sub-app: payment_eligibility (FULL) ────────────────────────────────────────

payment_eligibility_app = _make_cors_app(
    title="payment_eligibility_agent_mcps",
    description="MCP tools for auto-adjudication eligibility gating across 9 gates.",
)
payment_eligibility_app.include_router(payment_eligibility_router)
FastApiMCP(
    payment_eligibility_app,
    include_operations=[
        "get_auto_adjudication_thresholds",
        "check_eligibility",
        "get_auto_adjudication_record",
        "confirm_payment_approval",
    ],
).mount_http()
app.mount("/api/v1/payment_eligibility", payment_eligibility_app)


# ── Sub-app: payment_trigger (FULL) ────────────────────────────────────────────

payment_trigger_app = _make_cors_app(
    title="payment_trigger_agent_mcps",
    description="MCP tools for checking claim approval and triggering payment disbursements.",
)
payment_trigger_app.include_router(payment_trigger_router)
FastApiMCP(
    payment_trigger_app,
    include_operations=[
        "get_payment_eligibility",
        "check_claim_approved",
        "create_payment_disbursement",
        "update_payment_status",
        "get_payment_disbursements",
    ],
).mount_http()
app.mount("/api/v1/payment_trigger", payment_trigger_app)


# ── Sub-app: orchestration (HITL approval gates, local copy) ──────────────────
# Adjuster-local copy of OrchestratorAgent/MCP's orchestration sub-app — same
# tables (human_approval_requests, claim_orchestration_state), same tool names.
# Lets AdjusterOrchestrator (and claims-solution-integration) open/check HITL
# gates without OrchestratorAgent's process needing to be running at all.

orchestration_app = _make_cors_app(
    title="orchestration_agent_mcps",
    description="MCP tools for HITL approval gates and per-claim stage tracking (Adjuster-local copy).",
)
orchestration_app.include_router(orchestration_router)
FastApiMCP(
    orchestration_app,
    include_operations=[
        "get_claim_orchestration_state",
        "set_claim_orchestration_state",
        "create_approval_request",
        "get_pending_approvals",
        "decide_approval",
        "get_approval_status",
    ],
).mount_http()
app.mount("/api/v1/orchestration", orchestration_app)


# ── Health ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "jarvis_adjuster_agents_mcp",
        "sub_apps": [
            "claim_classification",
            "triage",
            "fraud_screening",
            "routing",
            "evidence_validation",
            "external_data",
            "damage_assessment",
            "verification",
            "loss_assessment",
            "reserve_recommendation",
            "financial_leakage",
            "repair_vs_replacement",
            "settlement_recommendation",
            "payment_eligibility",
            "payment_trigger",
            "orchestration",
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5800)
