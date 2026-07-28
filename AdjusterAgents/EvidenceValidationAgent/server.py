"""
server.py — Evidence Validation Agent
───────────────────────────────────────
LangGraph agent that verifies evidence authenticity and completeness for a
claim, flagging missing required types and suspicious items.

Port: 8905
MCP : http://localhost:8900/api/v1/evidence_validation/mcp

Run:
    py -3 server.py
"""

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Annotated, TypedDict

import uvicorn
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai.chat_models import AzureChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv(find_dotenv())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger("evidence_validation_agent")

PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "")
MCP_URL = os.getenv("MCP_URL", "http://localhost:8900/api/v1/evidence_validation/mcp")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8905"))

config_mcp_server = {
    "evidence_validation_mcp": {
        "url": MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    }
}

app = FastAPI(title="Evidence Validation Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def router(state: State):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    if isinstance(last, AIMessage) and last.content:
        if "Continue" in last.content:
            return "tools"
        if "End" in last.content:
            return "End"
    return "End"


_FALLBACK_PROMPT = """
You are the Evidence Validation Agent for an insurance claims platform,
assisting a Claims Adjuster.

IMPORTANT — TOOL SELECTION RULES:
  • When the user asks about "fraud flags", "active flags", or "what flags exist":
    → Call get_active_fraud_flags. This reads the fraud_flags table directly and
      returns records with flag_type, flag_description, risk_score, detected_by,
      and flagged_at. These are adjuster-recorded fraud flag records.
  • When the user asks to validate evidence, check completeness, or run a full
    evidence review:
    → Call run_evidence_validation. This generates drone/weather/image authenticity
      findings — these are ANALYSIS OUTPUTS, not fraud_flags records.
  • Never present drone findings, weather warnings, or image authenticity results
    as fraud_flags records. They are distinct categories.

Given a claim_id for a full validation workflow, run all steps below.
For a targeted question (e.g. "show fraud flags"), call only the relevant tool.

STEP 1 — Gather all evidence data
  Call get_evidence_items — all submitted evidence items for the claim.
  Call get_claim_documents — uploaded documents from the shared documents table.
  Call get_damage_items — damage items for cross-referencing.

STEP 2 — Retrieve fraud flag records  ← NEW
  Call get_active_fraud_flags with the claim_id.
  Returns actual fraud_flags table records (status = 'Active') including:
    - flag_type, flag_description, risk_score, detected_by, flagged_at
  Report these as "Fraud Flags (from fraud_flags table)" — NOT as validation findings.

STEP 3 — Run evidence validation
  Call run_evidence_validation with the claim_id. This tool:

  COMPLETENESS CHECK
  - Required evidence types per loss_type:
      Water Damage → photos, repair_estimate, plumber_report
      Fire         → photos, fire_report, repair_estimate
      Storm        → photos, weather_report, repair_estimate
      Theft/Other  → photos, police_report
  - completeness_percent = (matched / required) × 100

  FRAUD SIGNAL AGGREGATION (DB-driven, NOT LLM)
  - Reads fraud_risk_snapshots, fraud_flags, ai_fraud_signals counts only.
  - "Suspicious" status requires: fraud_score ≥ 70 OR ≥ 2 active flags.
    Never set based on filenames.

  DRONE AUTHENTICITY SIGNALS
  - Reads drone_authenticity_data for the claim.
  - drone_fraud_score = 100 - droneMatchPercent
      + 20 if tampering_detected is not null
      + 15 if geo_match is null (missing), +8 if Partial
      + 15 if inflation_detected = High, +8 if Medium
      + 10 if weather_match = No
    Clamped to 0-100.
  - Red flags (added automatically):
      droneMatch < 60% → "Drone imagery match below threshold"
      tampering detected → "Image tampering detected in drone data"
      geo_match = null → "Drone location data unavailable"
  - Amber flags:
      geo_match = Partial → "Partial GPS match in drone data"
      weather_match = No → "Weather conditions do not match drone data"

  WEATHER ALIGNMENT
  - Reads weather_location_alignment for secondary signal confirmation.

  EFFECTIVE FRAUD SCORE = max(db_fraud_score, drone_fraud_score)
  - ≥ 70 → Suspicious
  - ≥ 40 → Under Review
  - else → Verified (if complete) or Incomplete

  Does NOT write to the database.

STEP 4 — Save validation result
  Call save_validation_result with claim_id, overall_status, and
  authenticity_flags from Step 3.
  - Any flag with an evidence_id not found in the DB is automatically
    discarded (prevents evidence ID hallucination).
  - Matched flags update evidence_items.status to "Flagged" or "Verified".

STEP 5 — Report to adjuster
  Present results in clearly separated sections:

  FRAUD FLAGS (from fraud_flags table — get_active_fraud_flags):
  - List each active flag with: flag_type, flag_description, risk_score,
    detected_by, flagged_at.
  - If none: "No active fraud flags recorded for this claim."

  EVIDENCE VALIDATION FINDINGS (from run_evidence_validation):
  - Completeness % and missing evidence types.
  - DB fraud signals: score, active flags count, AI signals count.
  - Drone fraud score and drone-specific flags raised.
  - Weather alignment result.
  - Image authenticity results (images analyzed, flagged, risk level).
  - Effective fraud score, overall status, and recommendation.

  Never mix fraud_flags records with drone/weather/image findings.

When all steps are complete, end your response with "End".
"""


def load_prompt() -> str:
    if not PHOENIX_ENDPOINT:
        raise RuntimeError("Phoenix not configured")
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)
    prompt = client.prompts.get(name="evidence_validation_agent", label="production")
    prompt_set = prompt._template["messages"]
    system_msg = next(
        (item["content"][0]["text"] for item in prompt_set if item.get("role") == "system"), None
    )
    if not system_msg:
        raise ValueError("System prompt is empty or missing in Phoenix")
    return system_msg


