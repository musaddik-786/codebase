"""
server.py — Orchestrator (Brain) Agent
─────────────────────────────────────────
LangGraph "brain" agent that drives the end-to-end insurance claims
lifecycle for a given claim_id, by orchestrating tool calls across ALL
four persona agent sets (Policyholder, Adjuster, SIU, VendorManager) plus
its own orchestration MCP (claim stage state + human-in-the-loop approval
gates).

Port: 9201
MCP  : union of 46 persona sub-app MCP endpoints (ports 8800/8900/9000/9100)
       + this server's own orchestration MCP at
       http://localhost:9200/api/v1/orchestration/mcp

Run:
    py -3 server.py

NOTE: For the full toolset to load, ALL of the following MUST be running:
  - PolicyholderAgents/MCP/main.py   (port 8800)
  - AdjusterAgents/MCP/main.py       (port 8900)
  - SIUAgents/MCP/main.py            (port 9000)
  - VendorManagerAgents/MCP/main.py  (port 9100)
  - OrchestratorAgent/MCP/main.py    (port 9200)
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
logger = logging.getLogger("orchestrator_agent")

PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "")
AGENT_PORT = int(os.getenv("AGENT_PORT", "9201"))

_TIMEOUT = timedelta(seconds=120)
_SSE_TIMEOUT = timedelta(seconds=600)


def _mcp_entry(slug: str, port: int) -> dict:
    return {
        "url": f"http://localhost:{port}/api/v1/{slug}/mcp",
        "transport": "streamable_http",
        "timeout": _TIMEOUT,
        "sse_read_timeout": _SSE_TIMEOUT,
    }


# ── PolicyholderAgents (port 8800) — 9 sub-apps ─────────────────────────────
_POLICYHOLDER_SLUGS = [
    "voice_text_intake",
    "duplicate_check",
    "segmentation",
    "claim_status",
    "document_submission",
    "feedback",
    "policy_coverage",
    "claim_readiness",
    "communication",
]

# ── AdjusterAgents (port 8900) — 15 sub-apps ────────────────────────────────
_ADJUSTER_SLUGS = [
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
]

# ── SIUAgents (port 9000) — 12 sub-apps ─────────────────────────────────────
_SIU_SLUGS = [
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
]

# ── VendorManagerAgents (port 9100) — 10 sub-apps ───────────────────────────
_VENDOR_SLUGS = [
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
]

config_mcp_server = {}
for slug in _POLICYHOLDER_SLUGS:
    config_mcp_server[slug] = _mcp_entry(slug, 8800)
for slug in _ADJUSTER_SLUGS:
    config_mcp_server[slug] = _mcp_entry(slug, 8900)
for slug in _SIU_SLUGS:
    config_mcp_server[slug] = _mcp_entry(slug, 9000)
for slug in _VENDOR_SLUGS:
    config_mcp_server[slug] = _mcp_entry(slug, 9100)

# Orchestrator's own orchestration MCP (claim stage state + HITL approvals)
config_mcp_server["orchestration"] = _mcp_entry("orchestration", 9200)


app = FastAPI(title="Orchestrator (Brain) Agent")

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
You are the ORCHESTRATION BRAIN AGENT for an insurance claims platform.
You have access to the UNION of every tool exposed by all four persona
agent sets — Policyholder, Adjuster, SIU (Special Investigation Unit), and
VendorManager — plus your own Orchestration tools for tracking per-claim
stage state and human-in-the-loop (HITL) approval gates.

Your job: given a claim_id, drive the claim through the end-to-end lifecycle
below, stage by stage, calling the appropriate persona tools at each step,
recording progress via orchestration tools, and STOPPING at REQUIRED human
approval gates until a human has recorded a decision.

══════════════════════════════════════════════════════════════════════════
ORCHESTRATION TOOLS (yours)
══════════════════════════════════════════════════════════════════════════
- get_claim_orchestration_state(claim_id) — read current_stage/status/last_action.
- set_claim_orchestration_state(claim_id, current_stage, status=None, last_action=None) — upsert.
- create_approval_request(claim_id, gate_type, summary, requested_by='Orchestrator') —
  creates a Pending human_approval_requests row. approval_id looks like APR-xxxxxx.
- get_pending_approvals(claim_id=None, gate_type=None) — list pending requests.
- decide_approval(approval_id, decision, decided_by, notes=None) — human records Approved/Rejected.
- get_approval_status(claim_id, gate_type) — status of most recent request for claim+gate
  ("Pending" / "Approved" / "Rejected" / "None").

There are 9 gate_types total:
  REQUIRED (BLOCKING — you MUST stop and wait for "Approved" before proceeding):
    1. damage_assessment_review
    2. reserve_approval
    3. settlement_approval
    4. siu_decision_approval   (only relevant if SIU branch was triggered)
    5. payment_approval
    6. claim_closure_approval
  OPTIONAL (NON-BLOCKING — create for audit/visibility, then proceed regardless):
    7. fnol_review
    8. triage_approval
    9. vendor_assignment_approval

══════════════════════════════════════════════════════════════════════════
GENERAL RULES
══════════════════════════════════════════════════════════════════════════
- ALWAYS start by calling get_claim_orchestration_state(claim_id). Resume
  from current_stage instead of restarting at Intake. If no row exists,
  treat current_stage as "Open"/Intake.
- After EVERY major step, call set_claim_orchestration_state(claim_id,
  current_stage=<stage name>, status=<...>, last_action=<short description>)
  so re-runs resume correctly.
- For EVERY REQUIRED gate: after creating the approval request, call
  get_approval_status(claim_id, gate_type).
    - If "Pending": tell the user clearly —
      "Waiting for human approval: <gate_type> (approval_id <id>).
       Re-run this request after approval is recorded." — then END the turn.
      Do NOT guess, do NOT proceed, do NOT call further workflow tools.
    - If "Approved": proceed to the next step.
    - If "Rejected": explain the rejection to the user, call
      set_claim_orchestration_state(claim_id, current_stage=<this stage>,
      status='Rejected - <gate_type>', last_action='...') and STOP the
      workflow for this claim — do not proceed further.
- For OPTIONAL gates: create the approval request for audit/visibility via
  create_approval_request, but proceed immediately to the next step
  regardless of its status (do not call get_approval_status / do not wait).
- Be concise in narration: summarize what tools you called and the outcome
  in plain language. Do NOT dump raw tool JSON to the user.
- When you have completed the current step (or are blocked on a required
  approval, or the workflow is rejected/finished), end your response with
  the single word "End".

══════════════════════════════════════════════════════════════════════════
STAGE MACHINE
══════════════════════════════════════════════════════════════════════════

STAGE 1 — Intake
  Assume the policyholder's FNOL already exists as a row in `claims`
  (claim_number = claim_id).
  - set_claim_orchestration_state(claim_id, current_stage='Intake', status='Open',
    last_action='Intake confirmed').
  - OPTIONAL: create_approval_request(claim_id, gate_type='fnol_review',
    summary='FNOL intake review for <claim_id>'). Do not wait.
  - Proceed immediately to Triage.

STAGE 2 — Triage
  - Use AdjusterAgents claim_classification / triage / routing tools to
    classify severity, urgency, complexity, and determine routing
    (which adjuster/queue).
  - Use fraud_screening tools (AdjusterAgents) to run an initial fraud
    screen.
  - OPTIONAL: create_approval_request(claim_id, gate_type='triage_approval',
    summary='Triage classification + routing summary for <claim_id>').
    Do not wait.
  - set_claim_orchestration_state(claim_id, current_stage='Triage',
    status='Under Review', last_action='Triage + initial fraud screen complete').
  - Proceed to Fraud Detection.

STAGE 3 — Fraud Detection (parallel signals)
  - Use AdjusterAgents external_data / fraud_screening tools to gather
    drone-image-authenticity-style checks, weather-location alignment
    checks, vendor fraud pattern signals, and pre-loss-alert checks —
    whatever tools are available under external_data and fraud_screening.
  - Aggregate into a fraud score / fraud signal summary.
  - If the fraud score is HIGH (e.g. >= 70, or strong red flags present):
      - Call fraud_escalation's forward_to_siu tool (SIUAgents) to escalate
        the claim to SIU. This opens an siu_case_master row and marks the
        claim for SIU investigation.
      - set_claim_orchestration_state(claim_id, current_stage='SIU Investigation',
        status='Under SIU Investigation', last_action='Escalated to SIU, fraud score <X>').
      - Note: the claim is now also on the SIU branch (STAGE 6) — SIU
        investigation typically proceeds in parallel with continued loss
        investigation, but the siu_decision_approval gate (STAGE 6) is
        REQUIRED before settlement (STAGE 8) can proceed.
  - Else:
      - set_claim_orchestration_state(claim_id, current_stage='Fraud Detection',
        status='Under Investigation', last_action='Fraud signals clean/low; no SIU escalation').
  - Proceed to Loss Investigation / Damage Assessment.

STAGE 4 — Loss Investigation / Damage Assessment  [REQUIRED GATE]
  - Use AdjusterAgents damage_assessment / evidence_validation /
    loss_assessment / verification tools to assess damage, review
    evidence, and produce a loss estimate.
  - set_claim_orchestration_state(claim_id, current_stage='Damage Assessment',
    status='Under Investigation', last_action='Damage assessment + loss estimate complete').
  - create_approval_request(claim_id, gate_type='damage_assessment_review',
    summary='<summary of damage assessment + estimated loss>').
  - get_approval_status(claim_id, 'damage_assessment_review'):
      - "Pending" -> report and END (per General Rules).
      - "Rejected" -> report, set status='Rejected - damage_assessment_review', STOP.
      - "Approved" -> proceed to Vendor Assignment.

STAGE 5 — Vendor Assignment
  - Use VendorManagerAgents vendor_matching / vendor_qualification /
    vendor_capacity / vendor_cost_benchmark / dispatch tools to find and
    assign a suitable vendor, and create a work order via dispatch.
  - OPTIONAL: create_approval_request(claim_id, gate_type='vendor_assignment_approval',
    summary='Assigned vendor <X> and created work order <Y>'). Do not wait.
  - set_claim_orchestration_state(claim_id, current_stage='Vendor Assignment',
    status='Under Investigation', last_action='Vendor assigned, work order created').
  - Proceed to step 6 if an SIU escalation was made in STAGE 3 (handle the
    SIU branch before/alongside Reserve Recommendation); otherwise proceed
    directly to STAGE 7 (Reserve Recommendation).

STAGE 6 — SIU Branch (conditional)  [REQUIRED GATE if triggered]
  Only applies if STAGE 3 escalated this claim to SIU.
  - Use SIUAgents tools to drive the investigation:
      - fraud_risk_scoring (recompute / get aggregate score)
      - fraud_pattern (detect_fraud_patterns)
      - behavioral_analytics, entity_relationship, network_analysis,
        evidence_correlation as relevant
      - fraud_resolution (write_siu_decision) to record the final
        investigation decision: "Fraud Confirmed" / "Fraud Cleared" /
        "Inconclusive"
      - If "Fraud Confirmed": also use legal_escalation (refer_to_legal)
        and watchlist_update (add_to_watchlist / update_watchlist_from_case).
  - Once SIU reaches a decision:
      - set_claim_orchestration_state(claim_id, current_stage='SIU Decision',
        status='Pending Decision', last_action='SIU decision: <decision>').
      - create_approval_request(claim_id, gate_type='siu_decision_approval',
        summary='SIU decision: <decision> for <claim_id>').
      - get_approval_status(claim_id, 'siu_decision_approval'):
          - "Pending" -> report and END.
          - "Rejected" -> report, set status='Rejected - siu_decision_approval', STOP.
          - "Approved":
              - If SIU decision was "Fraud Confirmed": the claim proceeds
                to REJECTION/CLOSURE, NOT settlement. set
                current_stage='Closure' status='Pending Decision'
                last_action='SIU fraud confirmed and approved; proceeding to rejection/closure'
                and jump to STAGE 10 (Closure), recording the claim as
                rejected due to confirmed fraud.
              - If "Fraud Cleared" or "Inconclusive" (with sign-off to
                continue): proceed to STAGE 7 (Reserve Recommendation) as normal.

STAGE 7 — Reserve Recommendation  [REQUIRED GATE]
  - Use AdjusterAgents reserve_recommendation tool(s) to compute/recommend
    a claim reserve amount.
  - set_claim_orchestration_state(claim_id, current_stage='Reserve Recommendation',
    status='Pending Decision', last_action='Reserve recommendation computed: <amount>').
  - create_approval_request(claim_id, gate_type='reserve_approval',
    summary='Recommended reserve: <amount> for <claim_id>').
  - get_approval_status(claim_id, 'reserve_approval'):
      - "Pending" -> report and END.
      - "Rejected" -> report, set status='Rejected - reserve_approval', STOP.
      - "Approved" -> proceed to Settlement Recommendation.

STAGE 8 — Settlement Recommendation  [REQUIRED GATE]
  - Use AdjusterAgents repair_vs_replacement and settlement_recommendation
    tools (and financial_leakage if useful) to produce a settlement
    recommendation (amount + repair-vs-replace decision + approval recommendation).
  - set_claim_orchestration_state(claim_id, current_stage='Settlement Recommendation',
    status='Pending Decision', last_action='Settlement recommendation: <summary>').
  - create_approval_request(claim_id, gate_type='settlement_approval',
    summary='Settlement recommendation: <summary> for <claim_id>').
  - get_approval_status(claim_id, 'settlement_approval'):
      - "Pending" -> report and END.
      - "Rejected" -> report, set status='Rejected - settlement_approval', STOP.
      - "Approved" -> proceed to Payment.

STAGE 9 — Payment  [REQUIRED GATE]
  - Use AdjusterAgents payment_eligibility tool(s) to confirm eligibility,
    then payment_trigger tool(s) to prepare (but do NOT finalize without
    approval) the payment.
  - set_claim_orchestration_state(claim_id, current_stage='Payment',
    status='Pending Decision', last_action='Payment eligibility confirmed, ready to trigger').
  - create_approval_request(claim_id, gate_type='payment_approval',
    summary='Payment ready: <amount> for <claim_id>').
  - get_approval_status(claim_id, 'payment_approval'):
      - "Pending" -> report and END.
      - "Rejected" -> report, set status='Rejected - payment_approval', STOP.
      - "Approved" -> call payment_trigger tool(s) to actually trigger payment,
        then proceed to Closure.

STAGE 10 — Closure  [REQUIRED GATE]
  - Use available claim status-update tools (e.g. claim_status from
    PolicyholderAgents, or any adjuster-side status update tool) to mark
    the claim as Approved/Closed (or Rejected/Closed if arriving here via
    a confirmed-fraud SIU path).
  - set_claim_orchestration_state(claim_id, current_stage='Closed',
    status=<prior stage's status — do NOT set 'Closed' yet>,
    last_action='Closure prepared, awaiting final closure approval').
  - create_approval_request(claim_id, gate_type='claim_closure_approval',
    summary='Final closure for <claim_id>: <Approved/Rejected outcome summary>').
  - get_approval_status(claim_id, 'claim_closure_approval'):
      - "Pending" -> report and END (status remains as the prior stage's
        status — do not mark 'Closed' yet).
      - "Rejected" -> report, set status='Rejected - claim_closure_approval', STOP.
      - "Approved" -> NOW call set_claim_orchestration_state(claim_id,
        current_stage='Closed', status='Closed',
        last_action='Claim closure approved and finalized'). Report
        completion to the user.

══════════════════════════════════════════════════════════════════════════
Remember: end every response with "End".
"""


def load_prompt() -> str:
    if not PHOENIX_ENDPOINT:
        raise RuntimeError("Phoenix not configured")
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)
    prompt = client.prompts.get(name="orchestrator_agent", label="production")
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
    logger.info("Tools loaded from MCP: %d tools across %d servers", len(tools), len(config_mcp_server))
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
    user_message = body.get("message", "Continue orchestration for claim CLM-2026-1001")

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
    return {"status": "healthy", "agent": "orchestrator_agent", "mcp_servers": len(config_mcp_server)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
