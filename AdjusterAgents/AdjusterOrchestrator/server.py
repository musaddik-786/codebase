"""
server.py — Adjuster Orchestrator Agent
────────────────────────────────────────
Orchestrates the full Claims Adjuster flow (Claim Intake to Settlement) across
all 15 AdjusterAgents in a single conversation, with human-in-the-loop (HITL)
approval gates at the same decision points the master OrchestratorAgent uses.

Stage order (see AdjusterAgents/README or CLAUDE.md for the full dependency
rationale — this order is DB-dependency-correct, not just a UI mockup order):

  1. FraudScreeningAgent        — writes fraud_risk_snapshots/fraud_flags/ai_fraud_signals.
                                   MUST run first: ClaimClassificationAgent (422s without a
                                   fraud_risk_snapshots row) and EvidenceValidationAgent
                                   (reads fraud signals to set evidence overall_status)
                                   both hard-depend on this having already run.
  2. DamageAssessmentAgent      — writes damage_items (needed by LossAssessmentAgent).
  3. ExternalDataAgent          — independent weather/drone enrichment.
  4. VerificationAgent          — independent policy/coverage cross-check. Its result now
                                   carries a deterministic coverage_verdict computed from 3
                                   Critical/hard policy facts (policy_exists, policy_status,
                                   date_of_loss_in_policy_window) — see CODE-LEVEL COVERAGE
                                   GATE below. Every other check it runs stays Advisory-only
                                   and never affects this verdict.
     >>> HITL gate: coverage_verification_review (BLOCKING — opened and enforced in CODE,
         not by prompt instruction, the instant coverage_verdict comes back "Flagged")
  5. ClaimClassificationAgent   — needs fraud_risk_snapshots (step 1).
  6. EvidenceValidationAgent    — needs fraud_risk_snapshots/fraud_flags/ai_fraud_signals (step 1).
  7. TriageAgent                — needs fraud_risk_snapshots (step 1) + claims.complexity (step 5).
  8. RoutingAgent               — needs claim_triage (step 7).
     >>> HITL gate: triage_approval (audit-only — created, not blocking)
  9. LossAssessmentAgent        — needs damage_items (step 2) + policy_details.
 10. RepairVsReplacementAgent   — needs damage/condition context (step 2).
     >>> WORKFLOW CURRENTLY HARD-STOPS HERE IN CODE — see PHASE B HARD STOP below.
         damage_assessment_review is NOT opened right now (temporarily skipped).
 11. ReserveRecommendationAgent — DISABLED FOR NOW, see PHASE B HARD STOP below.
 12. SettlementRecommendationAgent — DISABLED FOR NOW, see PHASE B HARD STOP below.
 13. PaymentEligibilityAgent    — DISABLED FOR NOW, see PHASE B HARD STOP below.
 14. FinancialLeakageAgent      — DISABLED FOR NOW, see PHASE B HARD STOP below.
 15. PaymentTriggerAgent        — DISABLED FOR NOW, see PHASE B HARD STOP below.

NOTE — coverage_confirmed gap: no tool in AdjusterAgents' MCP surface writes
adjuster_findings.coverage_confirmed (only the DB seed data sets it). This was
only ever reachable in Phase E/F, both currently disabled — see PHASE B HARD
STOP below; kept here as historical context for when the flow is restored.

PHASE A + B MERGED (2026-07-17, user request): steps 1-10 above now run as
ONE continuous reply — the prompt's old "show a summary, stop the turn, wait
for the adjuster to say 'continue'" instruction between steps 8 and 9 was
replaced with "show the summary, then keep going" (the existing ##CONTINUE##
marker convention, already used elsewhere in this prompt for post-approval
continuations). Reasoning: no HITL decision is actually needed between what
used to be Phase A and Phase B — the only thing that can legitimately stop
this stretch early is the code-level coverage_verification_review gate, which
already fires mid-Phase-A regardless of this merge. This is prompt-level only
(not code-enforced) — if the LLM occasionally doesn't emit ##CONTINUE##, the
turn just pauses like it used to; that's a missed convenience, not a safety
gap, since nothing consequential (Reserve/Settlement/Payment) is reachable
either way per the hard stop below.

PHASE B HARD STOP (TEMPORARY, user request 2026-07-16): steps 11-15 above
(Reserve through Payment Trigger) are disabled while a different continuation
mechanism is being designed. after_tools_router() detects the instant
write_repair_vs_replacement_decision (step 10's persistence call, right after
compare_repair_vs_replace) finishes and routes straight to phase_b_halt_node,
which logs a summary via logger.info (server-side ONLY — deliberately nothing
is streamed to the adjuster's chat for this, by explicit decision) and ends
the graph turn. (2026-07-23: the halt used to fire one tool call earlier, right
after compare_repair_vs_replace itself — before the LLM's next turn could call
write_repair_vs_replacement_decision — which meant the recommendation was
computed but never persisted for any claim. Moved one step later so the
decision row is actually written before the halt.) damage_assessment_review is
also not opened for this same reason — nothing downstream currently acts on
its decision.
Phase C-F's prompt instructions were pulled out of _FALLBACK_PROMPT entirely
(see PHASE C+ DISABLED there) rather than left inline, since a commented-out
English instruction inside a prompt string doesn't reliably stop an LLM from
still reading and following it. To restore the original end-to-end flow: see
the restore instructions in both PHASE C+ DISABLED (_FALLBACK_PROMPT) and
phase_b_halt_node/after_tools_router (create_graph()).

CODE-LEVEL COVERAGE GATE (coverage_verification_review): unlike every other
gate in this file, this one is NOT opened by the LLM following a prompt
instruction — it's enforced directly in create_graph()'s routing. Right after
the "tools" node runs, after_tools_router() inspects run_verification's own
result (if that's what was just called) for coverage_verdict == "Flagged".
If so, it routes straight to a coverage_gate_check node that calls
create_approval_request itself and ends the graph turn — no LLM discretion
involved, so a prompt not being followed can't let a claim with a lapsed/
missing policy or an out-of-window loss date slip through to Reserve/
Settlement. See _last_tool_batch / _find_tool_result / coverage_gate_check.
Known limitation: if run_verification is batched together with sibling tool
calls (analyze_damage_from_description, run_external_data_checks — Phase A
step 2 allows any order/batching), those siblings in the SAME batch will
already have executed before this can react. Everything after that point —
Classification, Triage, Loss Assessment, and critically Reserve/Settlement/
Payment — is what's actually prevented.

HITL gates ARE implemented locally as of 2026-07-16 — AdjusterAgents/MCP now
hosts its own copy of the orchestration sub-app (human_approval_requests +
claim_orchestration_state, same table names, same tool names) at
http://localhost:5800/api/v1/orchestration/mcp. This is a duplicate service,
not a fork of the data — same shared Postgres database as everything else in
this platform. AdjusterOrchestrator no longer depends on OrchestratorAgent's
process being up at all; it was originally a remote call to
OrchestratorAgent's own `orchestration` MCP (port 9200) — see
AdjusterAgents/MCP/orchestration_mcp/ and OrchestratorAgent/MCP/orchestration_mcp/
for the (now-independent) two copies.

Port: 8920 (ADJUSTER_ORCHESTRATOR_PORT)
MCP : http://localhost:5800/api/v1/<slug>/mcp  (15 AdjusterAgents sub-apps
      + the local orchestration/HITL sub-app, all one process)

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
from typing import Annotated, List, Optional, TypedDict

import uvicorn
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Direct DB access for claim-journey stage advancement (see
# _advance_claim_journey_stage / _set_claim_orchestration_state_direct below)
# — same sys.path pattern every AdjusterAgents handler.py uses to reach the
# shared MCP/common/db.py helper.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "MCP", "common"))
from db import get_db_connection, row_to_dict  # noqa: E402
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai.chat_models import AzureChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

load_dotenv(find_dotenv())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger("adjuster_orchestrator_agent")

PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "")
AGENT_PORT = int(os.getenv("ADJUSTER_ORCHESTRATOR_PORT", "8920"))

# All 15 AdjusterAgents sub-apps are mounted on ONE shared MCP process
# (AdjusterAgents/MCP/main.py). Per CLAUDE.md's Known Pitfalls, that process is
# currently hardcoded to listen on port 5800, not the documented/intended 8900
# — if tools fail to load, set ADJUSTER_MCP_BASE_URL=http://localhost:5800
# (or fix the hardcoded port in AdjusterAgents/MCP/main.py) rather than editing
# every slug below individually.
ADJUSTER_MCP_BASE_URL = os.getenv("ADJUSTER_MCP_BASE_URL", "http://localhost:5800")

# HITL approval/state tools — now hosted locally in AdjusterAgents/MCP (same
# process, same port as the 15 agent sub-apps above), not OrchestratorAgent's
# MCP (port 9200) anymore. Same table names (human_approval_requests,
# claim_orchestration_state) — this is a duplicate service, not a fork of
# the data, since it's one shared Postgres database across every persona.
ORCHESTRATION_MCP_URL = os.getenv(
    "ORCHESTRATION_MCP_URL", f"{ADJUSTER_MCP_BASE_URL}/api/v1/orchestration/mcp"
)

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

# Maps every MCP tool name → the conceptual agent that owns it.
# Used for terminal logging so operators can see which agent is "active".
# NOTE: a few operation_ids (e.g. get_claim_details, get_damage_items) are
# duplicated verbatim across two AdjusterAgents sub-apps — this map keeps only
# one owner per name for logging purposes; it has no effect on tool routing.
_TOOL_TO_AGENT: dict = {
    # ClaimClassificationAgent
    "get_claim_details":               "ClaimClassificationAgent",
    "classify_claim":                  "ClaimClassificationAgent",
    "save_classification":             "ClaimClassificationAgent",
    "get_claim_classification":        "ClaimClassificationAgent",
    # TriageAgent
    "get_claim_triage":                "TriageAgent",
    "run_triage":                      "TriageAgent",
    # FraudScreeningAgent
    "get_fraud_flags":                 "FraudScreeningAgent",
    "write_fraud_flag":                "FraudScreeningAgent",
    "get_ai_fraud_signals":            "FraudScreeningAgent",
    "write_ai_fraud_signal":           "FraudScreeningAgent",
    "get_fraud_risk_snapshot":         "FraudScreeningAgent",
    "write_fraud_risk_snapshot":       "FraudScreeningAgent",
    "run_fraud_screening":             "FraudScreeningAgent",
    # RoutingAgent
    "get_auto_assignment_log":         "RoutingAgent",
    "assign_claim":                    "RoutingAgent",
    # EvidenceValidationAgent
    "get_evidence_items":              "EvidenceValidationAgent",
    "get_claim_documents":             "EvidenceValidationAgent",
    "run_evidence_validation":         "EvidenceValidationAgent",
    "save_validation_result":          "EvidenceValidationAgent",
    # ExternalDataAgent
    "get_weather_alignment":           "ExternalDataAgent",
    "get_drone_authenticity":          "ExternalDataAgent",
    "get_drone_evidence_summary":      "ExternalDataAgent",
    "run_external_data_checks":        "ExternalDataAgent",
    # DamageAssessmentAgent
    "get_damage_items":                "DamageAssessmentAgent",
    "write_damage_item":               "DamageAssessmentAgent",
    "get_condition_assessments":       "DamageAssessmentAgent",
    "write_condition_assessment":      "DamageAssessmentAgent",
    "analyze_damage_from_description": "DamageAssessmentAgent",
    # VerificationAgent
    "get_external_verifications":      "VerificationAgent",
    "create_verification":             "VerificationAgent",
    "get_verification_details":        "VerificationAgent",
    "write_verification_detail":       "VerificationAgent",
    "run_verification":                "VerificationAgent",
    # LossAssessmentAgent
    "get_loss_assessment":             "LossAssessmentAgent",
    "write_loss_assessment":           "LossAssessmentAgent",
    "get_loss_estimation":             "LossAssessmentAgent",
    "write_loss_estimation":           "LossAssessmentAgent",
    "run_loss_assessment":             "LossAssessmentAgent",
    # ReserveRecommendationAgent
    "recommend_reserve":               "ReserveRecommendationAgent",
    "get_adjuster_findings":           "ReserveRecommendationAgent",
    # FinancialLeakageAgent
    "get_cost_variance":               "FinancialLeakageAgent",
    "score_leakage":                   "FinancialLeakageAgent",
    # RepairVsReplacementAgent
    "get_estimates":                   "RepairVsReplacementAgent",
    "write_estimate":                  "RepairVsReplacementAgent",
    "get_repair_cost_detail":          "RepairVsReplacementAgent",
    "write_repair_cost":               "RepairVsReplacementAgent",
    "get_replacement_cost_detail":     "RepairVsReplacementAgent",
    "write_replacement_cost":          "RepairVsReplacementAgent",
    "compare_repair_vs_replace":       "RepairVsReplacementAgent",
    "write_repair_vs_replacement_decision": "RepairVsReplacementAgent",
    # SettlementRecommendationAgent
    "recommend_settlement":            "SettlementRecommendationAgent",
    "get_ai_decision_recommendation":  "SettlementRecommendationAgent",
    # PaymentEligibilityAgent
    "get_auto_adjudication_thresholds": "PaymentEligibilityAgent",
    "check_eligibility":               "PaymentEligibilityAgent",
    "get_auto_adjudication_record":    "PaymentEligibilityAgent",
    # PaymentTriggerAgent
    "get_payment_eligibility":         "PaymentTriggerAgent",
    "check_claim_approved":            "PaymentTriggerAgent",
    "create_payment_disbursement":     "PaymentTriggerAgent",
    "update_payment_status":           "PaymentTriggerAgent",
    "get_payment_disbursements":       "PaymentTriggerAgent",
    # Shared HITL tools (OrchestratorAgent MCP)
    "get_claim_orchestration_state":   "OrchestrationHITL",
    "set_claim_orchestration_state":   "OrchestrationHITL",
    "create_approval_request":         "OrchestrationHITL",
    "get_pending_approvals":           "OrchestrationHITL",
    "decide_approval":                 "OrchestrationHITL",
    "get_approval_status":             "OrchestrationHITL",
}

config_mcp_server = {
    slug: {
        "url": f"{ADJUSTER_MCP_BASE_URL}/api/v1/{slug}/mcp",
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    }
    for slug in _ADJUSTER_SLUGS
}
config_mcp_server["orchestration"] = {
    "url": ORCHESTRATION_MCP_URL,
    "transport": "streamable_http",
    "timeout": timedelta(seconds=120),
    "sse_read_timeout": timedelta(seconds=600),
}

app = FastAPI(title="Adjuster Orchestrator Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = "Start adjuster workflow"
    input_type: Optional[str] = None
    history: List[ChatTurn] = []


class ClaimNumberRequest(BaseModel):
    claim_number: str


class PaymentDecisionRequest(BaseModel):
    claim_number: str
    decision: str  # "Approved" | "Rejected"
    amount: Optional[float] = None
    payment_method: str = "ACH"


class State(TypedDict):
    messages: Annotated[list, add_messages]


def router(state: State):
    last = state["messages"][-1]

    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"

    if isinstance(last, AIMessage) and last.content:
        # LLM appends ##CONTINUE## → auto-proceed to the next stage in the same turn
        if "##CONTINUE##" in last.content:
            return "tools"
        # Any other text response (blocked on HITL, question, summary) → stop and
        # yield back to the frontend. The NEXT user message (or the same "continue"
        # prompt re-sent after a human decision) starts a fresh graph run.
        return "End"

    return "End"


def _last_tool_batch(messages: list):
    """
    Returns (ai_message, tool_messages) for the most recently executed tool-call
    batch, or (None, []) if the tail of `messages` isn't a resolved tool batch.

    Walks backward collecting trailing ToolMessages until hitting the AIMessage
    that spawned them. LangGraph's ToolNode only ever acts on the newest
    AIMessage's tool_calls, so this reliably isolates *this graph run's* most
    recent batch — never a historical one replayed in from `history` (those are
    already-resolved messages sitting earlier in the list, not at the tail
    immediately after a "tools" node execution).
    """
    tool_messages = []
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            tool_messages.insert(0, msg)
            continue
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            return msg, tool_messages
        break
    return None, []


def _find_tool_call_and_result(messages: list, tool_name: str):
    """
    If `tool_name` was called in the most recent tool batch, returns
    (call_args, parsed_result_dict). Returns (None, None) if that tool wasn't
    in this batch, or if its result can't be parsed — callers should treat that
    as "nothing to act on" (fail open: identical to today's always-continue
    behavior), never as a reason to block, since this must never be less
    reliable than the code path it's layered on top of.
    """
    ai_message, tool_messages = _last_tool_batch(messages)
    if ai_message is None:
        return None, None

    call = next((c for c in ai_message.tool_calls if c.get("name") == tool_name), None)
    if call is None:
        return None, None

    tool_message = next((m for m in tool_messages if getattr(m, "tool_call_id", None) == call["id"]), None)
    if tool_message is None:
        return call.get("args") or {}, None

    # A tool that raised (ToolNode sets status="error") never has a meaningful
    # JSON result to act on — its content is typically a plain error string, or
    # (as seen with MCP-wrapped tools) a list of error content blocks, neither
    # of which is the dict callers expect. Treat it the same as "unparseable"
    # (fail open), not as something to crash on.
    if getattr(tool_message, "status", None) == "error":
        logger.warning("%s tool call failed (status=error) — content: %r", tool_name, tool_message.content)
        return call.get("args") or {}, None

    result = _parse_mcp_tool_content(tool_message.content)
    if result is None:
        logger.warning("Could not parse %s tool result as JSON — raw content: %r", tool_name, tool_message.content)
    return call.get("args") or {}, result


def _parse_mcp_tool_content(content) -> Optional[dict]:
    """
    Extracts a JSON dict from a ToolMessage.content, however it's shaped.

    The REAL wire format for a successful MCP-wrapped tool call (via
    langchain_mcp_adapters) is a LIST of content blocks — e.g.
    [{"type": "text", "text": "<json-string>"}] — where the actual tool
    result lives one level deeper, as a JSON STRING inside the first text
    block, not directly as `content` itself. An earlier version of this
    function only handled `content` being a bare dict or a bare JSON
    string (true for hand-built test tools, but never true for a real MCP
    call) — meaning it silently returned None for every real tool result,
    every time, including run_verification's coverage_verdict. That's the
    root cause the coverage_verification_review code-level gate never
    actually fired via this code path — it only ever fired via the LLM's
    own prompt-driven discretion, exactly the reliability gap code-level
    enforcement was supposed to close. Confirmed via requested_by on every
    real coverage_verification_review row: always "AdjusterOrchestrator",
    never this file's "AdjusterOrchestrator (system-enforced)" marker.

    Returns None (fail open) for anything that doesn't cleanly parse to a
    dict — never raises, since a caller doing `.get()` on this must never
    crash regardless of what shape a tool happens to return.
    """
    try:
        if isinstance(content, dict):
            return content
        if isinstance(content, str):
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else None
        if isinstance(content, list):
            text_parts = [
                block.get("text")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
            ]
            if not text_parts:
                return None
            parsed = json.loads(text_parts[0])
            return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None
    return None


def _find_tool_result(messages: list, tool_name: str) -> Optional[dict]:
    """Convenience wrapper around _find_tool_call_and_result for callers that
    only need the parsed result, not the call args."""
    _, result = _find_tool_call_and_result(messages, tool_name)
    return result


def _find_last_tool_result_anywhere(messages: list, tool_name: str) -> Optional[dict]:
    """
    Like _find_tool_result, but searches the ENTIRE message history for the
    last ToolMessage produced by `tool_name`, not just the most recent
    contiguous tool-call batch. _find_tool_result/_last_tool_batch are built
    to be called mid-graph (from after_tools_router, right after the "tools"
    node runs, before any further reply is appended) — the backward walk in
    _last_tool_batch stops the instant it hits a message with no tool_calls,
    which is exactly what the tail of a FINISHED conversation looks like
    (the final text-only AIMessage). Calling the mid-graph helpers after
    graph.ainvoke() has already returned silently finds nothing. Needed by
    /reserve-analysis, which inspects the finished conversation post-hoc.
    """
    call_id_to_tool_name: dict = {}
    for msg in messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for call in msg.tool_calls:
                call_id_to_tool_name[call.get("id")] = call.get("name")

    for msg in reversed(messages):
        if (
            isinstance(msg, ToolMessage)
            and call_id_to_tool_name.get(getattr(msg, "tool_call_id", None)) == tool_name
        ):
            if getattr(msg, "status", None) == "error":
                return None
            return _parse_mcp_tool_content(msg.content)
    return None


# ── Claim journey stage advancement (2026-07-23) ────────────────────────────
# The policyholder-facing "Follow My Claim" journey stepper reads
# claim_journey_master.current_stage — an int 1-8 matching JOURNEY_STAGES in
# claims-solution-integration/vite-plugins/claim-journey.ts. Confirmed via
# direct DB check: literally nothing in the entire codebase ever advances it
# past 1 ("Claim Initiated") — advance_claim_stage (PolicyholderAgents'
# claim_status tool, the only thing that ever writes this column beyond the
# initial FNOL-intake seed) has zero callers anywhere. Separately,
# set_claim_orchestration_state (claim_orchestration_state table — a
# DIFFERENT table, used for this orchestrator's own HITL/gate bookkeeping)
# is a real, locally-hosted tool but was never actually called from this
# file's prompt either (only referenced in _TOOL_TO_AGENT for logging).
#
# Both are wired here as DIRECT, deterministic DB writes (not LLM tool
# calls) for the same reliability reason as coverage_gate_check/
# phase_b_halt_node above: a prompt instruction not being followed can't
# silently break this the way it did for damage_assessment_review's gate
# creation. See after_tools_router below for the 5 checkpoints (stages 2-6)
# this fires at inside this graph.
#
# Stages 7-8 (2026-07-23, added same day): Phase C+ (Reserve, Settlement,
# Financial Leakage, Payment) runs entirely outside this graph — through
# separate endpoints and direct frontend decideClaimGate() calls — so those
# two stages can't be wired here. Stage 7 "Decision & Settlement" is instead
# wired in AdjusterAgents/MCP/orchestration_mcp/handler.py's decide_approval()
# (the single choke point every gate decision funnels through, including
# reserve_approval/settlement_approval/financial_leakage_review from the
# Loss Assessment page) — it advances once all three of those gates are
# Approved. Stage 8 "Claim Closed" is wired in this file's own
# /payment-decision endpoint, right after create_payment_disbursement
# actually succeeds.

_JOURNEY_STAGE_NUMBERS = {
    "Claim Initiated": 1,
    "Claim Intake Validation": 2,
    "Segmentation & Triage": 3,
    "Loss Investigation": 4,
    "Loss Assessment": 5,
    "Decision Pending": 6,
    "Decision & Settlement": 7,
    "Claim Closed": 8,
}


def _advance_claim_journey_stage(claim_number: str, stage_name: str, sub_status: Optional[str] = None) -> None:
    """
    Direct-SQL equivalent of PolicyholderAgents' advance_claim_stage tool —
    same table/columns, called here instead of through an MCP tool call so
    it never depends on the LLM remembering to invoke it. Never moves the
    stage backward: a no-op if the claim is already at or past this stage
    (e.g. a re-run of an earlier phase step after the claim has since moved
    further along shouldn't regress the policyholder-facing tracker).
    """
    new_stage = _JOURNEY_STAGE_NUMBERS[stage_name]
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM claims WHERE claim_number = %s", (claim_number,))
        claim_row = row_to_dict(cur.fetchone())
        claim_id = claim_row.get("id") if claim_row else None

        cur.execute(
            "SELECT id, current_stage FROM claim_journey_master WHERE claim_number = %s ORDER BY id DESC LIMIT 1",
            (claim_number,),
        )
        journey_row = row_to_dict(cur.fetchone())

        if journey_row:
            if (journey_row.get("current_stage") or 0) >= new_stage:
                return
            set_clauses = ["current_stage = %s", "current_stage_name = %s", "last_stage_change_date = NOW()"]
            params = [new_stage, stage_name]
            if sub_status is not None:
                set_clauses.append("sub_status = %s")
                params.append(sub_status)
            params.append(journey_row["id"])
            cur.execute(f"UPDATE claim_journey_master SET {', '.join(set_clauses)} WHERE id = %s", params)
        else:
            cur.execute(
                """INSERT INTO claim_journey_master
                   (claim_id, claim_number, current_stage, current_stage_name, sub_status)
                   VALUES (%s,%s,%s,%s,%s)""",
                (claim_id, claim_number, new_stage, stage_name, sub_status or "Under Review"),
            )

        # NOTE: PolicyholderAgents' own advance_claim_stage tool uses a
        # nonexistent "entered_at" column here (real column is
        # stage_start_time) — found while testing this. Since that INSERT
        # follows the claim_journey_master write in the same transaction with
        # a single commit at the end, that bug means the original tool would
        # silently roll back its claim_journey_master update too, every time
        # it's ever called. Fixed here; flagged to the user as a related,
        # independently-discovered bug in the original tool.
        cur.execute(
            """INSERT INTO stage_time_sla_tracking
               (claim_id, claim_number, stage_number, stage_name, stage_start_time)
               VALUES (%s,%s,%s,%s,NOW())""",
            (claim_id, claim_number, new_stage, stage_name),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("ADVANCE_CLAIM_STAGE_FAILED claim=%s stage=%s error=%s", claim_number, stage_name, exc)
    finally:
        conn.close()


def _set_claim_orchestration_state_direct(
    claim_number: str, current_stage: str, status: Optional[str] = None, last_action: Optional[str] = None
) -> None:
    """
    Direct-SQL equivalent of the local set_claim_orchestration_state tool —
    same table/logic, called here for the same reliability reason as
    _advance_claim_journey_stage above.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, status FROM claim_orchestration_state WHERE claim_id = %s", (claim_number,))
        row = row_to_dict(cur.fetchone())
        now = datetime.now().isoformat()
        if row is None:
            cur.execute(
                """INSERT INTO claim_orchestration_state (claim_id, current_stage, status, last_action, updated_at)
                   VALUES (%s,%s,%s,%s,%s)""",
                (claim_number, current_stage, status or "Open", last_action, now),
            )
        else:
            effective_status = status if status is not None else row.get("status")
            cur.execute(
                """UPDATE claim_orchestration_state
                   SET current_stage = %s, status = %s, last_action = %s, updated_at = %s
                   WHERE claim_id = %s""",
                (current_stage, effective_status, last_action, now, claim_number),
            )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("SET_CLAIM_ORCHESTRATION_STATE_FAILED claim=%s stage=%s error=%s", claim_number, current_stage, exc)
    finally:
        conn.close()


def _advance_journey(
    claim_number: Optional[str],
    journey_stage_name: str,
    orchestration_stage: str,
    status: Optional[str] = None,
    last_action: Optional[str] = None,
    sub_status: Optional[str] = None,
) -> None:
    """Fires both trackers together — what the user asked for: advance_claim_stage
    alongside set_claim_orchestration_state, at each checkpoint."""
    if not claim_number:
        logger.warning("Skipping journey advance to %r — no claim_number in tool call args", journey_stage_name)
        return
    _advance_claim_journey_stage(claim_number, journey_stage_name, sub_status)
    _set_claim_orchestration_state_direct(claim_number, orchestration_stage, status, last_action)


def _build_coverage_issue_summary(claim_id: str, critical_issues: list) -> str:
    """Deterministic (non-LLM-authored) summary for the coverage_verification_review
    gate — built directly from run_verification's own critical_issues, so the
    approval record's wording never depends on prompt compliance."""
    parts = []
    for issue in critical_issues:
        field = issue.get("field", "unknown_check")
        actual = issue.get("actual", "?")
        expected = issue.get("expected", "?")
        flag = issue.get("flag", "?")
        parts.append(f"{field}: got \"{actual}\" (expected \"{expected}\") — {flag}")
    issue_text = "; ".join(parts) if parts else "one or more critical policy checks did not pass"
    return f"Claim {claim_id}: automatic coverage verification flagged {len(critical_issues)} critical issue(s) — {issue_text}."


_FALLBACK_PROMPT = """
You are the Adjuster Orchestrator Agent for an insurance claims management platform.

Your job is to walk one claim through the full Claims Adjuster journey — Fraud
Screening, Damage & Enrichment, Classification, Triage & Routing, Loss
Assessment, Reserve, Settlement, Payment Eligibility, and Payment — in one
seamless conversation, pausing for a human adjuster's sign-off at a few
specific points along the way.

The adjuster's message will usually be "Run the adjuster workflow for claim
<claim_number>" or "Continue the adjuster workflow for claim <claim_number>".
Extract claim_number from the message or from earlier turns — never ask the
adjuster to repeat it once you have it.

════════════════════════════════════════════════════════════
HOW APPROVALS WORK (read this once — it applies to every phase below)
════════════════════════════════════════════════════════════
A few steps need a human adjuster's sign-off before the claim can move on.
Each time that happens, do three things, in order:
  1. Open it: create_approval_request(claim_id=<claim_number>,
     gate_type="<gate name>", summary="<a plain-language summary written
     from the real numbers you just got — never copy example wording
     verbatim>", requested_by="AdjusterOrchestrator").
  2. Check it: get_approval_status(claim_id=<claim_number>,
     gate_type="<same gate name>").
  3. Act on the result:
       - "Pending"  → stop. Tell the adjuster what you're waiting on and
         that they can decide it in the approvals panel, then ask you to
         continue.
       - "Rejected" → stop the ENTIRE workflow and explain why (use
         decision_notes if present).
       - "Approved" → say so in one sentence and continue straight into the
         next phase, same reply.

Only a human deciding in the approvals panel (decide_approval) changes a
Pending request — you never decide one yourself. If you're re-checking a
gate you opened earlier (e.g. the adjuster just said "continue"), check its
status before opening a new one — never open a second request for a gate
that already has one Pending or Approved.

This is also how you "resume" after a pause — there is no separate resume
step anywhere else in this prompt. Each phase below just checks its own
data or gate first, and picks up from there.

════════════════════════════════════════════════════════════
PHASE A — FRAUD SCREENING, DAMAGE, ENRICHMENT & TRIAGE (no approval needed yet)
════════════════════════════════════════════════════════════
Only step 2 below is allowed to continue past a failure — its three checks
are independent of each other. Steps 1, 3, and 4 each feed data the next
step needs, so if any of THOSE fail, stop the phase and report it instead
of moving on (see General Rules).

1. FRAUD SCREENING — must happen first
   - Call run_fraud_screening(claim_id=<claim_number>).
   - This has to run before anything else in this phase: Classification and
     Evidence Validation below both read what this writes, and will behave
     incorrectly or fail outright without it. Never skip or reorder this.

2. DAMAGE, WEATHER, AND POLICY CHECKS — independent of each other, any order
   - Call analyze_damage_from_description(claim_number=<claim_number>). For
     each item it returns, call write_damage_item(claim_number=<claim_number>,
     category=..., severity=..., estimated_cost=..., adjuster_notes=...) —
     this tool does NOT save automatically, you must save each item yourself.
     If it instead reports damage already exists (existing_items_count > 0),
     skip straight to reading those existing items — do not re-assess.
   - Call run_external_data_checks(claim_id=<claim_number>) for weather/drone
     context. This tool can "succeed" (no thrown error) but still contain an
     "error" key in its own result if its internal drone-assessment step
     couldn't be parsed — nothing gets saved in that case. Check for an
     "error" key in the result itself, not just a failed tool call, and
     treat it the same as a failure for this check.
   - Call run_verification(claim_id=<claim_number>) for the policy/coverage
     cross-check. Its result includes coverage_verdict ("Confirmed" or
     "Flagged"). You do NOT need to act on a "Flagged" verdict yourself — the
     system automatically opens a coverage_verification_review request and
     halts the workflow the instant it sees one, before you get another turn.
     If you're reading this note at all, treat it as informational only.
   - If analyze_damage_from_description or run_external_data_checks fails, do
     not stop the phase — note the failure in plain language for your Phase A
     summary and continue with the others. They don't depend on each other.

   RESUMING AFTER A COVERAGE HALT — if the conversation history shows a
   "⛔ Coverage verification halted this claim" message from an earlier turn,
   that means Phase A stopped automatically before Classification ever ran.
   On this turn:
   - Call get_approval_status(claim_id=<claim_number>, gate_type="coverage_verification_review").
   - "Pending"  → stop again. Tell the adjuster it's still awaiting a decision.
   - "Rejected" → stop the ENTIRE workflow (same as any other rejected gate).
     Explain plainly that coverage could not be confirmed for this claim and it
     needs manual handling — there is currently no tool that marks a claim
     declined in this system (same gap as the coverage_confirmed note above),
     so this is as far as the automated workflow can take it.
   - "Approved" → say so in one sentence, then continue Phase A from step 3
     (Classification) onward, through Phase B below, all in the same reply —
     same merged behavior as the normal step 5 → Phase B transition.

3. CLASSIFY THE CLAIM AND VALIDATE EVIDENCE — need Step 1's fraud data
   - Call classify_claim(claim_number=<claim_number>). It returns a
     complexity and a routing recommendation — use those exact values to
     call save_classification(claim_number=<claim_number>, complexity=...,
     routing=...).
   - Call run_evidence_validation(claim_id=<claim_number>). Use its
     overall_status and authenticity_flags to call
     save_validation_result(claim_id=<claim_number>, overall_status=...,
     authenticity_flags=...).

4. TRIAGE AND ROUTE
   - Call run_triage(claim_id=<claim_number>).
   - Call assign_claim(claim_id=<claim_number>).
   - Open an AUDIT-ONLY note — this is visible for later review but never
     blocks the workflow, so do not wait on it:
     create_approval_request(claim_id=<claim_number>, gate_type="triage_approval",
     summary=<a sentence built from the real priority_score, sla_risk,
     routing, and assigned_to you just got>, requested_by="AdjusterOrchestrator").
     Proceed immediately afterward regardless of its status.

5. SUMMARIZE AND CONTINUE STRAIGHT INTO PHASE B
   No approval is needed between Phase A and Phase B — show the adjuster a
   short Markdown table of what you found so far, then keep going in the
   SAME reply (do not stop the turn here):

   | Item                  | Result            |
   |------------------------|-------------------|
   | Fraud Score            | ...               |
   | Damage Categories      | ... (total $...)  |
   | External Data Check    | ... (or "failed — see note") |
   | Policy Verification    | ... (or "failed — see note") |
   | Complexity             | ...               |
   | Priority / Routing     | ...               |
   | Assigned To            | ...               |

   After the table, say something like: "Fraud screening, damage assessment,
   verification, classification, and routing are complete for claim
   <claim_number>. Continuing to Loss Assessment now." Then append the
   literal marker ##CONTINUE## and proceed directly into Phase B below in
   this same reply — do not wait for another message.

════════════════════════════════════════════════════════════
PHASE B — LOSS ASSESSMENT & REPAIR VS REPLACEMENT (runs immediately after
Phase A in this same reply, no approval needed)
════════════════════════════════════════════════════════════
- Call run_loss_assessment(claim_number=<claim_number>) — ALWAYS call this
  fresh, every time you reach Phase B, even if you already have loss
  assessment numbers from earlier in this conversation or a prior run for
  this claim. Unlike damage assessment in Phase A (which is skip-if-already-
  exists), loss assessment must be recomputed every time, since damage items
  may have changed since it last ran. Do not substitute get_loss_assessment
  or get_claim_details for this step — those are read-only lookups for other
  purposes, not a valid replacement for actually running the assessment.
  This computes total loss, deductible, and net payable from the damage
  items Phase A saved.
- Call compare_repair_vs_replace(claim_number=<claim_number>, item_age=...,
  useful_life_remaining=...) — estimate item_age and useful_life_remaining
  from context (loss type, damage severity). Do NOT pass item_type — this
  tool derives it itself from the claim's damage item. If it tells you
  damage assessment hasn't been done yet, this normally shouldn't happen
  since Phase A already ran it — stop here and tell the adjuster damage
  assessment needs to be completed before this step can run, rather than
  guessing at repair-vs-replace numbers.
- Call write_repair_vs_replacement_decision

using:

- claim_number
- recommended_action
- ai_generated_message

The ai_generated_message should contain a concise summary of the recommendation.
- Show the adjuster a short Markdown table of the real results before opening
  the gate:

  | Item                          | Result  |
  |-------------------------------|---------|
  | Total Estimated Loss          | ...     |
  | Deductible Applied            | ...     |
  | Net Payable                   | ...     |
  | Subrogation Likelihood        | ...     |
  | Repair vs Replace Recommendation | ... (repair $... / replacement $...) |

- Build a one-line approval summary from the same REAL numbers. Say that same
  one-line summary out loud in your reply, directly below the table, before
  opening the gate: create_approval_request(claim_id=<claim_number>,
  gate_type="damage_assessment_review", summary=<that summary>,
  requested_by="AdjusterOrchestrator").
- Check get_approval_status(claim_id=<claim_number>, gate_type="damage_assessment_review")
  and follow the Pending/Rejected/Approved handling from "HOW APPROVALS WORK" above.
  On Approved, continue straight into Phase C in the same reply.
"""
# NOTE: the text above (Phase B's table + damage_assessment_review gate) is now
# unreachable in practice — see PHASE C+ DISABLED block below: the orchestrator
# hard-stops in CODE the instant compare_repair_vs_replace finishes, before the
# LLM gets a turn to show this table or open that gate. Left as-is/untouched
# rather than edited, since it's harmless dead prompt text and this whole
# arrangement is temporary (see phase_b_halt_node in create_graph()).

# ════════════════════════════════════════════════════════════════════════
# PHASE C+ DISABLED (temporary, user request 2026-07-16) — Reserve, Settlement,
# Payment Eligibility & Financial Leakage, and Payment Trigger are commented out
# below, NOT deleted, while a different continuation mechanism is designed.
# The orchestrator now hard-stops in code right after RepairVsReplacementAgent's
# compare_repair_vs_replace tool runs (see phase_b_halt_node / after_tools_router
# in create_graph()) — the LLM never reaches Phase C onward, so this text was
# pulled out of the active _FALLBACK_PROMPT string entirely (a commented-out
# English instruction inside the string wouldn't reliably stop an LLM from
# reading and following it — this way it structurally can't).
#
# To restore the original end-to-end flow: move this block's text back inside
# _FALLBACK_PROMPT (between Phase B and GENERAL RULES, uncommented), and remove
# the phase_b_halt hard-stop from after_tools_router/create_graph().
# ════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════
# PHASE C — RESERVE RECOMMENDATION (pauses here for adjuster approval)
# ════════════════════════════════════════════════════════════
# UPDATED 2026-07-20: recommend_reserve() has grown since this phase was
# originally drafted — it now also factors in the policy deductible and the
# remaining coverage limit (capping the recommendation at it), and it returns
# its own LLM-authored one-sentence `rationale` explaining the full
# calculation (base loss, deductible applied, net loss after deductible,
# severity buffer, fraud buffer, final figure, and the comparison against the
# adjuster's own reserve if one is already set). The table and approval
# summary below now surface all of that — not just severity/fraud buffers.
# - Call recommend_reserve(claim_id=<claim_number>). Its result has:
#   system_recommended_reserve, adjuster_set_reserve (may be null/"not set"),
#   variance_percent (may be "Not Applicable" if no adjuster reserve yet),
#   severity_buffer_percent, fraud_buffer_percent, and rationale.
# - Show the adjuster a short Markdown table of the real results before opening
#   the gate:
#
#   | Item                     | Result  |
#   |--------------------------|---------|
#   | Recommended Reserve      | ...     |
#   | Adjuster-Set Reserve     | ... (or "not yet set") |
#   | Variance                 | ... (or "not applicable — no adjuster reserve set yet") |
#   | Severity Buffer          | ...%    |
#   | Fraud Buffer             | ...%    |
#   | Rationale                | <the tool's own rationale sentence, verbatim> |
#
# - Build a one-line approval summary from the same REAL numbers — lead with
#   the tool's own `rationale` sentence (it already explains the deductible,
#   net loss, and buffers in plain language; do not re-derive a shorter one
#   that drops that detail), then append the recommended vs. adjuster-set
#   comparison. Say that same one-line summary out loud in your reply,
#   directly below the table, before opening create_approval_request(
#   claim_id=<claim_number>, gate_type="reserve_approval", summary=<that
#   summary>, requested_by="AdjusterOrchestrator").
# - Check get_approval_status(..., gate_type="reserve_approval") and follow the
#   same Pending/Rejected/Approved handling. On Approved, continue into Phase D.
#
# ════════════════════════════════════════════════════════════
# PHASE D — SETTLEMENT RECOMMENDATION (pauses here for adjuster approval)
# ════════════════════════════════════════════════════════════
# - Call recommend_settlement(claim_id=<claim_number>).
# - If this tool call returns an error instead of a result, do NOT show the
#   raw error to the adjuster. Say instead: "Settlement recommendation could
#   not be completed automatically for this claim — this looks like a data
#   issue with the policy or recommendation record, not something a retry
#   will fix. Recommending this claim be routed to manual settlement review."
#   Set current_stage-style context to "Blocked - settlement_recommendation_error"
#   in your own reasoning and STOP. Do not open the settlement_approval gate
#   in this case — there is no settlement figure yet to review.
# - If it succeeds: show the adjuster a short Markdown table of the real
#   results before opening the gate:
#
#   | Item                   | Result  |
#   |------------------------|---------|
#   | Settlement Amount      | ...     |
#   | Remaining Coverage Limit | ...   |
#   | Recommended Action     | ...     |
#   | STP Score              | ...     |
#   | Confidence             | ...     |
#
#   Then build a one-line approval summary from the same REAL numbers. Say
#   that same one-line summary out loud in your reply, directly below the
#   table, before opening create_approval_request(claim_id=<claim_number>,
#   gate_type="settlement_approval", summary=<that summary>,
#   requested_by="AdjusterOrchestrator").
# - Check get_approval_status(..., gate_type="settlement_approval") and follow
#   the same Pending/Rejected/Approved handling. On Approved, continue into Phase E.
#
# ════════════════════════════════════════════════════════════
# PHASE E — PAYMENT ELIGIBILITY & FINANCIAL LEAKAGE (pauses here for adjuster approval)
# ════════════════════════════════════════════════════════════
# - Call check_eligibility(claim_id=<claim_number>). In the rare case no
#   threshold configuration exists yet, its result won't have the usual
#   gates/failed_gates breakdown — just report the reason it gives and treat
#   eligibility as not yet determined, rather than assuming any gate passed.
# - Call score_leakage(claim_id=<claim_number>) for visibility. If it reports
#   no vendor cost data available, just note that in your summary and move on
#   — it is informational only and never blocks payment.
# - Call get_adjuster_findings(claim_id=<claim_number>) and look at
#   coverage_confirmed. There is currently no tool that can SET this value —
#   if it is missing or not "Yes", say so plainly in the approval summary below
#   and ask the human reviewer to confirm coverage as part of their decision,
#   since approving this gate is the only way that confirmation happens today.
# - Show the adjuster a short Markdown table of the real results before
#   opening the gate:
#
#   | Item                          | Result  |
#   |-------------------------------|---------|
#   | Eligible for Auto-Adjudication | ...    |
#   | Gates Passed / Failed         | ...     |
#   | Coverage Confirmed            | ... (or "Not confirmed — needs reviewer input") |
#   | Financial Leakage Risk        | ... (or "No vendor cost data available") |
#
# - Build a one-line approval summary from the same REAL results, plus the
#   coverage_confirmed note above if it applies. Say that same one-line
#   summary out loud in your reply, directly below the table, before opening
#   create_approval_request(claim_id=<claim_number>,
#   gate_type="payment_approval", summary=<that summary>,
#   requested_by="AdjusterOrchestrator").
# - Check get_approval_status(..., gate_type="payment_approval") and follow the
#   same Pending/Rejected/Approved handling. On Approved, continue into Phase F.
#
# ════════════════════════════════════════════════════════════
# PHASE F — PAYMENT TRIGGER (no approval — this is what the last gate unlocked)
# ════════════════════════════════════════════════════════════
# - Call get_payment_eligibility(claim_number=<claim_number>) then
#   check_claim_approved(claim_number=<claim_number>).
# - If approved, call create_payment_disbursement(claim_number=<claim_number>,
#   amount=<the net payable amount already established in Phase B/D>,
#   payment_method="ACH", approved_by="AdjusterOrchestrator").
# - If NOT approved, do not attempt disbursement. Tell the adjuster plainly
#   why, using check_claim_approved's own reason field (e.g. coverage not yet
#   confirmed), and stop — this needs manual follow-up, not a retry.
# - Present a final Markdown table summarizing every phase's real outcome for
#   this claim, built from the actual results gathered across the whole run:
#
#   | Item                     | Result  |
#   |--------------------------|---------|
#   | Fraud Score              | ...     |
#   | Complexity               | ...     |
#   | Priority / Routing       | ...     |
#   | Total Loss / Net Payable | ...     |
#   | Reserve Approved         | ...     |
#   | Settlement Action        | ...     |
#   | Payment Status           | ...     |
#   | Payment Amount           | ...     |
#   | Disbursement ID          | ... (or "not disbursed — see reason above") |
# ════════════════════════════════════════════════════════════════════════

_FALLBACK_PROMPT += """
════════════════════════════════════════════════════════════
GENERAL RULES
════════════════════════════════════════════════════════════
- Talk to the adjuster the way a colleague would — never say a table or
  column name out loud (say "recommended reserve", not
  "adjuster_findings.system_recommended_reserve").
- If a tool call errors, say plainly what broke, don't guess a result in its
  place, and stop that phase so the adjuster can investigate — don't silently
  move on. (The Phase D settlement-error special case referenced by earlier
  drafts of this rule is currently inert — Phase D is disabled, see PHASE C+
  DISABLED above.)
- Every approval summary must be written from the actual numbers you just
  received from a tool call — never copy example wording from this prompt
  verbatim into a real summary.
- Ask at most 2 clarifying questions per turn if you genuinely need adjuster
  input for something (e.g. an ambiguous item_age) — otherwise make a
  reasonable estimate from context rather than stopping to ask.
"""

# ════════════════════════════════════════════════════════════════════════
# RESERVE ANALYSIS PROMPT (2026-07-20) — a small, standalone prompt for the
# /reserve-analysis endpoint below, NOT part of the Phase A-F conversation
# above. Adapted from the (still-dormant) PHASE C text: same table shape and
# the same instruction to lead with the tool's own `rationale`, but with the
# gate-opening step removed — reserve_approval is decided when the adjuster
# clicks Save on the reserve amount, not when this analysis runs (matches how
# Loss Assessment's own Save button is what decides damage_assessment_review,
# not the agent run that produced the numbers).
# ════════════════════════════════════════════════════════════════════════
_RESERVE_ANALYSIS_PROMPT = """
You are the Adjuster Orchestrator, running only the Reserve Recommendation
step for one claim — not the full adjuster workflow.

The message names the claim_number. Call recommend_reserve(claim_id=<claim_number>)
exactly once. Its result has: system_recommended_reserve, adjuster_set_reserve
(may be null), variance_percent (may be "Not Applicable" if no adjuster
reserve is set yet), severity_buffer_percent, fraud_buffer_percent, and its
own LLM-authored rationale sentence.

Show a short Markdown table of the real results:

| Item                     | Result  |
|--------------------------|---------|
| Recommended Reserve      | ...     |
| Adjuster-Set Reserve     | ... (or "not yet set") |
| Variance                 | ... (or "not applicable — no adjuster reserve set yet") |
| Severity Buffer          | ...%    |
| Fraud Buffer             | ...%    |

Then show the tool's own `rationale` verbatim, unmodified, as a short
paragraph below the table — it already explains the deductible, net loss, and
buffers in plain language; do not shorten or rephrase it.

Do not call any other tool. Do not open or check any approval gate — that is
decided separately when the adjuster saves their reserve decision, not here.
Do not ask a follow-up question. Stop immediately after presenting the table
and rationale.
"""

# ════════════════════════════════════════════════════════════════════════
# SETTLEMENT ANALYSIS PROMPT (2026-07-20) — same pattern as the reserve
# analysis prompt above, for the /settlement-analysis endpoint. settlement_approval
# is decided when the adjuster saves their settlement amount, not here.
# ════════════════════════════════════════════════════════════════════════
_SETTLEMENT_ANALYSIS_PROMPT = """
You are the Adjuster Orchestrator, running only the Settlement Recommendation
step for one claim — not the full adjuster workflow.

The message names the claim_number. Call recommend_settlement(claim_id=<claim_number>)
exactly once. Its result has: settlement_amount, deductible, remaining_coverage_limit,
recommended_action, stp_score, and notes.

If this tool call returns an error instead of a result, do NOT show the raw
error to the adjuster. Say instead: "Settlement recommendation could not be
completed automatically for this claim — this looks like a data issue with
the policy or recommendation record, not something a retry will fix.
Recommending this claim be routed to manual settlement review." Then stop.

If it succeeds, show a short Markdown table of the real results:

| Item                     | Result  |
|--------------------------|---------|
| Settlement Amount        | ...     |
| Deductible Applied       | ...     |
| Remaining Coverage Limit | ...     |
| Recommended Action       | ...     |
| STP Score                | ...     |

Then show the tool's own `notes` verbatim, unmodified, as a short paragraph
below the table — it already explains why the business rules produced this
recommendation; do not shorten or rephrase it.

Do not call any other tool. Do not open or check any approval gate — that is
decided separately when the adjuster saves their settlement decision, not
here. Do not ask a follow-up question. Stop immediately after presenting the
table and notes (or the error message above, if the tool call failed).
"""

# ════════════════════════════════════════════════════════════════════════
# FINANCIAL LEAKAGE ANALYSIS PROMPT (2026-07-20) — same pattern as reserve/
# settlement above, for /financial-leakage-analysis. financial_leakage_review
# is decided when the adjuster saves their risk-level decision, not here.
# ════════════════════════════════════════════════════════════════════════
_FINANCIAL_LEAKAGE_ANALYSIS_PROMPT = """
You are the Adjuster Orchestrator, running only the Financial Leakage step
for one claim — not the full adjuster workflow.

The message names the claim_number. Call score_leakage(claim_id=<claim_number>)
exactly once. Its result has: total_estimated_cost, total_actual_cost,
overall_variance_percent, leakage_score (0-100), leakage_risk
("Low"|"Medium"|"High"|"Critical"), risk_flags (a list, each with item_type/
issue/severity — may be empty), and recommendation.

total_actual_cost is the aggregate repair or replacement cost of the claim's
damaged items (whichever table matches the claim's Repair vs Replace
decision) — not a vendor invoice total.

If the tool reports no Repair vs Replace decision or cost detail is
available for this claim yet (its "message" field will say so, and
leakage_risk will be "Unknown"), say plainly that financial leakage cannot be
scored yet because Repair vs Replace hasn't been run for this claim, and
stop — do not present a table in that case.

Otherwise, show a short Markdown table of the real results:

| Item                     | Result  |
|--------------------------|---------|
| Leakage Risk             | ...     |
| Leakage Score            | .../100 |
| Overall Variance         | ...%    |
| Total Estimated Cost     | ...     |
| Total Actual Cost        | ...     |

Then list each entry in `risk_flags` as a short bullet (item, issue,
severity) if there are any, followed by the tool's own `recommendation`
verbatim, unmodified, as a short paragraph — do not shorten or rephrase it.

Do not call any other tool. Do not open or check any approval gate — that is
decided separately when the adjuster saves their risk-level decision, not
here. Do not ask a follow-up question. Stop immediately after presenting the
table, flags, and recommendation (or the no-decision message above).
"""

# ════════════════════════════════════════════════════════════════════════
# PAYMENT ELIGIBILITY ANALYSIS PROMPT (2026-07-20) — run as part of the
# combined Financial Leakage → Payment Eligibility → Payment Trigger preview
# flow (see /financial-leakage-analysis). check_eligibility() itself only
# ever writes its own recommendation record now — it no longer auto-approves
# claims.status (see payment_eligibility_mcp/handler.py) — so, like Reserve/
# Settlement/Leakage, nothing here commits anything; that only happens via
# the adjuster's own final decision at /payment-decision.
# ════════════════════════════════════════════════════════════════════════
_PAYMENT_ELIGIBILITY_ANALYSIS_PROMPT = """
You are the Adjuster Orchestrator, running only the Payment Eligibility step
for one claim — not the full adjuster workflow.

The message names the claim_number. Call check_eligibility(claim_id=<claim_number>)
exactly once. Its result has: eligible_for_auto_adjudication, decision
("FULL_STP" or "MANUAL_REVIEW"), stp_category, gates (a dict of 8 named
checks, each with pass/value/threshold), failed_gates (a list of gate names),
and recommendation.

Show a short Markdown table of the real results:

| Item                           | Result  |
|--------------------------------|---------|
| Eligible for Auto-Adjudication | ...     |
| Decision                      | ...     |
| STP Category                  | ...     |
| Gates Passed / Failed         | <n passed> / <n failed, listing failed gate names if any> |

Then show the tool's own `recommendation` verbatim, unmodified, as a short
paragraph below the table.

Do not call any other tool. Do not open or check any approval gate and do not
say anything is "approved" for payment — eligibility is only one input to
the adjuster's own final payment decision, made separately. Do not ask a
follow-up question. Stop immediately after presenting the table and
recommendation.
"""

# ════════════════════════════════════════════════════════════════════════
# PAYMENT TRIGGER PREVIEW PROMPT (2026-07-20) — read-only preview only. The
# tools bound to this prompt are filtered in code (see get_trigger_preview_tools())
# to exclude create_payment_disbursement entirely — it is not merely
# discouraged by this prompt, it is structurally unavailable to call here.
# Actual disbursement only ever happens via the adjuster's explicit final
# decision at the deterministic (non-LLM) /payment-decision endpoint.
# ════════════════════════════════════════════════════════════════════════
_PAYMENT_TRIGGER_PREVIEW_PROMPT = """
You are the Adjuster Orchestrator, previewing payment readiness for one claim
— not disbursing anything, and not the full adjuster workflow.

The message names the claim_number. Call get_payment_eligibility(claim_number=<claim_number>)
then check_claim_approved(claim_number=<claim_number>) — both are read-only.
check_claim_approved's result has: approved, coverage_confirmed,
available_amount, amount_source, and reason (populated when not approved).

Show a short Markdown table of the real results:

| Item                    | Result  |
|-------------------------|---------|
| Approved for Payment    | ...     |
| Coverage Confirmed      | ...     |
| Available Amount        | ...     |
| Amount Source           | ...     |
| Reason (if not approved) | ... (or "N/A") |

You do not have a tool available to actually trigger payment — do not claim
payment was disbursed or initiated. This is a preview only; the adjuster
makes the final call separately. Do not ask a follow-up question. Stop
immediately after presenting the table.
"""


def load_prompt() -> str:
    if not PHOENIX_ENDPOINT:
        raise RuntimeError("Phoenix not configured")
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)
    prompt = client.prompts.get(name="adjuster_orchestrator_agent", label="production")
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

    async def coverage_gate_check_node(state: State):
        """
        Reached only when after_tools_router detects run_verification just came
        back with coverage_verdict == "Flagged". Opens the coverage_verification_review
        gate itself (bypassing LLM discretion entirely) and halts — this node's
        only outgoing edge goes straight to END.
        """
        args, result = _find_tool_call_and_result(state["messages"], "run_verification")
        claim_id = (args or {}).get("claim_id", "unknown")
        critical_issues = (result or {}).get("critical_issues", [])
        summary = _build_coverage_issue_summary(claim_id, critical_issues)

        create_approval_request = next((t for t in tools if t.name == "create_approval_request"), None)
        approval_note = ""
        if create_approval_request is not None:
            try:
                await create_approval_request.ainvoke({
                    "claim_id": claim_id,
                    "gate_type": "coverage_verification_review",
                    "summary": summary,
                    "requested_by": "AdjusterOrchestrator (system-enforced)",
                })
            except Exception as exc:
                logger.error("Failed to open coverage_verification_review gate for %s: %s", claim_id, exc)
                approval_note = (
                    " (Note: the system could not automatically open the approval "
                    "request — this needs manual follow-up.)"
                )
        else:
            logger.error("create_approval_request tool not available — cannot open coverage_verification_review gate")
            approval_note = (
                " (Note: the system could not automatically open the approval "
                "request — this needs manual follow-up.)"
            )

        halt_message = (
            f"⛔ **Coverage verification halted this claim.** {summary}\n\n"
            f"A `coverage_verification_review` request has been opened for a human "
            f"adjuster to confirm or override this before anything else runs. No "
            f"further steps (Classification, Triage, Loss Assessment, Reserve, "
            f"Settlement, Payment) will proceed until that decision is made.{approval_note}"
        )
        return {"messages": [AIMessage(content=halt_message)]}

    async def phase_b_halt_node(state: State):
        """
        TEMPORARY (user request, 2026-07-16): hard-stops the workflow in code
        the instant RepairVsReplacementAgent's write_repair_vs_replacement_decision
        tool finishes — the true last step of Phase B (persisting the
        recommendation) — instead of letting it continue into
        Reserve/Settlement/Payment (Phase C onward is pulled out of the active
        prompt, see PHASE C+ DISABLED in _FALLBACK_PROMPT above). This is
        deliberately silent to the adjuster's chat: no message is streamed
        (stream_graph() has no on_chain_end handler for this node's name,
        unlike coverage_gate_check) — the summary goes to server logs only,
        per an explicit "fully silent to chat" decision. damage_assessment_review
        is also NOT opened here (also an explicit decision) since nothing
        downstream currently acts on it while Phase C+ is disabled.

        2026-07-23 fix: the halt used to fire the instant compare_repair_vs_replace
        finished, one tool call too early — that's the recommendation step, not
        the persistence step, so write_repair_vs_replacement_decision (the very
        next tool the prompt tells the LLM to call) never got a turn to run,
        leaving repair_vs_replacement_decisions permanently empty for every
        claim. The halt now triggers one tool call later, after the decision
        row is actually written. compare_repair_vs_replace/run_loss_assessment
        results are pulled from anywhere in history (not just the last batch)
        since they ran in an earlier tool-call batch than the one that now
        triggers this halt.
        """
        rvr_args, rvr_result = _find_tool_call_and_result(state["messages"], "write_repair_vs_replacement_decision")
        loss_result = _find_last_tool_result_anywhere(state["messages"], "run_loss_assessment")
        compare_result = _find_last_tool_result_anywhere(state["messages"], "compare_repair_vs_replace")
        claim_id = (rvr_args or {}).get("claim_number", "unknown")

        logger.info(
            "PHASE_B_HALT %s",
            json.dumps(
                {
                    "claim_id": claim_id,
                    "note": "Workflow halted after Phase B (Repair vs Replace decision saved) — Phase C+ disabled for now.",
                    "loss_assessment": loss_result,
                    "repair_vs_replace_comparison": compare_result,
                    "repair_vs_replace_decision": rvr_result,
                    "timestamp_utc": datetime.utcnow().isoformat(),
                },
                default=str,
            ),
        )
        return {"messages": []}

    def after_tools_router(state: State):
        messages = state["messages"]

        result = _find_tool_result(messages, "run_verification")
        if result is not None and result.get("coverage_verdict") == "Flagged":
            return "coverage_gate_check"

        # Claim journey stage advancement — 5 checkpoints, stages 2-6. Each
        # _find_tool_call_and_result call only matches the CURRENT last tool
        # batch, so this fires exactly once per checkpoint (the instant that
        # batch is current), not on every subsequent turn.
        if result is not None and result.get("coverage_verdict") == "Confirmed":
            v_args, _ = _find_tool_call_and_result(messages, "run_verification")
            _advance_journey(
                (v_args or {}).get("claim_id"),
                "Claim Intake Validation", "Claim Intake Validation",
                status="In Progress", last_action="Coverage verification confirmed",
                sub_status="Coverage confirmed",
            )

        ev_args, _ = _find_tool_call_and_result(messages, "save_validation_result")
        if ev_args is not None:
            _advance_journey(
                ev_args.get("claim_id"),
                "Segmentation & Triage", "Classification & Evidence Validation",
                status="In Progress", last_action="Claim classified and evidence validated",
                sub_status="Classified, evidence validated",
            )

        routing_args, _ = _find_tool_call_and_result(messages, "assign_claim")
        if routing_args is not None:
            _advance_journey(
                routing_args.get("claim_id"),
                "Loss Investigation", "Triage & Routing",
                status="In Progress", last_action="Claim triaged and routed",
                sub_status="Triaged and routed",
            )

        loss_args, _ = _find_tool_call_and_result(messages, "run_loss_assessment")
        if loss_args is not None:
            _advance_journey(
                loss_args.get("claim_number"),
                "Loss Assessment", "Loss Assessment",
                status="In Progress", last_action="Loss assessment computed",
                sub_status="Loss assessment computed",
            )

        rvr_decision_args, _ = _find_tool_call_and_result(messages, "write_repair_vs_replacement_decision")
        if rvr_decision_args is not None:
            _advance_journey(
                rvr_decision_args.get("claim_number"),
                "Decision Pending", "Repair vs Replace Decision",
                status="Pending Decision",
                last_action="Repair vs Replace recommendation saved, awaiting adjuster review",
                sub_status="Awaiting adjuster review",
            )
            return "phase_b_halt"

        return "agent"

    graph_builder.add_node("agent", agent_node)
    graph_builder.add_node("tools", ToolNode(tools=tools))
    graph_builder.add_node("coverage_gate_check", coverage_gate_check_node)
    graph_builder.add_node("phase_b_halt", phase_b_halt_node)
    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges("agent", router, {"tools": "tools", "End": END})
    graph_builder.add_conditional_edges(
        "tools",
        after_tools_router,
        {"agent": "agent", "coverage_gate_check": "coverage_gate_check", "phase_b_halt": "phase_b_halt"},
    )
    graph_builder.add_edge("coverage_gate_check", END)
    graph_builder.add_edge("phase_b_halt", END)
    return graph_builder.compile()


