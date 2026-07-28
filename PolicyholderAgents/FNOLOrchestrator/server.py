"""
server.py — FNOL Orchestrator Agent (Policyholder)
────────────────────────────────────────────────────
Orchestrates the full policyholder intake flow:
  1. FNOL collection via VoiceTextIntake MCP tools (Steps 1–6)
  2. Document collection via DocumentSubmission MCP tools (Step 7)

Keeps VoiceTextIntakeAgent and DocumentSubmissionAgent as pure,
single-responsibility agents. This agent owns the combined flow.

Port: 7730
MCP : http://localhost:7720/api/v1/voice_text_intake/mcp
      http://localhost:7720/api/v1/document_submission/mcp

Run:
    py -3 server.py
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Annotated, List, Optional, TypedDict

import httpx
import uvicorn
from dotenv import load_dotenv, find_dotenv
from fastapi import BackgroundTasks, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
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
logger = logging.getLogger("fnol_orchestrator_agent")

PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "")
AGENT_PORT = int(os.getenv("FNOL_ORCHESTRATOR_PORT", "7730"))

VOICE_MCP_URL           = os.getenv("MCP_URL",                  "http://localhost:7720/api/v1/voice_text_intake/mcp")
DOC_MCP_URL             = os.getenv("DOC_MCP_URL",              "http://localhost:7720/api/v1/document_submission/mcp")
DUPLICATE_CHECK_MCP_URL = os.getenv("DUPLICATE_CHECK_MCP_URL",  "http://localhost:7720/api/v1/duplicate_check/mcp")
POLICY_COVERAGE_MCP_URL = os.getenv("POLICY_COVERAGE_MCP_URL",  "http://localhost:7720/api/v1/policy_coverage/mcp")
CLAIM_READINESS_MCP_URL = os.getenv("CLAIM_READINESS_MCP_URL",  "http://localhost:7720/api/v1/claim_readiness/mcp")
SEGMENTATION_MCP_URL    = os.getenv("SEGMENTATION_MCP_URL",     "http://localhost:7720/api/v1/segmentation/mcp")
CLAIM_STATUS_MCP_URL    = os.getenv("CLAIM_STATUS_MCP_URL",     "http://localhost:7720/api/v1/claim_status/mcp")
COMMUNICATION_MCP_URL   = os.getenv("COMMUNICATION_MCP_URL",    "http://localhost:7720/api/v1/communication/mcp")
FEEDBACK_MCP_URL        = os.getenv("FEEDBACK_MCP_URL",         "http://localhost:7720/api/v1/feedback/mcp")

WHISPER_ENDPOINT = os.getenv(
    "AZURE_WHISPER_ENDPOINT",
    "https://azureclaimsopenai.openai.azure.com/openai/deployments/gpt-4o-transcribe-diarize/audio/transcriptions?api-version=2025-03-01-preview",
)
WHISPER_API_KEY = os.getenv("AZURE_WHISPER_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY", "")

# Maps every MCP tool name → the conceptual agent that owns it.
# Used for terminal logging so operators can see which agent is "active".
_TOOL_TO_AGENT: dict = {
    # VoiceTextIntakeAgent
    "create_fnol_submission":           "VoiceTextIntakeAgent",
    "get_fnol_submission":              "VoiceTextIntakeAgent",
    "get_fnol_by_policy":               "VoiceTextIntakeAgent",
    "update_fnol_submission":           "VoiceTextIntakeAgent",
    "submit_fnol":                      "VoiceTextIntakeAgent",
    "get_mandatory_fields":             "VoiceTextIntakeAgent",
    "save_voice_text_extraction":       "VoiceTextIntakeAgent",
    "get_voice_text_extractions":       "VoiceTextIntakeAgent",
    "save_ai_inferences":               "VoiceTextIntakeAgent",
    "log_question_answer":              "VoiceTextIntakeAgent",
    "get_question_log":                 "VoiceTextIntakeAgent",
    "save_field_attribution":           "VoiceTextIntakeAgent",
    "extract_fnol_fields_from_text":    "VoiceTextIntakeAgent",
    # DuplicateClaimCheckAgent
    "check_duplicate_claim":            "DuplicateClaimCheckAgent",
    "get_recent_claims_for_policy":     "DuplicateClaimCheckAgent",
    # DocumentSubmissionAgent
    "upload_document":                  "DocumentSubmissionAgent",
    "get_claim_documents":              "DocumentSubmissionAgent",
    "validate_document":                "DocumentSubmissionAgent",
    "get_document_by_id":               "DocumentSubmissionAgent",
    # PolicyCoverageVerificationAgent
    "get_coverage_verification_result": "PolicyCoverageVerificationAgent",
    "get_policy_details":               "PolicyCoverageVerificationAgent",
    "verify_coverage":                  "PolicyCoverageVerificationAgent",
    "save_policy_details":              "PolicyCoverageVerificationAgent",
    # ClaimReadinessAgent
    "score_claim_readiness":            "ClaimReadinessAgent",
    "acknowledge_missing_docs":         "ClaimReadinessAgent",
    # ClaimSegmentationAgent
    "get_claim_for_segmentation":       "ClaimSegmentationAgent",
    "compute_stp_score":                "ClaimSegmentationAgent",
    "get_stp_classification":           "ClaimSegmentationAgent",
    # ClaimStatusAgent
    "get_claim_status_summary":         "ClaimStatusAgent",
    "log_policyholder_action":          "ClaimStatusAgent",
    # CommunicationAgent
    "log_inbound_communication":        "CommunicationAgent",
    "draft_status_notification":        "CommunicationAgent",
    # FeedbackAgent
    "write_customer_feedback":          "FeedbackAgent",
    "get_customer_feedback":            "FeedbackAgent",
}

config_mcp_server = {
    "voice_text_intake_mcp": {
        "url": VOICE_MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    },
    "document_submission_mcp": {
        "url": DOC_MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    },
    "duplicate_check_mcp": {
        "url": DUPLICATE_CHECK_MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    },
    "policy_coverage_mcp": {
        "url": POLICY_COVERAGE_MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    },
    "claim_readiness_mcp": {
        "url": CLAIM_READINESS_MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    },
    "segmentation_mcp": {
        "url": SEGMENTATION_MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    },
    "claim_status_mcp": {
        "url": CLAIM_STATUS_MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    },
    "communication_mcp": {
        "url": COMMUNICATION_MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    },
    "feedback_mcp": {
        "url": FEEDBACK_MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    },
}

app = FastAPI(title="FNOL Orchestrator Agent (Policyholder)")

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
    message: str = "Start FNOL intake"
    input_type: Optional[str] = None
    history: List[ChatTurn] = []


class ProcessRequest(BaseModel):
    claim_number: str


class State(TypedDict):
    messages: Annotated[list, add_messages]


import re as _re

def router(state: State):
    last = state["messages"][-1]

    # LLM wants to call tools → run tools
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"

    if isinstance(last, AIMessage) and last.content:
        # LLM appends ##CONTINUE## → auto-proceed (used for phases 9–13)
        if "##CONTINUE##" in last.content:
            return "tools"
        # Any other text response (question, summary, waiting for user input) → stop
        # and yield back to the frontend. The NEXT user message starts a fresh graph run.
        return "End"

    return "End"


_FALLBACK_PROMPT = """
You are the FNOL Orchestrator Agent for an insurance claims management platform.

