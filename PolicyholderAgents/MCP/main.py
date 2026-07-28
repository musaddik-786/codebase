"""
main.py
───────
MCP server entry point for the Policyholder Agents platform — hosts 9
agent MCP sub-apps on a single FastAPI app (port 7720), backed by a local
SQLite database.

Registered sub-apps:
  /api/v1/voice_text_intake   — Voice/Text Intake (FNOL)              [FULL]
  /api/v1/duplicate_check     — Duplicate Claim Check                  [FULL]
  /api/v1/segmentation         — Claim Segmentation / STP              [FULL]
  /api/v1/claim_status          — Claim Status ("Follow My Claim")      [FULL]
  /api/v1/document_submission   — Document Submission & Classification [FULL]
  /api/v1/feedback               — Feedback / Sentiment Tracking         [FULL]
  /api/v1/policy_coverage         — Policy Coverage Verification        [PLACEHOLDER]
  /api/v1/claim_readiness          — Claim Readiness                     [PLACEHOLDER]
  /api/v1/communication             — Communication                       [PLACEHOLDER]

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

from voice_text_intake_router import router as voice_text_intake_router
from duplicate_check_router import router as duplicate_check_router
from segmentation_router import router as segmentation_router
from claim_status_router import router as claim_status_router
from document_submission_router import router as document_submission_router
from feedback_router import router as feedback_router
from policy_coverage_router import router as policy_coverage_router
from claim_readiness_router import router as claim_readiness_router
from communication_router import router as communication_router

import uvicorn


app = FastAPI(docs_url="/docs", title="Jarvis Policyholder Agents MCP Server")

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


# ── Sub-app: voice_text_intake (FULL) ─────────────────────────────────────────

voice_intake_app = _make_cors_app(
    title="voice_text_intake_agent_mcps",
    description="MCP tools for FNOL Voice/Text Intake: field extraction, "
                 "submission management, and audit logging.",
)
voice_intake_app.include_router(voice_text_intake_router)
FastApiMCP(
    voice_intake_app,
    include_operations=[
        "create_fnol_submission",
        "get_fnol_submission",
        "get_fnol_by_policy",
        "update_fnol_submission",
        "submit_fnol",
        "get_mandatory_fields",
        "save_voice_text_extraction",
        "get_voice_text_extractions",
        "save_ai_inferences",
        "log_question_answer",
        "get_question_log",
        "save_field_attribution",
        "extract_fnol_fields_from_text",
        "cleanup_draft_fnols",
    ],
).mount_http()
app.mount("/api/v1/voice_text_intake", voice_intake_app)


# ── Sub-app: duplicate_check (FULL) ───────────────────────────────────────────

duplicate_check_app = _make_cors_app(
    title="duplicate_claim_check_agent_mcps",
    description="MCP tools for checking duplicate FNOL/claim submissions.",
)
duplicate_check_app.include_router(duplicate_check_router)
FastApiMCP(
    duplicate_check_app,
    include_operations=[
        "check_duplicate_claim",
        "get_recent_claims_for_policy",
    ],
).mount_http()
app.mount("/api/v1/duplicate_check", duplicate_check_app)


# ── Sub-app: segmentation (FULL) ──────────────────────────────────────────────

segmentation_app = _make_cors_app(
    title="claim_segmentation_agent_mcps",
    description="MCP tools for STP scoring and claim segmentation.",
)
segmentation_app.include_router(segmentation_router)
FastApiMCP(
    segmentation_app,
    include_operations=[
        "get_claim_for_segmentation",
        "compute_stp_score",
        "get_segmentation_result",
        "get_stp_classification",
    ],
).mount_http()
app.mount("/api/v1/segmentation", segmentation_app)


# ── Sub-app: claim_status (FULL) ──────────────────────────────────────────────

claim_status_app = _make_cors_app(
    title="claim_status_agent_mcps",
    description="MCP tools for claim journey tracking ('Follow My Claim').",
)
claim_status_app.include_router(claim_status_router)
FastApiMCP(
    claim_status_app,
    include_operations=[
        "get_claim_journey",
        "get_claim_status_summary",
        "log_policyholder_action",
        "get_policyholder_actions",
    ],
).mount_http()
app.mount("/api/v1/claim_status", claim_status_app)


# ── Sub-app: document_submission (FULL) ───────────────────────────────────────

document_submission_app = _make_cors_app(
    title="document_submission_agent_mcps",
    description="MCP tools for uploading, categorising, and validating claim evidence files.",
)
document_submission_app.include_router(document_submission_router)
FastApiMCP(
    document_submission_app,
    include_operations=[
        "upload_document",
        "validate_document",
        "get_claim_documents",
        "get_document",
    ],
).mount_http()
app.mount("/api/v1/document_submission", document_submission_app)


# ── Sub-app: feedback (FULL) ───────────────────────────────────────────────────

feedback_app = _make_cors_app(
    title="feedback_agent_mcps",
    description="MCP tools for policyholder feedback and sentiment tracking.",
)
feedback_app.include_router(feedback_router)
FastApiMCP(
    feedback_app,
    include_operations=[
        "write_customer_feedback",
        "get_customer_feedback",
        "update_sentiment_tracker",
        "get_sentiment_tracker",
    ],
).mount_http()
app.mount("/api/v1/feedback", feedback_app)


# ── Sub-app: policy_coverage (PLACEHOLDER) ────────────────────────────────────

# policy_coverage_app = _make_cors_app(
#     title="policy_coverage_agent_mcps",
#     description="[PLACEHOLDER] MCP tools for local policy coverage verification.",
# )
# policy_coverage_app.include_router(policy_coverage_router)
# FastApiMCP(
#     policy_coverage_app,
#     include_operations=["get_policy_details_stub"],
# ).mount_http()
# app.mount("/api/v1/policy_coverage", policy_coverage_app)





policy_coverage_app = _make_cors_app(
    title="policy_coverage_agent_mcps",
    description="MCP tools for Guidewire policy lookup, coverage verification, and payment tracking.",
)
policy_coverage_app.include_router(policy_coverage_router)
FastApiMCP(
    policy_coverage_app,
    include_operations=[
        "gw_search_policy",
        "gw_get_policy_coverages",
        "save_policy_details",
        "get_policy_details",
        "get_coverage_verification_result",
        "verify_coverage",
        "record_claim_payment",
        "get_claim_details",
    ],
).mount_http()
app.mount("/api/v1/policy_coverage", policy_coverage_app)



# ── Sub-app: claim_readiness (PLACEHOLDER) ────────────────────────────────────

claim_readiness_app = _make_cors_app(
    title="claim_readiness_agent_mcps",
    description="MCP tools for validating FNOL field completeness, document presence, and initial fraud pre-screen.",
)
claim_readiness_app.include_router(claim_readiness_router)
FastApiMCP(
    claim_readiness_app,
    include_operations=[
        "score_claim_readiness",
        "acknowledge_missing_docs",
        "get_intake_validation_result",
    ],
).mount_http()
app.mount("/api/v1/claim_readiness", claim_readiness_app)


# ── Sub-app: communication (PLACEHOLDER) ──────────────────────────────────────

# communication_app = _make_cors_app(
#     title="communication_agent_mcps",
#     description="[PLACEHOLDER] MCP tools for policyholder communication history.",
# )
# communication_app.include_router(communication_router)
# FastApiMCP(
#     communication_app,
#     include_operations=["get_communication_history_stub"],
# ).mount_http()
# app.mount("/api/v1/communication", communication_app)



communication_app = _make_cors_app(
    title="communication_agent_mcps",
    description="[PLACEHOLDER] MCP tools for policyholder communication history.",
)
communication_app.include_router(communication_router)
FastApiMCP(
    communication_app,
    include_operations=["get_communication_history", "log_inbound_communication", "draft_status_notification"],
).mount_http()
app.mount("/api/v1/communication", communication_app)


# ── Health ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "jarvis_policyholder_agents_mcp",
        "sub_apps": [
            "voice_text_intake",
            "duplicate_check",
            "segmentation",
            "claim_status",
            "document_submission",
            "feedback",
            "policy_coverage",
            "claim_readiness",
            "communication",
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7720)