async def get_tools():
    client = MultiServerMCPClient(config_mcp_server)
    tools = await client.get_tools()
    logger.info("Tools loaded from MCP: %s", [t.name for t in tools])
    return tools


# Scoped MCP client for /reserve-analysis below — only the reserve_recommendation
# sub-app, not all 15 agents + orchestration. Keeps the LLM from being able to
# call anything unrelated, and keeps tool loading fast for this single-purpose
# endpoint.
_reserve_mcp_server = {
    "reserve_recommendation": config_mcp_server["reserve_recommendation"],
}


async def get_reserve_tools():
    client = MultiServerMCPClient(_reserve_mcp_server)
    tools = await client.get_tools()
    logger.info("Reserve analysis tools loaded from MCP: %s", [t.name for t in tools])
    return tools


# Scoped MCP client for /settlement-analysis below — only settlement_recommendation.
_settlement_mcp_server = {
    "settlement_recommendation": config_mcp_server["settlement_recommendation"],
}


async def get_settlement_tools():
    client = MultiServerMCPClient(_settlement_mcp_server)
    tools = await client.get_tools()
    logger.info("Settlement analysis tools loaded from MCP: %s", [t.name for t in tools])
    return tools


# Scoped MCP client for /financial-leakage-analysis below — only financial_leakage.
_leakage_mcp_server = {
    "financial_leakage": config_mcp_server["financial_leakage"],
}


