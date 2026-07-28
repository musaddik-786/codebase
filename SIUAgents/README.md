# SIU Agents

A set of 12 agents for the "SIU (Special Investigation Unit)" persona of the
claims platform. This persona SHARES the SQLite database with
PolicyholderAgents and AdjusterAgents
(`PolicyholderAgents/data/policyholder.db`) — claims, policy_details,
fraud_risk_snapshots, ai_fraud_signals, fraud_flags, investigation_notes,
and other core/shared records are common across personas. No separate
database file is created for this persona.

## Architecture

- `MCP/main.py` — single FastAPI MCP server (port **9000**) hosting all 12
  agent tool sub-apps under `/api/v1/<slug>`, each wrapped with
  `FastApiMCP(...).mount_http()` exposing an MCP endpoint at
  `/api/v1/<slug>/mcp`. Initializes the shared SQLite DB (new tables) on
  startup.
- `MCP/common/db.py` — `get_db_connection()` / `row_to_dict()` helpers,
  resolving to `PolicyholderAgents/data/policyholder.db`.
- `MCP/common/init_db.py` — creates all new SIU-persona tables (idempotent,
  `CREATE TABLE IF NOT EXISTS`), re-declares shared fraud tables
  (`fraud_risk_snapshots`, `ai_fraud_signals`, `fraud_flags`,
  `investigation_notes`) defensively, and seeds reference data for sample
  claim `CLM-2026-1001` (an `siu_case_master` row, `siu_claim_master` row,
  `siu_progress_tracker` row, and a couple `investigation_notes` rows).
  Safe to run before or after PolicyholderAgents'/AdjusterAgents' `init_db`.
- Each `<AgentName>Agent/server.py` — LangGraph agent with a FastAPI
  `/chat` SSE endpoint and `/health`, connecting to its MCP sub-app via
  `MultiServerMCPClient`.

## Agents

| # | Agent | Slug | MCP mount | Agent port | Status |
|---|-------|------|-----------|------------|--------|
| 1 | FraudRiskScoringAgent | `fraud_risk_scoring` | `/api/v1/fraud_risk_scoring` | 9001 | FULL |
| 2 | CaseAssignmentAgent | `case_assignment` | `/api/v1/case_assignment` | 9002 | PLACEHOLDER |
| 3 | BehavioralAnalyticsAgent | `behavioral_analytics` | `/api/v1/behavioral_analytics` | 9003 | PLACEHOLDER |
| 4 | EntityRelationshipAgent | `entity_relationship` | `/api/v1/entity_relationship` | 9004 | PLACEHOLDER |
| 5 | FraudPatternAgent | `fraud_pattern` | `/api/v1/fraud_pattern` | 9005 | FULL |
| 6 | NetworkAnalysisAgent | `network_analysis` | `/api/v1/network_analysis` | 9006 | PLACEHOLDER |
| 7 | EvidenceCorrelationAgent | `evidence_correlation` | `/api/v1/evidence_correlation` | 9007 | PLACEHOLDER |
| 8 | FraudEscalationAgent | `fraud_escalation` | `/api/v1/fraud_escalation` | 9008 | FULL |
| 9 | FraudResolutionAgent | `fraud_resolution` | `/api/v1/fraud_resolution` | 9009 | FULL |
| 10 | LegalEscalationAgent | `legal_escalation` | `/api/v1/legal_escalation` | 9010 | FULL |
| 11 | WatchlistUpdateAgent | `watchlist_update` | `/api/v1/watchlist_update` | 9011 | FULL |
| 12 | SIUClosureAgent | `siu_closure` | `/api/v1/siu_closure` | 9012 | PLACEHOLDER |

### FULL agent notes

- **FraudRiskScoringAgent**: `recompute_fraud_risk_score` reads all
  `ai_fraud_signals` and `fraud_flags` for a claim, computes an aggregate
  `fraud_score` (average of signal scores, boosted if any active flag has
  `risk_score >= 70`), `red_flag_count` (active fraud_flags), and
  `prior_claims`/`vendor_risk` heuristics, then writes a new
  `fraud_risk_snapshots` row.
- **FraudPatternAgent**: `detect_fraud_patterns` uses an LLM (JSON response
  format) to identify 0-3 known fraud typologies (`staged_loss`,
  `inflated_estimate`, `rapid_repeat_claim`, `vendor_collusion`) from a
  claim's signals/flags, writes `vendor_red_flags` for Medium/High/Critical
  patterns (if `vendor_id` given), and `fraud_risk_flags_output` rows for
  every identified pattern.
- **FraudEscalationAgent**: `forward_to_siu` creates an
  `siu_escalation_records` row, opens a new `siu_case_master` row, logs a
  "Case Opened" `siu_timeline_events` row, and inserts a matching
  `siu_claim_master` row (with `fraud_flag` set if the claim's fraud score
  is >= 70).
- **FraudResolutionAgent**: `resolve_siu_case` records an `siu_decision`
  ("Fraud Confirmed" / "Fraud Cleared" / "Inconclusive"), closes the
  `siu_case_master` row, updates the related `siu_escalation_records`
  status, logs a "Case Resolved" timeline event and activity log entry, and
  (if confirmed) sets `siu_claim_master.fraud_flag`.
