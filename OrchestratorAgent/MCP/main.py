"""
main.py
───────
MCP server entry point for the Orchestrator (Brain) Agent platform —
hosts a single agent MCP sub-app on FastAPI (port 9200), backed by the
SQLite database SHARED with PolicyholderAgents
(`PolicyholderAgents/data/policyholder.db`).

Registered sub-apps:
  /api/v1/orchestration   — Orchestration (claim stage state + HITL approvals) [FULL]

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

from orchestration_router import router as orchestration_router

import uvicorn


app = FastAPI(docs_url="/docs", title="Jarvis Orchestrator Agent MCP Server")

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


# ── Sub-app: orchestration (FULL) ───────────────────────────────────────────

orchestration_app = _make_cors_app(
    title="orchestration_agent_mcps",
    description="MCP tools for claim orchestration stage state and human-in-the-loop approval gates.",
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
        "service": "jarvis_orchestrator_agent_mcp",
        "sub_apps": [
            "orchestration",
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9200)