async def get_leakage_tools():
    client = MultiServerMCPClient(_leakage_mcp_server)
    tools = await client.get_tools()
    logger.info("Financial leakage analysis tools loaded from MCP: %s", [t.name for t in tools])
    return tools


# Scoped MCP client for the Payment Eligibility step of the combined analysis.
_eligibility_mcp_server = {
    "payment_eligibility": config_mcp_server["payment_eligibility"],
}


async def get_eligibility_tools():
    client = MultiServerMCPClient(_eligibility_mcp_server)
    tools = await client.get_tools()
    logger.info("Payment eligibility analysis tools loaded from MCP: %s", [t.name for t in tools])
    return tools


# The payment_trigger MCP sub-app exposes create_payment_disbursement on the
# SAME connection as get_payment_eligibility/check_claim_approved — there's no
# way to get a narrower connection at the URL level, so the preview step
# filters the fetched tool list down to just the two read-only tools before
# binding them to the LLM. This makes create_payment_disbursement structurally
# uncallable during preview, not just prompt-discouraged.
_trigger_mcp_server = {
    "payment_trigger": config_mcp_server["payment_trigger"],
}
_TRIGGER_PREVIEW_TOOL_NAMES = {"get_payment_eligibility", "check_claim_approved"}


async def get_trigger_preview_tools():
    client = MultiServerMCPClient(_trigger_mcp_server)
    all_tools = await client.get_tools()
    tools = [t for t in all_tools if t.name in _TRIGGER_PREVIEW_TOOL_NAMES]
    logger.info("Payment trigger preview tools loaded from MCP (filtered): %s", [t.name for t in tools])
    return tools