- **LegalEscalationAgent**: `refer_to_legal` checks the most recent SIU
  decision for a claim; if "Fraud Confirmed", creates a `legal_escalations`
  row (status "Pending Review") and logs an activity entry. Otherwise
  explains referral is not applicable.
- **WatchlistUpdateAgent**: `update_watchlist_from_case` checks the most
  recent SIU decision for a claim; if "Fraud Confirmed", adds the
  policyholder to `fraud_watchlist` with severity "High". `check_watchlist`
  looks up active watchlist entries for any entity_id.

### Placeholder notes

- **CaseAssignmentAgent**: only `get_siu_case_master` (real read of
  `siu_case_master`) is implemented. Investigator assignment/workload-
  balancing logic (round-robin or skill-based assignment of
  `assigned_investigator`) is TODO.
- **BehavioralAnalyticsAgent**: only `get_siu_activity_log` (real read of
  `siu_activity_log`) is implemented. Behavioral pattern analytics across
  claimant/vendor interaction history (frequency, timing anomalies,
  communication tone shifts) is TODO.
- **EntityRelationshipAgent**: only `get_fraud_network_graph` (real read of
  `fraud_network_graph`) is implemented. Entity relationship graph
  construction/traversal logic linking claimants, vendors, adjusters,
  addresses across claims is TODO.
- **NetworkAnalysisAgent**: only `get_vendor_network_signals` (real read of
  `vendor_network_signals`) is implemented. Graph-based collusion/fraud-ring
  detection across `fraud_network_graph` + `vendor_network_signals` is TODO.
- **EvidenceCorrelationAgent**: only `get_investigation_notes` (real read of
  `investigation_notes`) is implemented. Cross-referencing evidence across
  `documents`, `investigation_notes`, and `siu_timeline_events` to detect
  inconsistencies between sources is TODO.
- **SIUClosureAgent**: only `get_siu_progress_tracker` (real read of
  `siu_progress_tracker`) is implemented. Closure-readiness checklist logic
  validating all investigation steps are complete before final case closure
  is TODO.

## Configuration

Each agent reads Azure OpenAI credentials from its own `.env` (chat
deployment `gpt-4.1-jarvis`, API version `2025-01-01-preview`), plus
`MCP_URL` (pointing at its MCP sub-app's `/mcp` endpoint on port 9000) and
`AGENT_PORT`. The root `SIUAgents/.env` holds the shared Azure OpenAI config
(copied verbatim from `AdjusterAgents/.env`) plus
`MCP_BASE_URL="http://0.0.0.0:9000"`.

`PHOENIX_ENDPOINT` / `PHOENIX_API_KEY` are left blank — all agents fall back
to their built-in `_FALLBACK_PROMPT` when Phoenix is not configured.

## Running

```bash
# 1. Install dependencies (from SIUAgents/)
pip install -r requirements.txt

# 2. Initialize the shared SQLite DB (idempotent/defensive — safe to run
#    first, or after PolicyholderAgents'/AdjusterAgents' init_db)
python MCP/common/init_db.py

# 3. Start the MCP tool server (also re-runs init_db on startup)
python MCP/main.py

# 4. In separate terminals, start any of the agents
python FraudRiskScoringAgent/server.py        # 9001
python CaseAssignmentAgent/server.py          # 9002 - placeholder
python BehavioralAnalyticsAgent/server.py     # 9003 - placeholder
python EntityRelationshipAgent/server.py      # 9004 - placeholder
python FraudPatternAgent/server.py            # 9005
python NetworkAnalysisAgent/server.py         # 9006 - placeholder
python EvidenceCorrelationAgent/server.py     # 9007 - placeholder
python FraudEscalationAgent/server.py         # 9008
python FraudResolutionAgent/server.py         # 9009
python LegalEscalationAgent/server.py         # 9010
python WatchlistUpdateAgent/server.py         # 9011
python SIUClosureAgent/server.py              # 9012 - placeholder
```

Each agent exposes:
- `POST /chat` — SSE streaming chat endpoint (`{"message": "..."}`)
- `GET /health` — health check

## Shared sample data

This platform shares `PolicyholderAgents/data/policyholder.db`, including:

- Policy `POL-1001` (Homeowners, Active, deductible 1000, limit 250000)
- Policy `POL-1002` (Auto, Active, deductible 500, limit 50000)
- Claim `CLM-2026-1001` (policy `POL-1001`, status `Open`)

`SIUAgents/MCP/common/init_db.py` additionally seeds:

- `siu_case_master`: `SIU-2026-0001` for claim `CLM-2026-1001`, status
  "Open", assigned_investigator "Unassigned".
- `siu_claim_master`: claim `CLM-2026-1001`, stage "Investigation", status
  "Open", policy_id "POL-1001", loss_type from `claims`, fnol_complete
  "Yes", fraud_flag false.
- `siu_progress_tracker`: `SIU-2026-0001` / `CLM-2026-1001`, stage "Initial
  Review", progress_percent 10.0, estimated_duration "5-7 days",
  days_elapsed 1.
- `investigation_notes`: two sample rows for `CLM-2026-1001` with risk_flag
  "Low" and "Medium".