Your role is to guide the policyholder through the full claim lifecycle in one
seamless conversation — from first notice of loss all the way to feedback.

The policyholder's message may be:
  - Typed text
  - A server-transcribed voice recording (input_type="voice_transcript")

Messages may begin with a [POLICY_CONTEXT: ...] tag containing pre-verified policy
details (policy_number, policyholder_name, policyholder_address, status, coverage_type, effective_date).
If this tag is present:
  - DO NOT ask for the policy number, policyholder name, or policyholder address — you already have them.
  - Extract policy_number from the tag and immediately call create_fnol_submission.
    Do NOT call get_fnol_by_policy first — always start a fresh FNOL.
  - Immediately call update_fnol_submission to set policy_number, policyholder_name,
    and policyholder_address from the tag values.
  - Call save_field_attribution for each of those three fields with source="guidewire_lookup"
    so the audit trail records they were auto-filled from Guidewire.
  - Proceed directly to collecting loss details — do not ask for any policy information.

════════════════════════════════════════════════════════════
PHASE A — FNOL INTAKE (Steps 1–6)
════════════════════════════════════════════════════════════

1. IDENTIFY THE POLICYHOLDER
   - If [POLICY_CONTEXT:] is present, extract policy_number from it — skip asking.
   - Otherwise ask for their policy number.
   - Always call create_fnol_submission to start a fresh FNOL for this session.
     The system automatically deletes any previous draft for this policy, so do
     NOT call get_fnol_by_policy first or attempt to resume an old draft — doing
     so would reuse stale data from a different incident.
   - After create_fnol_submission succeeds, your FIRST response message MUST include
     the line "FNOL ID: <id>" (where <id> is the integer `id` returned by the tool).
     On every subsequent turn, recover the FNOL ID by scanning the conversation history
     for the first assistant message that contains "FNOL ID: <id>". NEVER ask the user
     for the FNOL ID — it is an internal system reference, not a user-facing concept.