async def get_trigger_action_tools():
    """Unfiltered — used only by the deterministic /payment-decision endpoint,
    never by an LLM-driven graph."""
    client = MultiServerMCPClient(_trigger_mcp_server)
    return await client.get_tools()


async def stream_graph(graph, initial_state, config):
    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        kind = event.get("event", "")

        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield f"data: {chunk.content}\n\n"

        elif kind == "on_tool_start":
            tool_name = event.get("name", "unknown_tool")
            agent_name = _TOOL_TO_AGENT.get(tool_name, "UnknownAgent")
            logger.info("▶ %-40s  tool → %s", f"[{agent_name}]", tool_name)
            yield f"data: [Tool: {tool_name}] Starting...\n\n"

        elif kind == "on_tool_end":
            tool_name = event.get("name", "unknown_tool")
            agent_name = _TOOL_TO_AGENT.get(tool_name, "UnknownAgent")
            logger.info("✓ %-40s  tool → %s", f"[{agent_name}]", tool_name)
            yield f"data: [Tool: {tool_name}] Done\n\n"

        elif kind == "on_chain_end" and event.get("name") == "coverage_gate_check":
            # coverage_gate_check_node returns its AIMessage directly (no LLM
            # invocation), so it never fires on_chat_model_stream above — stream
            # its content here instead, or the client would see the SSE stream
            # go quiet with no explanation right when the workflow halts.
            output = event.get("data", {}).get("output") or {}
            for msg in output.get("messages") or []:
                content = getattr(msg, "content", None)
                if content:
                    yield f"data: {content}\n\n"


