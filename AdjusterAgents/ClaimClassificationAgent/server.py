"""
server.py — Claim Classification Agent
──────────────────────────────────────────
LangGraph agent that classifies a claim's complexity and recommends a
routing track (Fast Track / Standard / Specialist Review) for an adjuster.

Port: 8901
MCP : http://localhost:8900/api/v1/claim_classification/mcp

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
logger = logging.getLogger("claim_classification_agent")

PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "")
MCP_URL = os.getenv("MCP_URL", "http://localhost:8900/api/v1/claim_classification/mcp")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8901"))

config_mcp_server = {
    "claim_classification_mcp": {
        "url": MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    }
}

app = FastAPI(title="Claim Classification Agent")

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
You are the Claim Classification Agent for an insurance claims platform,
assisting a Claims Adjuster.

Given a claim_number, your full workflow is:

STEP 1 — Fetch claim data
  Call get_claim_details to retrieve the claim record.

STEP 2 — Intake validation
  Call run_intake_validation. This checks 7 mandatory FNOL fields:
    policy_number, policyholder_name, loss_type, short_description,
    location, date_of_loss, severity.
  - completeness_score = (filled / 7) × 100
  - passed = score ≥ 85 AND no blocking failure
  - Blocking failures: missing short_description, missing location,
    coverage_amount = 0.
  - Result is saved to intake_validation_result_output.
  - If validation fails (passed=false), inform the adjuster of blocking
    issues before proceeding.

STEP 3 — Deterministic complexity classification
  Call classify_claim. Rules (no LLM):
  - Complexity from estimated_cost vs auto_adjudication_threshold_configs:
      Simple: ≤ simple_threshold (default $5,000)
      Moderate: ≤ moderate_threshold (default $25,000)
      Complex: > $25,000 or severity = Critical/High
  - CRITICAL: If classify_claim returns HTTP 422 with
    "fraud_score_unavailable", fraud screening has NOT been run.
    Do NOT proceed. Missing fraud data is NEVER treated as score 0.
  - If fraud_score ≥ 70 → always Complex + Specialist Review.
  - Save the result by calling save_classification with the returned
    complexity and routing values.

STEP 4 — STP score computation
  Call compute_stp_score. This computes an 8-factor weighted score:
    fnolCompleteness×20%, readiness×15%, coverage×15%, severity×10%,
    fraudAmbiguity×10%, subrogationRisk×10%, VIS×15%, similarityIndex×5%
  STP categories:
    ≥ 85 + Low fraud + Low subrogation → Full STP → Fast Track
    ≥ 70                               → Vendor STP → Standard
    ≥ 50                               → Fast Track STP → Standard
    < 50 OR High/Critical severity     → Manual → Specialist Review
  Results saved to: stp_score_input_factors, stp_calculation_result,
  segmentation_result_output.
  Returns 422 if fraud score unavailable — same rule applies.

STEP 5 — Review and report
  Call get_claim_classification and get_stp_result to confirm persisted data.
  Report to the adjuster:
    - Intake validation result (completeness %, any blocking issues)
    - Complexity level and cost threshold used
    - Fraud score from DB and its impact on routing
    - STP score, category, and recommended processing path

When all steps are complete, end your response with "End".
"""


def load_prompt() -> str:
    if not PHOENIX_ENDPOINT:
        raise RuntimeError("Phoenix not configured")
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)
    prompt = client.prompts.get(name="claim_classification_agent", label="production")
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
    user_message = body.get("message", "Classify this claim")

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
    return {"status": "healthy", "agent": "claim_classification_agent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
