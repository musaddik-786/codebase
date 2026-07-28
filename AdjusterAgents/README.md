# Adjuster Agents

A set of 15 agents for the "Claims Adjuster" persona of the claims
platform. This persona SHARES the SQLite database with PolicyholderAgents
(`PolicyholderAgents/data/policyholder.db`) — claims, policy_details, and
other core records are common across personas. No separate database file is
created for this persona.

## Architecture

- `MCP/main.py` — single FastAPI MCP server (port **8900**) hosting all 15
  agent tool sub-apps under `/api/v1/<slug>`, each wrapped with
  `FastApiMCP(...).mount_http()` exposing an MCP endpoint at
  `/api/v1/<slug>/mcp`. Initializes the shared SQLite DB (new tables) on
  startup.
- `MCP/common/db.py` — `get_db_connection()` / `row_to_dict()` helpers,
  resolving to `PolicyholderAgents/data/policyholder.db`.
- `MCP/common/init_db.py` — creates all new Adjuster-persona tables
  (idempotent, `CREATE TABLE IF NOT EXISTS`) and seeds reference data
  (auto-adjudication threshold configs, and an `adjuster_findings` row for
  sample claim `CLM-2026-1001`). Safe to run before or after
  PolicyholderAgents' `init_db`.
- Each `<AgentName>Agent/server.py` — LangGraph agent with a FastAPI
  `/chat` SSE endpoint and `/health`, connecting to its MCP sub-app via
  `MultiServerMCPClient`.

## Agents

| # | Agent | Slug | MCP mount | Agent port | Status |
|---|-------|------|-----------|------------|--------|
| 1 | ClaimClassificationAgent | `claim_classification` | `/api/v1/claim_classification` | 8901 | FULL |
| 2 | TriageAgent | `triage` | `/api/v1/triage` | 8902 | PLACEHOLDER |
| 3 | FraudScreeningAgent | `fraud_screening` | `/api/v1/fraud_screening` | 8903 | FULL |
| 4 | RoutingAgent | `routing` | `/api/v1/routing` | 8904 | PLACEHOLDER |
| 5 | EvidenceValidationAgent | `evidence_validation` | `/api/v1/evidence_validation` | 8905 | PLACEHOLDER |
| 6 | ExternalDataAgent | `external_data` | `/api/v1/external_data` | 8906 | FULL |
| 7 | DamageAssessmentAgent | `damage_assessment` | `/api/v1/damage_assessment` | 8907 | FULL |
| 8 | VerificationAgent | `verification` | `/api/v1/verification` | 8908 | FULL |
| 9 | LossAssessmentAgent | `loss_assessment` | `/api/v1/loss_assessment` | 8909 | FULL |
| 10 | ReserveRecommendationAgent | `reserve_recommendation` | `/api/v1/reserve_recommendation` | 8910 | PLACEHOLDER |
| 11 | FinancialLeakageAgent | `financial_leakage` | `/api/v1/financial_leakage` | 8911 | PLACEHOLDER |
| 12 | RepairVsReplacementAgent | `repair_vs_replacement` | `/api/v1/repair_vs_replacement` | 8912 | FULL |
| 13 | SettlementRecommendationAgent | `settlement_recommendation` | `/api/v1/settlement_recommendation` | 8913 | PLACEHOLDER |
| 14 | PaymentEligibilityAgent | `payment_eligibility` | `/api/v1/payment_eligibility` | 8914 | PLACEHOLDER |
| 15 | PaymentTriggerAgent | `payment_trigger` | `/api/v1/payment_trigger` | 8915 | FULL |

### Placeholder notes

- **TriageAgent**: only `get_claim_triage` (real read of `claim_triage`) is
  implemented. Dedicated prioritization/SLA-risk scoring logic combining
  severity + complexity + fraud_risk_score into a priority queue ranking is
  TODO.
- **RoutingAgent**: only `get_auto_assignment_log` (real read of
  `auto_assignment_log`) is implemented. Agentic adjuster/team assignment
  logic beyond static rules (load-balancing, skill matching) is TODO.
- **EvidenceValidationAgent**: only `get_evidence_items` (real read of
  `evidence_items`) is implemented. Evidence authenticity/completeness
  verification logic (cross-checking against fnol_evidence/documents,
  flagging missing required evidence types) is TODO.