@app.post("/chat")
async def chat_stream(body: ChatRequest):
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

    today_str = datetime.now().strftime("%Y-%m-%d")
    system_prompt = f"[TODAY: {today_str}]\n\n{system_prompt}"

    user_message = body.message
    if body.input_type:
        user_message = f"[input_type: {body.input_type}] {user_message}"

    history_messages = []
    for turn in body.history:
        if not turn.content:
            continue
        if turn.role == "user":
            history_messages.append(HumanMessage(content=turn.content))
        elif turn.role == "assistant":
            history_messages.append(AIMessage(content=turn.content))
    history_messages.append(HumanMessage(content=user_message))

    graph = create_graph(model=model, tools=tools, prompt=system_prompt)

    async def generate():
        start = time.time()
        last_event_at = start
        last_tool = None
        try:
            async for event in stream_graph(
                graph=graph,
                initial_state={"messages": history_messages},
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

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/reserve-analysis")
async def reserve_analysis(body: ClaimNumberRequest):
    """
    Runs ONLY the Reserve Recommendation step, through the orchestrator's own
    LLM/tool-calling loop — a separate, minimal flow from /chat's full Phase
    A-F conversation (which still hard-stops after Phase B). Scoped tools +
    a tiny dedicated prompt mean this is one tool call, not a 10-agent chain,
    so unlike /chat's SSE stream this is a single awaited JSON response — no
    racing a timeout against a run that might still be in flight.

    Does not open reserve_approval — that's decided when the adjuster saves
    their reserve amount (see /save-reserve in the frontend's vite-plugin),
    not here.
    """
    load_dotenv(find_dotenv())

    claim_number = body.claim_number.strip()
    if not claim_number:
        raise HTTPException(status_code=400, detail="claim_number is required")

    tools = await get_reserve_tools()

    model = AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

    today_str = datetime.now().strftime("%Y-%m-%d")
    prompt = f"[TODAY: {today_str}]\n\n{_RESERVE_ANALYSIS_PROMPT}"

    graph = create_graph(model=model, tools=tools, prompt=prompt)

    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=f"Run the reserve recommendation for claim {claim_number}.")]},
            config={"recursion_limit": 10},
        )
    except Exception as e:
        logger.error("RESERVE_ANALYSIS_ERROR claim=%s error=%s", claim_number, e)
        raise HTTPException(status_code=500, detail=f"Reserve analysis failed: {e}")

    messages = result["messages"]
    tool_result = _find_last_tool_result_anywhere(messages, "recommend_reserve") or {}

    summary_markdown = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            summary_markdown = msg.content
            break

    if not tool_result:
        logger.warning("RESERVE_ANALYSIS_NO_RESULT claim=%s — recommend_reserve did not return a parseable result", claim_number)

    return {
        "claim_number": claim_number,
        "summary_markdown": summary_markdown,
        "system_recommended_reserve": tool_result.get("system_recommended_reserve"),
        "adjuster_set_reserve": tool_result.get("adjuster_set_reserve"),
        "variance_percent": tool_result.get("variance_percent"),
        "severity_buffer_percent": tool_result.get("severity_buffer_percent"),
        "fraud_buffer_percent": tool_result.get("fraud_buffer_percent"),
        "rationale": tool_result.get("rationale"),
    }


