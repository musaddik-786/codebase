"""
server.py — Voice/Text Intake Agent (Policyholder)
─────────────────────────────────────────────────────
LangGraph-based FastAPI agent that captures FNOL via text or
voice (recorded in browser, transcribed via gpt-4o-transcribe-diarize REST).

Port: 7701
MCP : http://localhost:7720/api/v1/voice_text_intake/mcp

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
from fastapi import FastAPI, File, Request, UploadFile
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
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
logger = logging.getLogger("voice_text_intake_agent")

PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "")
MCP_URL = os.getenv("MCP_URL", "http://localhost:7720/api/v1/voice_text_intake/mcp")
AGENT_PORT = int(os.getenv("AGENT_PORT", "7701"))

WHISPER_ENDPOINT = os.getenv(
    "AZURE_WHISPER_ENDPOINT",
    "https://azureclaimsopenai.openai.azure.com/openai/deployments/gpt-4o-transcribe-diarize/audio/transcriptions?api-version=2025-03-01-preview",
)
WHISPER_API_KEY = os.getenv("AZURE_WHISPER_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY", "")

config_mcp_server = {
    "voice_text_intake_mcp": {
        "url": MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    },
}

app = FastAPI(title="Voice/Text Intake Agent (Policyholder)")

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
You are the Voice/Text Intake Agent for an insurance claims management platform.

Your role is to capture a First Notice of Loss (FNOL) from a policyholder.
The policyholder's message may be:
  - Typed text
  - A server-transcribed voice recording (input_type="voice_transcript")

Messages may begin with a [POLICY_CONTEXT: ...] tag containing pre-verified policy
details (policy_number, policyholder_name, policyholder_address, status, coverage_type, effective_date).
If this tag is present:
  - DO NOT ask for the policy number, policyholder name, or policyholder address — you already have them.
  - Extract policy_number from the tag and immediately call get_fnol_by_policy.
  - Call create_fnol_submission (or resume the existing draft) then immediately call
    update_fnol_submission to set policy_number, policyholder_name, and policyholder_address
    from the tag values.
  - Call save_field_attribution for each of those three fields with source="guidewire_lookup"
    so the audit trail records they were auto-filled from Guidewire.
  - Proceed directly to collecting loss details — do not ask for any policy information.

Follow this workflow exactly:

1. IDENTIFY THE POLICYHOLDER
   - If [POLICY_CONTEXT:] is present, extract policy_number from it — skip asking.
   - Otherwise ask for their policy number.
   - Call get_fnol_by_policy to check for any existing open FNOL submissions.
   - If an open draft exists, resume it; otherwise call create_fnol_submission.

2. COLLECT LOSS DETAILS (conversational Q&A)
   - Call get_mandatory_fields to retrieve the required field list.
   - For each mandatory field not yet captured, ask the policyholder the
     corresponding inference_question from the mandatory fields list.
   - After each answer, call log_question_answer to persist the exchange.

3. EXTRACT FIELDS FROM THE USER'S MESSAGE
   - Call extract_fnol_fields_from_text directly with the user's message as
     raw_text and the appropriate input_type ("voice_transcript" or "text").
     This automatically saves extraction + inference records.

4. AFTER EXTRACTION
   - Call update_fnol_submission to persist all extracted fields onto the FNOL.
   - Call save_field_attribution with source details for each field.
   - For any mandatory field still missing, ask the policyholder directly.
   - Keep calling log_question_answer for each follow-up exchange.

5. REVIEW & CONFIRM
   - Summarise all captured details back to the policyholder.
   - Ask them to confirm or correct any values.
   - Call update_fnol_submission for any corrections.

6. SUBMIT
   - Before calling submit_fnol, call update_fnol_submission one final time to
     make sure policyholder_name, policyholder_address, and policy_number are set — use
     values from [POLICY_CONTEXT:] if present. Do NOT skip this step even if
     you believe the fields were saved earlier.
   - Then call submit_fnol. This creates the claim record.
   - The tool will return {"claim_number": "CLM-XXXX", "status": "submitted"}.
     This is always a success — do NOT treat it as an error regardless of what
     the fnol record fields contain.
   - Report the assigned claim_number back to the policyholder.

Always be empathetic. The policyholder may be distressed. Keep questions
concise and clear. Do not ask for information you can already infer with
high confidence from prior input.

When you have completed the task, end your response with "End".
"""


def load_prompt() -> str:
    if not PHOENIX_ENDPOINT:
        raise RuntimeError("Phoenix not configured")
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)
    prompt = client.prompts.get(name="voice_text_intake_agent_policyholder", label="production")
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
            return audio_bytes  # fall back to original
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

    # Convert to WAV 16kHz mono — dramatically improves transcription accuracy
    wav_bytes = await asyncio.get_running_loop().run_in_executor(
        None, _convert_to_wav_16k, audio_bytes, src_mime
    )
    send_bytes = wav_bytes
    send_name = "audio.wav"
    send_mime = "audio/wav"
    logger.info(
        "Transcribe: original %d bytes (%s) → WAV %d bytes",
        len(audio_bytes), src_mime, len(wav_bytes),
    )

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                WHISPER_ENDPOINT,
                headers={"api-key": WHISPER_API_KEY},
                files={"file": (send_name, send_bytes, send_mime)},
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

    user_message = body.message
    if body.input_type:
        user_message = f"[input_type: {body.input_type}] {user_message}"

    # Rebuild full conversation history from client-supplied turns
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
            import asyncio
            if isinstance(e, asyncio.CancelledError):
                raise

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "voice_text_intake_agent_policyholder"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
