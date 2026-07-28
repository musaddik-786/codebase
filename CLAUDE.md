# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jarvis Claims Agents V2 is a multi-agent AI insurance claims platform. It orchestrates a full end-to-end claim lifecycle through 47+ specialized agents organized into 5 personas (Policyholder, Adjuster, SIU, VendorManager, Orchestrator), backed by Azure OpenAI and Azure PostgreSQL, with a React/Vite/TypeScript frontend.

## Commands

### Backend (Python)

```bash
# Install dependencies (requirements.txt is shared across all persona folders)
pip install -r PolicyholderAgents/requirements.txt
# (PolicyholderAgents/requirements.txt additionally pins azure-storage-blob for evidence uploads; otherwise identical across personas)

# Initialize databases — idempotent, run once per persona in order:
python PolicyholderAgents/MCP/common/init_db.py
python AdjusterAgents/MCP/common/init_db.py
python SIUAgents/MCP/common/init_db.py
python VendorManagerAgents/MCP/common/init_db.py
python OrchestratorAgent/MCP/common/init_db.py

# Start MCP tool servers (one per persona):
python PolicyholderAgents/MCP/main.py    # port 7700
python AdjusterAgents/MCP/main.py        # port 8900 (see Known Pitfalls — currently hardcoded to 5800)
python SIUAgents/MCP/main.py             # port 9000
python VendorManagerAgents/MCP/main.py   # port 9100
python OrchestratorAgent/MCP/main.py     # port 9200

# Start individual agent servers (examples):
python PolicyholderAgents/VoiceTextIntakeAgent/server.py  # port 7701
python OrchestratorAgent/server.py                        # port 9201
# Each agent has its own server.py
```

### Frontend — ClaimsUI (active)

```bash
cd ClaimsUI
npm install   # first time only
npm run dev   # http://localhost:5173
npm run build # tsc -b && vite build → dist/
```

Routes: `/` (Home), `/policyholder`, `/adjuster`, `/siu`, `/vendor-manager`, `/orchestrator`.

### Frontend — hexaware-claims-portal (alternative)

```bash
cd hexaware-claims-portal
npm install
npm run dev        # http://localhost:5173
npm run build
npm run typecheck  # TypeScript check (no emit)
```

### No automated test suite

There are no pytest, ruff, mypy, or ESLint configs in this repo. Validation is done manually via curl or the frontend. The only type-check available is `npm run typecheck` in `hexaware-claims-portal`.

### Testing an agent manually

```bash
# Health check
curl http://localhost:7701/health

# Chat (SSE streaming)
curl -N -X POST http://localhost:7701/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I need to file a claim for water damage"}'

# Chat with history and input_type
curl -N -X POST http://localhost:7701/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "follow up question",
    "input_type": "text",
    "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
  }'
```

The `/chat` `ChatRequest` schema accepts:
- `message` (required) — current user message
- `input_type` (optional) — `"text"` or `"voice_transcript"`; prepended as `[input_type: ...]` tag
- `history` (optional) — `List[{role, content}]` conversation turns; agents rebuild full graph state from this on every call (no server-side session persistence)

## Architecture

### Process Model

Each persona runs **two separate process types**:

1. **MCP Server** (one per persona): A FastAPI app that mounts N tool sub-apps, each wrapped with `FastApiMCP(...).mount_http()`. Exposes tools at `/api/v1/<tool_slug>/mcp`.

2. **Agent Servers** (one per agent, 47 total): Standalone FastAPI + LangGraph processes. Each connects back to its persona's MCP server via `MultiServerMCPClient` to get tools, then exposes:
   - `POST /chat` — SSE streaming endpoint; accepts `{"message": "..."}`, streams `data: {chunk}\n\n`
   - `GET /health` — health check

### LangGraph Agent Pattern

All 47 agents follow an identical pattern: `State(messages)` → `agent_node` (LLM + bound tools) → `router` (checks for tool calls → ToolNode loop, or END) → compile → stream via `graph.astream_events(..., version="v2")`. System prompts are loaded from `Phoenix` if configured, otherwise fall back to hardcoded strings.