@app.post("/settlement-analysis")
async def settlement_analysis(body: ClaimNumberRequest):
    """
    Runs ONLY the Settlement Recommendation step, through the orchestrator's
    own LLM/tool-calling loop — same pattern as /reserve-analysis above.

    Does not open settlement_approval — that's decided when the adjuster
    saves their settlement amount (see /save-settlement in the frontend's
    vite-plugin), not here.
    """
    load_dotenv(find_dotenv())

    claim_number = body.claim_number.strip()
    if not claim_number:
        raise HTTPException(status_code=400, detail="claim_number is required")

    tools = await get_settlement_tools()

    model = AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

    today_str = datetime.now().strftime("%Y-%m-%d")
    prompt = f"[TODAY: {today_str}]\n\n{_SETTLEMENT_ANALYSIS_PROMPT}"

    graph = create_graph(model=model, tools=tools, prompt=prompt)

    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=f"Run the settlement recommendation for claim {claim_number}.")]},
            config={"recursion_limit": 10},
        )
    except Exception as e:
        logger.error("SETTLEMENT_ANALYSIS_ERROR claim=%s error=%s", claim_number, e)
        raise HTTPException(status_code=500, detail=f"Settlement analysis failed: {e}")

    messages = result["messages"]
    tool_result = _find_last_tool_result_anywhere(messages, "recommend_settlement") or {}

    summary_markdown = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            summary_markdown = msg.content
            break

    if not tool_result:
        logger.warning("SETTLEMENT_ANALYSIS_NO_RESULT claim=%s — recommend_settlement did not return a parseable result", claim_number)

    return {
        "claim_number": claim_number,
        "summary_markdown": summary_markdown,
        "settlement_amount": tool_result.get("settlement_amount"),
        "deductible": tool_result.get("deductible"),
        "remaining_coverage_limit": tool_result.get("remaining_coverage_limit"),
        "recommended_action": tool_result.get("recommended_action"),
        "stp_score": tool_result.get("stp_score"),
        "notes": tool_result.get("notes"),
    }


