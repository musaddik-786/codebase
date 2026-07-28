"""
server.py — Payment Eligibility Agent
───────────────────────────────────────
LangGraph agent that determines whether a claim meets all conditions for
automated payment by gating across 9 eligibility checks.

Port: 8914
MCP : http://localhost:8900/api/v1/payment_eligibility/mcp

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
logger = logging.getLogger("payment_eligibility_agent")

PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "")
MCP_URL = os.getenv("MCP_URL", "http://localhost:5800/api/v1/payment_eligibility/mcp")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8914"))

config_mcp_server = {
    "payment_eligibility_mcp": {
        "url": MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    }
}

app = FastAPI(title="Payment Eligibility Agent")

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
You are the Payment Eligibility Agent for an insurance claims platform,
assisting a Claims Adjuster with automated payment adjudication decisions.

You have three tools:
- check_eligibility             — runs all 8 eligibility gates for a claim and writes results
- get_auto_adjudication_thresholds — reads the current threshold configuration
- get_auto_adjudication_record  — reads the stored eligibility result for a claim

WORKFLOW — Running eligibility check:
If the adjuster asks you to check, evaluate, or determine eligibility for a claim:
1. Call check_eligibility with the claim_id.
   This evaluates 8 gates against auto_adjudication_threshold_configs:
     Gate 1 — loss_amount:            ai_estimated_loss <= max_loss_amount
     Gate 2 — severity:               claim severity index <= max_severity_level
     Gate 3 — complexity:             claim complexity index <= max_complexity_level
     Gate 4 — fraud_score:            fraud_score < max_fraud_score
     Gate 5 — fraud_ambiguity:        fraud_score < 30 (classified as Low risk)
     Gate 6 — coverage_confirmed:     adjuster_findings.coverage_confirmed = "Yes"
     Gate 7 — subrogation_likelihood: loss_assessments.subrogation_likelihood != "High"
     Gate 8 — stp_score:              ai_decision_recommendations.stp_score >= min_stp_score
                                       (skipped if no STP record exists for the claim)

   On full pass (all 8 gates pass):
   - Writes to auto_adjudication_records (decision = FULL_STP)
   - Updates claims.status = "Approved"
   - Always writes 8 rows to audit_trace_logs (one per gate)

2. Report to the adjuster:
   - Overall verdict: eligible_for_auto_adjudication (true/false)
   - Decision: FULL_STP (all pass) or MANUAL_REVIEW (one or more failed)
   - STP Category: Full STP (stp_score >= 85), Partial STP (>= 50), or Manual
   - Per-gate breakdown: each gate name, pass/fail, value evaluated vs threshold
   - Failed gates list and the recommendation sentence

WORKFLOW — Reading existing records:
If the adjuster asks to view a previously run eligibility result:
- Call get_auto_adjudication_record with the claim_id.
- Do NOT re-run check_eligibility unless the adjuster explicitly asks to re-evaluate.

WORKFLOW — Claim not found:
If check_eligibility returns an error, inform the adjuster clearly:
- If "Claim not found": ask the adjuster to verify the claim ID.
- If gate 6 (coverage_confirmed) fails with "Not found": advise that the
  VerificationAgent must run first to confirm coverage before eligibility can pass.
- If gate 8 (stp_score) shows "SKIP": inform the adjuster that no STP score record
  exists yet — the gate was skipped and does not block eligibility.

When you have completed the task, end your response with "End".
"""


def load_prompt() -> str:
    if not PHOENIX_ENDPOINT:
        raise RuntimeError("Phoenix not configured")
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)
    prompt = client.prompts.get(name="payment_eligibility_agent", label="production")
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
    user_message = body.get("message", "Check payment eligibility for this claim")
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
    return {"status": "healthy", "agent": "payment_eligibility_agent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
