"""
server.py — Triage Agent
─────────────────────────
LangGraph agent that prioritizes claims by urgency/severity/SLA risk and
recommends routing decisions.

Port: 8902
MCP : http://localhost:8900/api/v1/triage/mcp

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
logger = logging.getLogger("triage_agent")

PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "")
MCP_URL = os.getenv("MCP_URL", "http://localhost:8900/api/v1/triage/mcp")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8902"))

config_mcp_server = {
    "triage_mcp": {
        "url": MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    }
}

app = FastAPI(title="Triage Agent")

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
    # Only route to tools when there are actual tool_calls — string matching on
    # "Continue"/"End" is unreliable if the LLM uses those words in normal text.
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "End"


_FALLBACK_PROMPT = """
You are the Triage Agent for an insurance claims platform, assisting a Claims Adjuster.

Given a claim_id, your workflow is:

1. Call the tool named "run_triage" exactly (use that exact name) with the claim_id.
   This will:
   - Compute a composite priority score from severity, complexity, fraud risk, and claim age.
   - Determine the SLA risk level (Low/Medium/High/Critical).
   - Produce a routing recommendation and write the result to claim_triage.

2. Summarize for the adjuster using the tool output exactly — do not infer or rephrase scores:
   - The priority score and its breakdown (severity_pts, complexity_pts, fraud_pts, age_pts).
   - The SLA risk level.
   - The routing recommendation and rationale.
   - If fraud data was missing, mention that fraud risk was treated as uncertain.

When you have completed the task, end your response with "End".
"""


def load_prompt() -> str:
    if not PHOENIX_ENDPOINT:
        raise RuntimeError("Phoenix not configured")
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)
    prompt = client.prompts.get(name="triage_agent", label="production")
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
    user_message = body.get("message", "Run triage for this claim")
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
    return {"status": "healthy", "agent": "triage_agent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