def _build_model() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


async def _run_single_tool_analysis(tools: list, prompt_text: str, user_message: str, tool_name: str) -> dict:
    """
    Shared runner for the single-tool-call analysis endpoints (Reserve,
    Settlement, Leakage, Eligibility, Trigger preview): builds a fresh graph
    with the given scoped tools + prompt, runs it to completion, and extracts
    the named tool's result + the LLM's own narrated summary. Each call is
    fully independent — no shared conversation state between steps, same as
    every other endpoint in this file.
    """
    model = _build_model()
    today_str = datetime.now().strftime("%Y-%m-%d")
    prompt = f"[TODAY: {today_str}]\n\n{prompt_text}"
    graph = create_graph(model=model, tools=tools, prompt=prompt)

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=user_message)]},
        config={"recursion_limit": 10},
    )
    messages = result["messages"]
    tool_result = _find_last_tool_result_anywhere(messages, tool_name) or {}

    summary_markdown = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            summary_markdown = msg.content
            break

    return {"tool_result": tool_result, "summary_markdown": summary_markdown}


@app.post("/financial-leakage-analysis")
async def financial_leakage_analysis(body: ClaimNumberRequest):
    """
    Runs Financial Leakage, then Payment Eligibility, then a read-only
    Payment Trigger preview — three independent single-tool-call analyses
    (see _run_single_tool_analysis), run sequentially in Python rather than
    relying on one LLM turn to reliably sequence three tool calls itself.
    Each step is exactly the same reliable pattern already proven for
    /reserve-analysis and /settlement-analysis.

    None of these three commit anything — score_leakage/check_eligibility are
    pure recommendations, and the Payment Trigger preview's tools are
    filtered to exclude create_payment_disbursement entirely (see
    get_trigger_preview_tools()). The adjuster's actual final payment
    decision — including any real disbursement — only happens via the
    separate, deterministic (non-LLM) /payment-decision endpoint below.
    """
    load_dotenv(find_dotenv())

    claim_number = body.claim_number.strip()
    if not claim_number:
        raise HTTPException(status_code=400, detail="claim_number is required")

    try:
        leakage_tools = await get_leakage_tools()
        leakage = await _run_single_tool_analysis(
            leakage_tools,
            _FINANCIAL_LEAKAGE_ANALYSIS_PROMPT,
            f"Run the financial leakage analysis for claim {claim_number}.",
            "score_leakage",
        )
    except Exception as e:
        logger.error("LEAKAGE_ANALYSIS_ERROR claim=%s error=%s", claim_number, e)
        raise HTTPException(status_code=500, detail=f"Financial leakage analysis failed: {e}")

    try:
        eligibility_tools = await get_eligibility_tools()
        eligibility = await _run_single_tool_analysis(
            eligibility_tools,
            _PAYMENT_ELIGIBILITY_ANALYSIS_PROMPT,
            f"Run the payment eligibility analysis for claim {claim_number}.",
            "check_eligibility",
        )
    except Exception as e:
        logger.error("ELIGIBILITY_ANALYSIS_ERROR claim=%s error=%s", claim_number, e)
        raise HTTPException(status_code=500, detail=f"Payment eligibility analysis failed: {e}")

    try:
        trigger_preview_tools = await get_trigger_preview_tools()
        trigger_preview = await _run_single_tool_analysis(
            trigger_preview_tools,
            _PAYMENT_TRIGGER_PREVIEW_PROMPT,
            f"Preview payment readiness for claim {claim_number}.",
            "check_claim_approved",
        )
    except Exception as e:
        logger.error("TRIGGER_PREVIEW_ERROR claim=%s error=%s", claim_number, e)
        raise HTTPException(status_code=500, detail=f"Payment trigger preview failed: {e}")

    leakage_result = leakage["tool_result"]
    eligibility_result = eligibility["tool_result"]
    trigger_result = trigger_preview["tool_result"]

    if not leakage_result:
        logger.warning("LEAKAGE_ANALYSIS_NO_RESULT claim=%s", claim_number)
    if not eligibility_result:
        logger.warning("ELIGIBILITY_ANALYSIS_NO_RESULT claim=%s", claim_number)
    if not trigger_result:
        logger.warning("TRIGGER_PREVIEW_NO_RESULT claim=%s", claim_number)

    return {
        "claim_number": claim_number,
        "leakage": {
            "summary_markdown": leakage["summary_markdown"],
            "total_estimated_cost": leakage_result.get("total_estimated_cost"),
            "total_actual_cost": leakage_result.get("total_actual_cost"),
            "overall_variance_percent": leakage_result.get("overall_variance_percent"),
            "leakage_score": leakage_result.get("leakage_score"),
            "leakage_risk": leakage_result.get("leakage_risk"),
            "risk_flags": leakage_result.get("risk_flags"),
            "recommendation": leakage_result.get("recommendation"),
        },
        "eligibility": {
            "summary_markdown": eligibility["summary_markdown"],
            "eligible_for_auto_adjudication": eligibility_result.get("eligible_for_auto_adjudication"),
            "decision": eligibility_result.get("decision"),
            "stp_category": eligibility_result.get("stp_category"),
            "gates": eligibility_result.get("gates"),
            "failed_gates": eligibility_result.get("failed_gates"),
            "recommendation": eligibility_result.get("recommendation"),
        },
        "paymentPreview": {
            "summary_markdown": trigger_preview["summary_markdown"],
            "approved": trigger_result.get("approved"),
            "coverage_confirmed": trigger_result.get("coverage_confirmed"),
            "available_amount": trigger_result.get("available_amount"),
            "amount_source": trigger_result.get("amount_source"),
            "reason": trigger_result.get("reason"),
        },
    }