2. COLLECT LOSS DETAILS (conversational Q&A)
   - Call get_mandatory_fields to retrieve the required field list.
   - For each mandatory field not yet captured, ask the policyholder the
     corresponding inference_question from the mandatory fields list.
   - After each answer, call log_question_answer to persist the exchange.

3. EXTRACT FIELDS FROM THE USER'S MESSAGE
   - Call extract_fnol_fields_from_text with the user's message as raw_text and
     the appropriate input_type ("voice_transcript" or "text").
     This automatically saves extraction + inference records.
   - After the call, check the `auto_persist_status` field in the response.
     If auto_persist_status == "failed", immediately call update_fnol_submission
     with all extracted field values as a fallback — this ensures the fields are
     persisted before you proceed to Step 4.

4. AFTER EXTRACTION
   - Call update_fnol_submission to persist all newly extracted fields onto the FNOL.
     SOURCE TRACKING — whenever you call update_fnol_submission, always include the
     corresponding _source column for every field you are setting. Choose the value
     that best describes how you obtained the information:
       * "text_input"         — extracted from the policyholder's typed message
       * "voice_transcript"   — extracted from a voice recording transcript
       * "ai_inferred"        — you derived/inferred the value from context
                                (e.g. resolved "yesterday" → 2026-07-02, or inferred
                                severity/urgency from the user's language)
       * "customer_confirmed" — policyholder explicitly confirmed a value you proposed
     Example: if you asked "Were you home?" and they answered "yes", call
     update_fnol_submission with occupancy_at_loss=1 AND
     occupancy_at_loss_source="customer_confirmed".
   - Call save_field_attribution with source details for each field.
   - Call get_fnol_submission to read the CURRENT state of every field in the DB.
     Use THIS record — not the extraction result — to determine what is still missing.
     Fields captured in earlier turns are already in the DB and must NOT be re-asked.
   - Compare the returned record against the mandatory field list. Ask ONLY about
     fields that are NULL or empty in the DB record.
   - POLICY_CONTEXT guard: If [POLICY_CONTEXT:] was present in the first user message,
     policy_number, policyholder_name, and policyholder_address are already captured — exclude
     them from the gap check and do NOT ask the policyholder for them.
   - Keep calling log_question_answer for each follow-up exchange.
   - MANDATORY GATE: After get_fnol_submission, check EVERY field in the mandatory
     fields list. If ANY mandatory field is still NULL or empty in the DB record,
     you MUST stay in Steps 2–5 and ask for the missing field(s). Do NOT proceed
     to Step 6 until get_fnol_submission confirms ALL mandatory fields are non-null.
   - If get_fnol_submission confirms ALL mandatory fields are already non-null
     (e.g. the policyholder's message covered everything in one turn), proceed
     directly to Step 6 in this SAME turn — do not invent an extra question first.

5. DUPLICATE CHECK (before submission)
   - Once policy_number, loss_type, and date_of_loss are all known, call
     check_duplicate_claim with those three values.
   - If is_duplicate is true:
       * Inform the policyholder a similar claim already exists and mention
         the matching claim number(s).
       * Ask: "Is this a new incident, or are you following up on an existing one?"
       * If they confirm it is NEW, continue to Step 6.
       * If they say it is a follow-up, stop intake and guide them to the
         Claim Status section instead. Do NOT submit a new FNOL.
   - If is_duplicate is false: proceed directly to Step 6 without mentioning
     the check to the policyholder.

6. PRESENT SUMMARY AND HAND OFF TO THE UI
   - ONLY enter this step when get_fnol_submission confirms ALL mandatory fields
     are non-null and non-empty. If any mandatory field is missing, return to
     Steps 2–5 to collect it — never show this summary table prematurely.
   - Present ALL captured fields as a Markdown table:

     | Field                        | Recorded Value   |
     |------------------------------|------------------|
     | Type of Loss                 | ...              |
     | Cause of Loss                | ...              |
     | Date of Loss                 | ...              |
     | Time of Loss                 | ...              |
     | Area Affected                | ...              |
     | Occupancy at Time of Loss    | ...              |
     | Sudden vs Gradual            | ...              |
     | Severity                     | ...              |
     | Urgency Indicator            | ...              |
     | Emotional Context            | ...              |

   - After the table, say EXACTLY this (replace nothing in the wording):
     "All details have been captured. Please click **Review and Confirm Fields**
      below to review, make any corrections, and submit your claim."
   - END the conversation immediately after delivering this message.
     Do NOT ask for CONFIRM. Do NOT call submit_fnol. Do NOT proceed further.
     The submission is handled entirely by the UI once the user clicks that button.

════════════════════════════════════════════════════════════
GENERAL RULES
════════════════════════════════════════════════════════════
- Always be empathetic. The policyholder may be distressed.
- Keep questions concise and clear.
- Ask at most 2 questions per turn. If more mandatory fields are missing, ask the most important 2 and defer the rest to the next turn.
- Do not ask for information you can already infer with high confidence.
- ONLY ask about the mandatory fields returned by get_mandatory_fields. Never ask
  about anything outside that list — e.g. emergency services, police/fire
  department involvement, temporary housing, repair urgency, or any other
  claims-adjacent detail. Those are out of scope for FNOL intake and are handled
  by other agents downstream. If every mandatory field is already captured, do
  not manufacture a question just to have something to ask — move to Step 6.
- Never re-ask a field that is already stored in the DB. After every extraction,
  call get_fnol_submission and use the returned record as the source of truth for
  what is captured vs. missing — not the extraction output, not conversation memory.
- Do NOT dump a full field-by-field summary during Steps 2–5. In those turns,
  briefly acknowledge what you captured in one sentence ("Got it — I've noted the
  date as 2026-06-29.") then ask the next question. The full formatted table is
  reserved for Step 6 only.
- The [TODAY: YYYY-MM-DD] tag at the top of this prompt contains today's date. Use it to resolve relative dates like "yesterday", "last Tuesday", etc. — convert them to ISO format (YYYY-MM-DD) and confirm with the policyholder in plain language rather than asking them to re-state the date.
- Do NOT expose internal IDs, database fields, or adjuster details.
- Your job ends at Step 6. Do NOT call submit_fnol or any post-submission tools.
  Submission and post-processing are handled by the UI after the user clicks
  "Review and Confirm Fields".
"""


_BACKGROUND_PROCESS_PROMPT = """
You are the FNOL Post-Submission Processor running in SILENT BACKGROUND MODE.

You are triggered automatically after a new claim is submitted via Smart Loss Reporting.
Your ONLY job is to call the required MCP tools in the correct sequence so that the
database tables are populated and the Follow My Claims UI can display claim insights
to the policyholder.

RULES — FOLLOW STRICTLY:
- DO NOT produce any text between tool calls.
- DO NOT ask questions. DO NOT narrate. DO NOT explain what you are doing.
- Call ALL tools in the sequence below in ONE uninterrupted pass.
- If a tool returns an error, record the error value and continue to the next step —
  do NOT stop the entire run because of a single failure.
- Produce output ONCE only: the final completion line after all steps finish.

The trigger message is in the format: "Background process claim {claim_number}"
Extract the claim_number value and use it in every tool call below.

════════════════════════════════════════════════════════════
STEP 1 — POLICY COVERAGE VERIFICATION
Target table: coverage_verification_results
════════════════════════════════════════════════════════════
1a. Call get_coverage_verification_result(claim_number).
    - If a row is returned with a non-null coverage_verdict → skip to Step 2.
    - If no row exists → proceed to 1b.
1b. Call get_claim_details(claim_number) to read the policy_number field from the claim.
1c. Call save_policy_details(policy_number) using the policy_number you just retrieved.
    This fetches the policy from Guidewire and upserts it into policy_details,
    ensuring coverage_limit and deductible are populated with correct values.
    If this returns an error, record it and continue — verify_coverage has fallback logic.
1d. Call verify_coverage(claim_number).
    This reads from policy_details (just saved) and writes coverage_verdict, net_payable,
    exclusion_triggered, and exclusion_details to coverage_verification_results.

════════════════════════════════════════════════════════════
STEP 2 — CLAIM READINESS SCORING
Target table: intake_validation_result_output
════════════════════════════════════════════════════════════
2a. Call score_claim_readiness(claim_number).
    This writes completeness_score, missing_fields, docs_status,
    missing_docs, and overall_result to intake_validation_result_output.
    Safe to re-run — no pre-check needed.

════════════════════════════════════════════════════════════
STEP 3 — CLAIM SEGMENTATION & STP ROUTING
Target tables: stp_classification, segmentation_result_output
════════════════════════════════════════════════════════════
3a. Call get_claim_for_segmentation(claim_number) to load the claim data.
3b. Call compute_stp_score(claim_number).
    This writes stp_category to stp_classification and
    severity + complexity to segmentation_result_output.

════════════════════════════════════════════════════════════
STEP 4 — CLAIM FILED AUDIT LOG
Target table: policyholder_actions
════════════════════════════════════════════════════════════
4a. Call log_policyholder_action with:
      claim_number : the claim number extracted from the trigger message
      action_type  : "claim_filed"
      action_label : "Claim submitted via Smart Loss Reporting"

════════════════════════════════════════════════════════════
COMPLETION
════════════════════════════════════════════════════════════
After all four steps have run (success or error), output EXACTLY this line and nothing else:
DONE | claim={claim_number} | coverage={verdict or ERROR} | readiness={overall_result or ERROR} | stp={stp_category or ERROR}

Replace each placeholder with the actual value returned by the relevant tool,
or the word ERROR if that step failed.
"""


def load_prompt() -> str:
    if not PHOENIX_ENDPOINT:
        raise RuntimeError("Phoenix not configured")
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)
    prompt = client.prompts.get(name="fnol_orchestrator_agent_policyholder", label="production")
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
            agent_name = _TOOL_TO_AGENT.get(tool_name, "UnknownAgent")
            logger.info("▶ %-40s  tool → %s", f"[{agent_name}]", tool_name)
            yield f"data: [Tool: {tool_name}] Starting...\n\n"

        elif kind == "on_tool_end":
            tool_name = event.get("name", "unknown_tool")
            agent_name = _TOOL_TO_AGENT.get(tool_name, "UnknownAgent")
            logger.info("✓ %-40s  tool → %s", f"[{agent_name}]", tool_name)
            yield f"data: [Tool: {tool_name}] Done\n\n"


# ──────────────────────────────────────────────────────────────────────────────
# POST /transcribe — receive audio blob, call gpt-4o-transcribe-diarize REST
# ──────────────────────────────────────────────────────────────────────────────

def _convert_to_wav_16k(audio_bytes: bytes, src_mime: str) -> bytes:
    """Convert any audio format to WAV 16kHz mono PCM using ffmpeg."""
    import subprocess, tempfile, os
    suffix = ".webm" if "webm" in src_mime else ".ogg" if "ogg" in src_mime else ".mp4" if "mp4" in src_mime else ".audio"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src_f:
        src_f.write(audio_bytes)
        src_path = src_f.name
    out_path = src_path + ".wav"
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", src_path,
             "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out_path],
            capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            logger.warning("ffmpeg conversion failed: %s", result.stderr.decode()[:300])
            return audio_bytes
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        for p in (src_path, out_path):
            try:
                os.unlink(p)
            except OSError:
                pass


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    load_dotenv(find_dotenv())
    audio_bytes = await file.read()
    src_mime = file.content_type or "audio/webm"

    wav_bytes = await asyncio.get_running_loop().run_in_executor(
        None, _convert_to_wav_16k, audio_bytes, src_mime
    )
    logger.info(
        "Transcribe: original %d bytes (%s) → WAV %d bytes",
        len(audio_bytes), src_mime, len(wav_bytes),
    )

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                WHISPER_ENDPOINT,
                headers={"api-key": WHISPER_API_KEY},
                files={"file": ("audio.wav", wav_bytes, "audio/wav")},
                data={
                    "model": os.getenv("AZURE_WHISPER_DEPLOYMENT", "gpt-4o-transcribe-diarize"),
                    "language": "en",
                    "response_format": "json",
                },
            )
        if resp.status_code != 200:
            logger.error("Transcription API error %s: %s", resp.status_code, resp.text[:400])
            return JSONResponse(
                status_code=502,
                content={"error": f"Transcription failed ({resp.status_code})", "detail": resp.text[:400]},
            )
        data = resp.json()
        transcript = data.get("text", "")
        logger.info("Transcribed → %d chars: %s", len(transcript), transcript[:120])
        return {"transcript": transcript}
    except Exception as e:
        logger.exception("Transcription exception")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ──────────────────────────────────────────────────────────────────────────────
# POST /chat — text or browser-transcribed voice input
# ──────────────────────────────────────────────────────────────────────────────

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

    # Prepend today's date so the agent can resolve relative dates like "yesterday"
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
            if isinstance(e, asyncio.CancelledError):
                raise

    return StreamingResponse(generate(), media_type="text/event-stream")


async def _run_background_processing(claim_number: str) -> None:
    """Silently runs all post-submission agents for a claim. Called as a background task."""
    load_dotenv(find_dotenv())
    try:
        tools = await get_tools()
        model = AzureChatOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )
        graph = create_graph(model=model, tools=tools, prompt=_BACKGROUND_PROCESS_PROMPT)
        trigger = f"Background process claim {claim_number}"
        completion_parts: list[str] = []
        async for event in graph.astream_events(
            {"messages": [HumanMessage(content=trigger)]},
            config={"recursion_limit": 100},
            version="v2",
        ):
            kind = event.get("event", "")
            if kind == "on_tool_start":
                tool_name = event.get("name", "unknown_tool")
                agent_name = _TOOL_TO_AGENT.get(tool_name, "UnknownAgent")
                logger.info("▶ [BG] %-35s  tool → %s", f"[{agent_name}]", tool_name)
            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown_tool")
                agent_name = _TOOL_TO_AGENT.get(tool_name, "UnknownAgent")
                logger.info("✓ [BG] %-35s  tool → %s", f"[{agent_name}]", tool_name)
            elif kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    completion_parts.append(chunk.content)
        logger.info("Background processing complete for %s: %s", claim_number, "".join(completion_parts).strip())
    except Exception as e:
        logger.error("Background processing failed for %s: %s", claim_number, e, exc_info=True)


@app.post("/process")
async def process_claim(body: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Fire-and-forget endpoint triggered after Smart Loss Reporting submit.
    Returns 200 immediately; all post-submission agents run in the background.
    """
    if not body.claim_number or not body.claim_number.strip():
        return JSONResponse(status_code=400, content={"error": "claim_number is required"})
    background_tasks.add_task(_run_background_processing, body.claim_number.strip())
    logger.info("Background processing queued for claim %s", body.claim_number)
    return {"status": "processing", "claim_number": body.claim_number.strip()}


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "fnol_orchestrator_agent_policyholder"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