### Orchestrator Brain

`OrchestratorAgent/server.py` aggregates all 47+ persona MCP endpoints into one `MultiServerMCPClient`, giving the orchestrator ~52 tools representing the entire claim lifecycle. It drives: **Intake → Triage → Fraud Detection → Damage Assessment → Vendor Assignment → [SIU Branch] → Reserve → Settlement → Payment → Closure**.

There are **9 HITL gates** managed via the `human_approval_requests` table — 6 blocking and 3 audit-only:

- **Blocking** (orchestrator waits): `damage_assessment_review`, `reserve_approval`, `settlement_approval`, `siu_decision_approval`, `payment_approval`, `claim_closure_approval`
- **Audit-only** (created for visibility, don't block flow): `fnol_review`, `triage_approval`, `vendor_assignment_approval`

Approve/reject via:
```bash
POST http://localhost:9200/api/v1/orchestration/approvals/{approval_id}/decide
{"decision": "approved", "decided_by": "adjuster_1", "notes": ""}
```

### MCP Tool Server Structure

Each persona's `MCP/` folder follows:
```
MCP/
├── main.py                  # FastAPI app, mounts sub-apps
├── common/
│   ├── db.py                # get_db_connection(), row_to_dict()
│   └── init_db.py           # CREATE TABLE IF NOT EXISTS + seed data
├── <tool>_router.py         # FastAPI endpoints per tool
└── <tool>_mcp/
    ├── models.py            # Pydantic request/response models
    └── handler.py           # Business logic
```

The `operation_id` on each FastAPI route becomes the MCP tool name visible to agents. `FastApiMCP(...).include_operations([...])` whitelists which routes are exposed as tools — routes without a matching `operation_id` in that list are not surfaced.

### Shared Database

All personas share **one PostgreSQL database** (`claimsagenticdb.postgres.database.azure.com`). Tables are created by `init_db.py` scripts across personas. Core tables: `claims`, `claims_master`, `claim_journey_master`, `policy_details`. Persona-specific tables are prefixed by domain (e.g., `siu_case_master`, `vendor_master_input`).

### Frontend Differences

| | ClaimsUI | hexaware-claims-portal |
|---|---|---|
| Router | `react-router-dom` (`BrowserRouter`) | Wouter |
| Agent config | `src/config/agents.ts` (central port map) | Per-component hardcoded URLs |
| Persona UI | All 5 personas have pages | Only Policyholder is fully built |
| FNOL | Agent chat panels per tool | 6-step wizard (`src/components/fnol/`) |

`ClaimsUI/src/config/agents.ts` is the single source of truth for all backend ports in the ClaimsUI — update it when ports change rather than hunting through components. Each agent entry also carries a `status` field (`"full"` or `"placeholder"`) indicating production readiness; placeholder agents return stub/hardcoded data.

## Environment

A single `.env` file at the repo root is loaded by all agents via `load_dotenv(find_dotenv())`. Required variables:

```
AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_PG_HOST, AZURE_PG_PORT, AZURE_PG_DATABASE, AZURE_PG_USER, AZURE_PG_PASSWORD
AZURE_PG_SSLMODE=require
```

Optional:
- `PHOENIX_ENDPOINT` / `PHOENIX_API_KEY` — LLM observability (Arize Phoenix); agents fall back to hardcoded system prompts if unset
- `AZURE_STORAGE_CONNECTION_STRING` / `AZURE_STORAGE_CONTAINER_NAME` — blob evidence storage; falls back to `data/uploads/` locally
- `AZURE_WHISPER_ENDPOINT` / `AZURE_WHISPER_API_KEY` / `AZURE_WHISPER_DEPLOYMENT_NAME` — voice transcription (VoiceTextIntakeAgent only; uses `gpt-4o-transcribe-diarize`)
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` — document embeddings (DocumentSubmissionAgent)
- Guidewire: `GW_PC_BASE_URL` / `GW_CC_BASE_URL` / `GW_AUTHORIZATION` (Basic auth) / `GW_TIMEOUT_SECONDS`

## Port Reference

| Persona | MCP Server | Agent Ports |
|---|---|---|
| Policyholder | **7700** | **7701–7709**, 7710 (FNOLOrchestrator — combines VoiceTextIntake + DocumentSubmission into a single end-to-end FNOL flow) |
| Adjuster | 8900 | 8901–8915 |
| SIU | 9000 | 9001–9012 |
| VendorManager | 9100 | 9101–9110 |
| Orchestrator | 9200 | 9201 |

Note: Policyholder was remapped from 8800/8801–8809 to 7700/7701–7709 because those ports were already in use on the deployment machine.

## Known Pitfalls

- **`fnol_mandatory_fields` column name**: The DB schema uses `display_order`; any query using `ORDER BY field_order` will fail and — because `conn.autocommit = False` — leaves the transaction in an aborted state, causing all subsequent queries on the same connection to also fail. Always call `conn.rollback()` in except blocks before reusing a connection.

- **DocumentSubmissionAgent MCP URL**: Its `MCP_URL` must point to the Policyholder MCP server (`http://localhost:7700/api/v1/document_submission/mcp`). The tool is registered on the shared MCP server, not on a separate port.

- **PostgreSQL transaction state**: With `autocommit = False`, a failed query in an inner `try/except` that doesn't rollback will poison all subsequent queries in that connection. Always `conn.rollback()` in exception handlers before continuing to use the connection.

- **MCP client timeouts**: All agents configure `MultiServerMCPClient` with `timeout=120` and `sse_read_timeout=600`. The OrchestratorAgent graph runs with `{"recursion_limit": 250}`. If an agent hangs, check that its MCP server is up before tuning these values.

- **OrchestratorAgent Policyholder port**: `OrchestratorAgent/server.py` line ~138 hardcodes port `8800` for Policyholder MCP (`_mcp_entry(slug, 8800)`). This deployment remapped Policyholder to port `7700`. If the orchestrator can't reach Policyholder tools, update that line to `7700`.

- **Stub agents**: Several agents (e.g., `PolicyCoverageVerificationAgent`) implement only stub/placeholder tools. Don't assume all 47 agents are production-ready — check `handler.py` for `_stub` or hardcoded return values.

- **Per-persona README files are stale**: The `README.md` files inside each persona folder reference the original ports (8800/8801–8809) and describe an older SQLite-based DB. Treat them as architectural documentation only — the actual running configuration uses the ports in the table above and Azure PostgreSQL. `TEST_GUIDE.md`'s table of contents is also stale in the same way (still lists Policyholder as 8801–8809).

- **`AdjusterAgents/MCP/main.py` hardcodes the wrong port**: Its `uvicorn.run(...)` call is hardcoded to port `5800`, not `8900` as the Port Reference table describes. Running it directly starts on 5800 — pass `--port 8900` or fix the hardcoded value if agents can't reach the Adjuster MCP server on the documented port.

## Test Data

Sample data seeded by `init_db.py`: policy `POL-1001` (Homeowners), claim `CLM-2026-1001`. See `TEST_GUIDE.md` for full per-agent test cases and lifecycle ordering.

`test.sql` at the repo root has useful ad-hoc queries for inspecting claim state, HITL approval records, and journey steps directly against the DB.

## Additional References

- `workflow_explanation.md` — end-to-end narrative walkthrough of all four personas and two FNOL paths (Standard + Motor). Good orientation before reading agent code.
- `hexaware-claims-portal` supports a **Motor FNOL** path (vehicle accidents) with additional fields for vehicle details, driver info, and accident circumstances — this is distinct from the Standard FNOL used in ClaimsUI.

## Notes on Python Environments

Each persona folder (`PolicyholderAgents/`, `AdjusterAgents/`, etc.) may contain its own `venv`/`vnev` directory. The `requirements.txt` files are identical across personas — one shared install is sufficient, but activate the correct venv or use the repo-root environment when running agents.