- **ReserveRecommendationAgent**: only `get_adjuster_findings` (real read of
  `adjuster_findings`, including `adjusted_reserve`) is implemented. Reserve
  calculation logic deriving a recommended reserve from loss_assessments +
  fraud_risk + severity is TODO.
- **FinancialLeakageAgent**: only `get_cost_variance` (real read of
  `cost_variance_output`) is implemented. Claim-level leakage scoring
  aggregating cost variance across vendors/line items is TODO.
- **SettlementRecommendationAgent**: only `get_ai_decision_recommendation`
  (real read of `ai_decision_recommendations`) is implemented. Settlement
  amount calculation combining loss_estimation_outputs, repair-vs-replace
  decisions, and policy limits/deductibles is TODO.
- **PaymentEligibilityAgent**: only `get_auto_adjudication_thresholds` (real
  read of all `auto_adjudication_threshold_configs` rows) is implemented.
  Eligibility gating logic comparing a claim's loss amount/severity/
  complexity against these thresholds is TODO.

## Configuration

Each agent reads Azure OpenAI credentials from its own `.env` (chat
deployment `gpt-4.1-jarvis`, API version `2025-01-01-preview`), plus
`MCP_URL` (pointing at its MCP sub-app's `/mcp` endpoint on port 8900) and
`AGENT_PORT`. The root `AdjusterAgents/.env` holds the shared Azure OpenAI
config (copied verbatim from `PolicyholderAgents/.env`) plus
`MCP_BASE_URL="http://0.0.0.0:8900"`.

`PHOENIX_ENDPOINT` / `PHOENIX_API_KEY` are left blank — all agents fall back
to their built-in `_FALLBACK_PROMPT` when Phoenix is not configured.

## Running

```bash
# 1. Install dependencies (from AdjusterAgents/)
pip install -r requirements.txt

# 2. Initialize the shared SQLite DB (safe to run first or after
#    PolicyholderAgents' init_db — both are idempotent/defensive)
python MCP/common/init_db.py

# 3. Start the MCP tool server (also re-runs init_db on startup)
python MCP/main.py

# 4. In separate terminals, start any of the agents
python ClaimClassificationAgent/server.py     # 8901
python TriageAgent/server.py                  # 8902 - placeholder
python FraudScreeningAgent/server.py          # 8903
python RoutingAgent/server.py                 # 8904 - placeholder
python EvidenceValidationAgent/server.py      # 8905 - placeholder
python ExternalDataAgent/server.py            # 8906
python DamageAssessmentAgent/server.py        # 8907
python VerificationAgent/server.py            # 8908
python LossAssessmentAgent/server.py          # 8909
python ReserveRecommendationAgent/server.py   # 8910 - placeholder
python FinancialLeakageAgent/server.py        # 8911 - placeholder
python RepairVsReplacementAgent/server.py     # 8912
python SettlementRecommendationAgent/server.py # 8913 - placeholder
python PaymentEligibilityAgent/server.py      # 8914 - placeholder
python PaymentTriggerAgent/server.py          # 8915
```

Each agent exposes:
- `POST /chat` — SSE streaming chat endpoint (`{"message": "..."}`)
- `GET /health` — health check

## Shared sample data

This platform shares `PolicyholderAgents/data/policyholder.db`, including:

- Policy `POL-1001` (Homeowners, Active, deductible 1000, limit 250000)
- Policy `POL-1002` (Auto, Active, deductible 500, limit 50000)
- Claim `CLM-2026-1001` (policy `POL-1001`, status `Open`)

`AdjusterAgents/MCP/common/init_db.py` additionally seeds:

- `auto_adjudication_threshold_configs`: `DEFAULT` (max_loss_amount 10000,
  max_severity_level Medium, max_complexity_level Simple) and `HIGH_VALUE`
  (25000 / High / Moderate).
- `adjuster_findings` for `CLM-2026-1001` (adjuster_name "Auto-Seed",
  coverage_confirmed "Pending", fraud_risk "Low" / score 10,
  repair_vs_replace "TBD", adjusted_reserve 5000).
