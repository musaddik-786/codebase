# Policyholder Agents

A set of 9 agents for the "Policyholder" persona of the claims platform,
backed by a local SQLite database (`data/policyholder.db`) and a local
file folder for document uploads (`data/uploads/`).

## Architecture

- `MCP/main.py` — single FastAPI MCP server (port **8800**) hosting all 9
  agent tool sub-apps under `/api/v1/<slug>`, each wrapped with
  `FastApiMCP(...).mount_http()` exposing an MCP endpoint at
  `/api/v1/<slug>/mcp`. Initializes the SQLite DB on startup.
- `MCP/common/db.py` — `get_db_connection()` / `row_to_dict()` helpers.
- `MCP/common/init_db.py` — creates all tables (idempotent) and seeds
  reference data (mandatory FNOL fields, sample policy `POL-1001`/`POL-1002`,
  sample claim `CLM-2026-1001`).
- Each `<AgentName>Agent/server.py` — LangGraph agent with a FastAPI
  `/chat` SSE endpoint and `/health`, connecting to its MCP sub-app via
  `MultiServerMCPClient`.

## Agents

| # | Agent | Slug | MCP mount | Agent port | Status |
|---|-------|------|-----------|------------|--------|
| 1 | VoiceTextIntakeAgent | `voice_text_intake` | `/api/v1/voice_text_intake` | 8801 | FULL |
| 2 | DuplicateClaimCheckAgent | `duplicate_check` | `/api/v1/duplicate_check` | 8802 | FULL |
| 3 | ClaimSegmentationAgent | `segmentation` | `/api/v1/segmentation` | 8803 | FULL |
| 4 | ClaimStatusAgent | `claim_status` | `/api/v1/claim_status` | 8804 | FULL |
| 5 | DocumentSubmissionAgent | `document_submission` | `/api/v1/document_submission` | 8805 | FULL |
| 6 | FeedbackAgent | `feedback` | `/api/v1/feedback` | 8806 | FULL |
| 7 | PolicyCoverageVerificationAgent | `policy_coverage` | `/api/v1/policy_coverage` | 8807 | PLACEHOLDER |
| 8 | ClaimReadinessAgent | `claim_readiness` | `/api/v1/claim_readiness` | 8808 | PLACEHOLDER |
| 9 | CommunicationAgent | `communication` | `/api/v1/communication` | 8809 | PLACEHOLDER |

### Placeholder notes

- **PolicyCoverageVerificationAgent**: only `get_policy_details_stub` (real
  read of `policy_details`) is implemented. Coverage-vs-loss verification
  logic for this local-DB platform is TODO.
- **ClaimReadinessAgent**: only `get_intake_validation_result_stub` (real
  read of `intake_validation_result_output`) is implemented.
  Completeness-scoring against `fnol_mandatory_fields` is TODO.
- **CommunicationAgent**: only `get_communication_history_stub` (real read
  of `communication_history`) is implemented. Auto-drafting of
  status-change notifications is TODO.

## Configuration

Each agent reads Azure OpenAI credentials from its own `.env` (chat
deployment `gpt-4.1-jarvis`, API version `2025-01-01-preview`), plus
`MCP_URL` (pointing at its MCP sub-app's `/mcp` endpoint on port 8800) and
`AGENT_PORT`. The root `PolicyholderAgents/.env` holds the shared Azure
OpenAI config plus `AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large`
(used by DocumentSubmissionAgent for document-type classification).

`PHOENIX_ENDPOINT` / `PHOENIX_API_KEY` are left blank — all agents fall back
to their built-in `_FALLBACK_PROMPT` when Phoenix is not configured.

## Running

```bash
# 1. Install dependencies (from PolicyholderAgents/)
pip install -r requirements.txt

# 2. Start the MCP tool server (initializes the SQLite DB automatically)
python MCP/main.py

# 3. In separate terminals, start any of the agents
python VoiceTextIntakeAgent/server.py
python DuplicateClaimCheckAgent/server.py
python ClaimSegmentationAgent/server.py
python ClaimStatusAgent/server.py
python DocumentSubmissionAgent/server.py
python FeedbackAgent/server.py
python PolicyCoverageVerificationAgent/server.py   # placeholder
python ClaimReadinessAgent/server.py               # placeholder
python CommunicationAgent/server.py                # placeholder
```

Each agent exposes:
- `POST /chat` — SSE streaming chat endpoint (`{"message": "..."}`)
- `GET /health` — health check

## Sample data

- Policy `POL-1001` (Homeowners, Active, deductible 1000, limit 250000)
- Policy `POL-1002` (Auto, Active, deductible 500, limit 50000)
- Claim `CLM-2026-1001` (policy `POL-1001`, status `Open`, journey stage 1
  "Claim Initiated")