def create_graph(model, tools, prompt):
    graph_builder = StateGraph(State)
    llm_with_tools = model.bind_tools(tools)

    async def agent_node(state: State):
        all_messages = [SystemMessage(content=prompt)] + state["messages"]
        message = await llm_with_tools.ainvoke(all_messages)
        return {"messages": [message]}

    graph_builder.add_node("agent", agent_node)
    graph_builder.add_node("tools", ToolNode(tools=tools))
    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges("agent", router, {"tools": "tools", "End": END})
    graph_builder.add_edge("tools", "agent")
    return graph_builder.compile()


async def get_tools():
    client = MultiServerMCPClient(config_mcp_server)
    tools = await client.get_tools()
    logger.info("Tools loaded from MCP: %s", [t.name for t in tools])
    return tools


async def stream_graph(graph, initial_state, config):
    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        kind = event.get("event", "")
        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield f"data: {chunk.content}\n\n"
        elif kind == "on_tool_start":
            yield f"data: [Tool: {event.get('name', 'unknown_tool')}] Starting...\n\n"
        elif kind == "on_tool_end":
            yield f"data: [Tool: {event.get('name', 'unknown_tool')}] Done\n\n"


@app.post("/chat")
async def chat_stream(request: Request):
    load_dotenv(find_dotenv())
    tools = await get_tools()

    model = AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

    try:
        system_prompt = load_prompt()
    except Exception as e:
        logger.warning("Phoenix prompt load failed (%s) — using fallback prompt", e)
        system_prompt = _FALLBACK_PROMPT

    body = await request.json()
    user_message = body.get("message", "Validate evidence for this claim")
    graph = create_graph(model=model, tools=tools, prompt=system_prompt)

    async def generate():
        start = time.time()
        last_event_at = start
        last_tool = None
        try:
            async for event in stream_graph(
                graph=graph,
                initial_state={"messages": [user_message]},
                config={"recursion_limit": 250},
            ):
                last_event_at = time.time()
                if isinstance(event, str) and event.startswith("data: [Tool:"):
                    try:
                        last_tool = event.split("[Tool:", 1)[1].split("]", 1)[0]
                    except Exception:
                        pass
                yield event
        except BaseException as e:
            elapsed = time.time() - start
            since_last = time.time() - last_event_at
            err = {
                "exception_class": type(e).__name__,
                "message": str(e),
                "elapsed_total_seconds": round(elapsed, 2),
                "seconds_since_last_event": round(since_last, 2),
                "last_tool_invoked": last_tool,
                "traceback": traceback.format_exc(),
                "timestamp_utc": datetime.utcnow().isoformat(),
            }
            logger.error("AGENT_ERROR %s", json.dumps(err, default=str))
            try:
                yield f"data: [AGENT_ERROR] {json.dumps(err, default=str)}\n\n"
            except Exception:
                pass
            import asyncio
            if isinstance(e, asyncio.CancelledError):
                raise

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "evidence_validation_agent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