def _find_tool(tools: list, name: str):
    return next((t for t in tools if t.name == name), None)


@app.post("/payment-decision")
async def payment_decision(body: PaymentDecisionRequest):
    """
    The adjuster's actual final payment decision — deliberately NOT an LLM
    turn. By the time this is called, there is nothing left to reason about:
    the amount, method, and approval all come from what the adjuster already
    reviewed in the combined analysis above. Directly invoking the tools
    (bypassing agent_node/create_graph entirely) means there is no LLM
    discretion involved in the one action in this whole effort that actually
    moves money.

    decision="Approved": calls confirm_payment_approval (commits
    claims.status = "Approved" — the commit that used to happen inside
    check_eligibility() itself, see payment_eligibility_mcp/handler.py), then
    create_payment_disbursement (which has its own internal safety checks —
    blocks on failed Full-STP eligibility, unconfirmed coverage, or a
    zero/missing amount — and returns an "error" key rather than disbursing
    if any of those fire).

    decision="Rejected": no tool calls at all.
    """
    load_dotenv(find_dotenv())

    claim_number = body.claim_number.strip()
    if not claim_number:
        raise HTTPException(status_code=400, detail="claim_number is required")

    decision = body.decision.strip().capitalize()
    if decision not in ("Approved", "Rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'Approved' or 'Rejected'")

    if decision == "Rejected":
        return {"claim_number": claim_number, "decision": "Rejected", "disbursed": False}

    if body.amount is None or body.amount <= 0:
        raise HTTPException(status_code=400, detail="A valid amount is required to approve payment")

    try:
        eligibility_tools = await get_eligibility_tools()
        trigger_tools = await get_trigger_action_tools()
    except Exception as e:
        logger.error("PAYMENT_DECISION_TOOL_LOAD_ERROR claim=%s error=%s", claim_number, e)
        raise HTTPException(status_code=500, detail=f"Could not load payment tools: {e}")

    confirm_tool = _find_tool(eligibility_tools, "confirm_payment_approval")
    disburse_tool = _find_tool(trigger_tools, "create_payment_disbursement")
    if confirm_tool is None or disburse_tool is None:
        raise HTTPException(status_code=500, detail="Required payment tools are not available from the MCP server")

    try:
        confirm_result = _parse_mcp_tool_content(await confirm_tool.ainvoke({"claim_id": claim_number})) or {}
    except Exception as e:
        logger.error("CONFIRM_PAYMENT_APPROVAL_ERROR claim=%s error=%s", claim_number, e)
        raise HTTPException(status_code=500, detail=f"Could not confirm payment approval: {e}")

    try:
        disburse_result = _parse_mcp_tool_content(
            await disburse_tool.ainvoke({
                "claim_number": claim_number,
                "amount": body.amount,
                "payment_method": body.payment_method,
                "approved_by": "adjuster_1",
            })
        ) or {}
    except Exception as e:
        logger.error("CREATE_PAYMENT_DISBURSEMENT_ERROR claim=%s error=%s", claim_number, e)
        raise HTTPException(status_code=500, detail=f"Could not create payment disbursement: {e}")

    if disburse_result.get("error"):
        logger.warning("PAYMENT_DISBURSEMENT_BLOCKED claim=%s reason=%s", claim_number, disburse_result.get("reason"))
        return {
            "claim_number": claim_number,
            "decision": "Approved",
            "disbursed": False,
            "confirmApproval": confirm_result,
            "error": disburse_result.get("error"),
            "reason": disburse_result.get("reason"),
        }

    # Journey stage 8 "Claim Closed" — the one place a real disbursement is
    # ever triggered, so it's the natural terminal checkpoint for the
    # policyholder-facing journey tracker (see _advance_journey docstring).
    _advance_journey(
        claim_number, "Claim Closed", "Payment Disbursed",
        status="Closed", last_action="Payment approved and disbursed",
        sub_status="Payment disbursed",
    )

    return {
        "claim_number": claim_number,
        "decision": "Approved",
        "disbursed": True,
        "confirmApproval": confirm_result,
        "disbursement": disburse_result,
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "adjuster_orchestrator_agent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
