# OrchestratorAgent (Brain Agent)

The Orchestrator is the "brain" agent for the Jarvis claims platform. It
holds the UNION of every tool exposed by the four persona agent sets
(Policyholder, Adjuster, SIU, VendorManager) — 46 sub-app MCP endpoints —
plus its own 6 orchestration tools (claim stage state + human-in-the-loop
approval gates), for a total of ~52 tools.

It drives a given `claim_id` through the full claim lifecycle (Intake ->
Triage -> Fraud Detection -> Damage Assessment -> Vendor Assignment -> SIU
branch (conditional) -> Reserve -> Settlement -> Payment -> Closure),
pausing at REQUIRED human approval gates and resuming where it left off on
re-run.

## Components

- `MCP/main.py` — FastAPI + FastApiMCP server on port **9200**, mounts the
  `orchestration` sub-app at `/api/v1/orchestration/mcp`.
- `MCP/orchestration_mcp/` — models.py + handler.py for orchestration tools.
- `MCP/orchestration_router.py` — FastAPI router exposing the 6 tools.
- `MCP/common/db.py`, `MCP/common/init_db.py` — shared SQLite DB helpers
  (same `PolicyholderAgents/data/policyholder.db`), creating
  `claim_orchestration_state` and `human_approval_requests` tables.
- `server.py` — LangGraph brain agent on port **9201**, `/chat` (SSE) and
  `/health`. Builds a `MultiServerMCPClient` config of 46 persona MCP
  entries + 1 orchestration entry (47 total).

## Orchestration MCP endpoints (port 9200, `/api/v1/orchestration`)

| operation_id | Method/Path |
|---|---|
| `get_claim_orchestration_state` | GET `/api/orchestration/state/{claim_id}` |
| `set_claim_orchestration_state` | POST `/api/orchestration/state/{claim_id}` |
| `create_approval_request` | POST `/api/orchestration/approvals/{claim_id}` |
| `get_pending_approvals` | GET `/api/orchestration/approvals/pending` |
| `decide_approval` | POST `/api/orchestration/approvals/{approval_id}/decide` |
| `get_approval_status` | GET `/api/orchestration/approvals/{claim_id}/{gate_type}/status` |

MCP tool endpoint: `http://0.0.0.0:9200/api/v1/orchestration/mcp`
Health: `http://0.0.0.0:9200/health`

## The 9 HITL gate_types

**REQUIRED / BLOCKING** — the brain agent creates the approval request,
calls `get_approval_status`, and STOPS ("End") until status is
`Approved` (or reports + stops if `Rejected`):

1. `damage_assessment_review`
2. `reserve_approval`
3. `settlement_approval`
4. `siu_decision_approval` (only if claim was escalated to SIU)
5. `payment_approval`
6. `claim_closure_approval`

**OPTIONAL / NON-BLOCKING** — created for audit/visibility only, the agent
proceeds immediately regardless of status:

7. `fnol_review`
8. `triage_approval`
9. `vendor_assignment_approval`

## MultiServerMCPClient config (server.py)

`config_mcp_server` is built programmatically from 4 slug lists:

- PolicyholderAgents (port 8800, 9 slugs): `voice_text_intake`,
  `duplicate_check`, `segmentation`, `claim_status`, `document_submission`,
  `feedback`, `policy_coverage`, `claim_readiness`, `communication`
- AdjusterAgents (port 8900, 15 slugs): `claim_classification`, `triage`,
  `fraud_screening`, `routing`, `evidence_validation`, `external_data`,
  `damage_assessment`, `verification`, `loss_assessment`,
  `reserve_recommendation`, `financial_leakage`, `repair_vs_replacement`,
  `settlement_recommendation`, `payment_eligibility`, `payment_trigger`
- SIUAgents (port 9000, 12 slugs): `fraud_risk_scoring`, `case_assignment`,
  `behavioral_analytics`, `entity_relationship`, `fraud_pattern`,
  `network_analysis`, `evidence_correlation`, `fraud_escalation`,
  `fraud_resolution`, `legal_escalation`, `watchlist_update`, `siu_closure`
- VendorManagerAgents (port 9100, 10 slugs): `vendor_onboarding`,
  `vendor_matching`, `vendor_qualification`, `vendor_capacity`,
  `vendor_cost_benchmark`, `dispatch`, `vendor_performance`,
  `sla_compliance`, `vendor_escalation`, `eta_prediction`
- OrchestratorAgent (port 9200, 1 slug): `orchestration`

Each entry: `{"url": "http://0.0.0.0:<port>/api/v1/<slug>/mcp", "transport":
"streamable_http", "timeout": timedelta(seconds=120), "sse_read_timeout":
timedelta(seconds=600)}`.

## Running

1. Initialize the shared DB (run AFTER the other 4 personas' `init_db.py`,
   since `claim_orchestration_state` seeding doesn't strictly require
   `claims` but follows the same ordering convention):
   ```
   py -3 OrchestratorAgent/MCP/common/init_db.py
   ```
2. Start ALL 5 MCP servers (required for the brain agent's full toolset):
   ```
   py -3 PolicyholderAgents/MCP/main.py    # port 8800
   py -3 AdjusterAgents/MCP/main.py        # port 8900
   py -3 SIUAgents/MCP/main.py             # port 9000
   py -3 VendorManagerAgents/MCP/main.py   # port 9100
   py -3 OrchestratorAgent/MCP/main.py     # port 9200
   ```
3. Start the brain agent:
   ```
   py -3 OrchestratorAgent/server.py       # port 9201
   ```
4. POST to `/chat` with `{"message": "Continue orchestration for claim
   CLM-2026-1001"}` (SSE response).

## Human approval workflow

Approvals are recorded via `decide_approval(approval_id, decision,
decided_by, notes=None)` where `decision` is `"Approved"` or `"Rejected"`.
A human/ops UI (not included here) would call this MCP tool/endpoint
directly, or via `POST /api/orchestration/approvals/{approval_id}/decide`
on port 9200. After a decision is recorded, re-running the brain agent for
the same `claim_id` will detect the approval and proceed to the next stage.
