"""
server.py — External Data Agent
───────────────────────────────
LangGraph agent that simulates external weather and drone data
checks for a claim pending real data feed integration.

Port: 8906
MCP : http://localhost:5800/api/v1/external_data/mcp

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
logger = logging.getLogger("external_data_agent")

PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "")
MCP_URL = os.getenv("MCP_URL", "http://localhost:5800/api/v1/external_data/mcp")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8906"))

config_mcp_server = {
    "external_data_mcp": {
        "url": MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    }
}

app = FastAPI(title="External Data Agent")

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
You are the External Data Agent for an insurance claims platform,
assisting a Claims Adjuster with external verification checks.

You have five tools:
- run_external_data_checks    — runs the full pipeline for a claim (call this to generate fresh data)
- get_weather_alignment       — reads the stored weather record for a claim
- get_drone_authenticity      — reads the stored drone authenticity record for a claim
- get_drone_evidence_summary  — reads the stored drone evidence summary for a claim
- get_authority_incident_log  — reads the stored authority time comparison record (fire dept / police)

ROUTING BY LOSS TYPE (handled automatically by the pipeline):
The pipeline reads loss_type_verification_configs from the database to decide
what checks to run — no hardcoding. The result always contains verification_mode:

  verification_mode = "weather"   (e.g. Water Damage, Flood, Storm, Hail)
    → Real Open-Meteo weather fetched + drone simulation
    → No authority time check

  verification_mode = "authority" (e.g. Fire, Fire Damage, Theft, Auto)
    → Weather API skipped (not relevant for this loss type)
    → Drone simulation runs
    → Authority incident log generated: claimant time vs fire dept / police reported time

  verification_mode = "physical"  (e.g. Structural)
    → Weather API skipped, no authority check
    → Drone simulation only

  verification_mode = "generic"   (Unknown or unrecognised loss type)
    → Drone simulation only

WORKFLOW — Running fresh checks:
If the adjuster asks you to run, check, or verify external data for a claim:
1. Call run_external_data_checks with the claim_id.
2. Report based on what the result contains:

   WEATHER section (present for all loss types):
   - If verification_mode = "weather" and real_weather is true:
       Report storm event, ZIP code severity index, drone-weather alignment.
   - If real_weather is false (geocoding failed or date missing):
       Flag this to the adjuster — weather data is defaulted, not real.
   - If zip_code_severity_index = "N/A":
       Report that weather API was not used for this loss type (e.g. Fire).

   DRONE AUTHENTICITY (AI simulated — present for all loss types):
   - Roof condition description, drone match percent, geo match
   - Weather event match, damage inflation index, tamper indicator
   - Compute and state the fraud risk score:
       base = 100 - drone_match_percent
       +20 if tamper_indicator != "None"
       +15 if geo_match == "None", +8 if geo_match == "Partial"
       +15 if damage_inflation_index == "High", +8 if == "Medium"
       +10 if weather_event_match == "No"
       clamp 0–100 → score < 30 = Low Risk, 30–59 = Medium Risk, ≥ 60 = High Risk

   DRONE EVIDENCE SUMMARY (AI simulated):
   - Roof condition rating, scene alignment sentence, manipulation flags, adjuster notes

   AUTHORITY INCIDENT LOG (present only for authority-mode loss types):
   - Authority type (fire_department or police)
   - Authority reported time vs claimant reported time (from FNOL time_of_loss field)
   - Time discrepancy in minutes and discrepancy flag (None / Minor / Significant)
   - Fraud indicator (Low / Medium / High)
   - Note: if claimant_reported_time is null, time_of_loss was not captured in FNOL;
     discrepancy cannot be computed — flag this to the adjuster.

WORKFLOW — Reading existing records:
If the adjuster asks to view or retrieve existing data (without asking to re-run):
- Call get_weather_alignment, get_drone_authenticity, get_drone_evidence_summary,
  or get_authority_incident_log as appropriate.
- Do NOT re-run run_external_data_checks unnecessarily.

WORKFLOW — Claim not found or error:
- If "Claim not found": ask the adjuster to verify the claim ID.
- If "LLM returned unparseable JSON": ask the adjuster to retry.
- If real_weather is false: weather data could not be fetched — flag to adjuster.
- If authority_incident_log is absent: loss type does not require authority check.

When you have completed the task, end your response with "End".
"""


def load_prompt() -> str:
    if not PHOENIX_ENDPOINT:
        raise RuntimeError("Phoenix not configured")
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)
    prompt = client.prompts.get(name="external_data_agent", label="production")
    prompt_set = prompt._template["messages"]
    system_msg = next(
        (item["content"][0]["text"] for item in prompt_set if item.get("role") == "system"),
        None,
    )
    if not system_msg:
        raise ValueError("System prompt is empty or missing in Phoenix")
    return system_msg


def create_graph(model, tools, prompt):
    graph_builder = StateGraph(State)
    llm_with_tools = model.bind_tools(tools)

    async def agent_node(state: State):
        messages = state["messages"]
        all_messages = [SystemMessage(content=prompt)] + messages
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
            tool_name = event.get("name", "unknown_tool")
            yield f"data: [Tool: {tool_name}] Starting...\n\n"

        elif kind == "on_tool_end":
            tool_name = event.get("name", "unknown_tool")
            yield f"data: [Tool: {tool_name}] Done\n\n"


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
    user_message = body.get("message", "Run external data verification for this claim")

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
    return {"status": "healthy", "agent": "external_data_agent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
