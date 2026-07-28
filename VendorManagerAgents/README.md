# Vendor Manager Agents

A set of 10 agents for the "Vendor Manager" persona of the claims platform.
This persona SHARES the SQLite database with PolicyholderAgents,
AdjusterAgents, and SIUAgents (`PolicyholderAgents/data/policyholder.db`) —
`claims` and other core/shared records are common across personas. No
separate database file is created for this persona.

## Architecture

- `MCP/main.py` — single FastAPI MCP server (port **9100**) hosting all 10
  agent tool sub-apps under `/api/v1/<slug>`, each wrapped with
  `FastApiMCP(...).mount_http()` exposing an MCP endpoint at
  `/api/v1/<slug>/mcp`. Initializes the shared SQLite DB (new tables) on
  startup.
- `MCP/common/db.py` — `get_db_connection()` / `row_to_dict()` helpers,
  resolving to `PolicyholderAgents/data/policyholder.db`.
- `MCP/common/init_db.py` — creates all new Vendor-Manager-persona tables
  (idempotent, `CREATE TABLE IF NOT EXISTS`), re-declares the shared
  `claims` table defensively, and seeds reference data: 5 `vendors`
  (Plumbing/Roofing/Auto Body/Electrical/Contractor specialties), matching
  `vendor_master_input` records (`VEN-001`..`VEN-005`), two
  `vendor_benchmarks` rows, two `vendor_jobs_input` rows for claim
  `CLM-2026-1001`, one pending `vendor_applications` row, and one
  `vendor_assignment` row for `CLM-2026-1001`. Safe to run before or after
  the other personas' `init_db`.
- Each `<AgentName>Agent/server.py` — LangGraph agent with a FastAPI
  `/chat` SSE endpoint and `/health`, connecting to its MCP sub-app via
  `MultiServerMCPClient`.

## Agents

| # | Agent | Slug | MCP mount | Agent port | Status |
|---|-------|------|-----------|------------|--------|
| 1 | VendorOnboardingAgent | `vendor_onboarding` | `/api/v1/vendor_onboarding` | 9101 | FULL |
| 2 | VendorMatchingAgent | `vendor_matching` | `/api/v1/vendor_matching` | 9102 | FULL |
| 3 | VendorQualificationAgent | `vendor_qualification` | `/api/v1/vendor_qualification` | 9103 | PLACEHOLDER |
| 4 | VendorCapacityManagementAgent | `vendor_capacity` | `/api/v1/vendor_capacity` | 9104 | PLACEHOLDER |
| 5 | VendorCostBenchmarkAgent | `vendor_cost_benchmark` | `/api/v1/vendor_cost_benchmark` | 9105 | FULL |
| 6 | DispatchAgent | `dispatch` | `/api/v1/dispatch` | 9106 | FULL |
| 7 | VendorPerformanceAgent | `vendor_performance` | `/api/v1/vendor_performance` | 9107 | FULL |
| 8 | SLAComplianceAgent | `sla_compliance` | `/api/v1/sla_compliance` | 9108 | FULL |
| 9 | EscalationAgent | `vendor_escalation` | `/api/v1/vendor_escalation` | 9109 | FULL |
| 10 | ETAPredictionAgent | `eta_prediction` | `/api/v1/eta_prediction` | 9110 | FULL |

### FULL agent notes

- **VendorOnboardingAgent**: `list_vendor_applications` /
  `get_vendor_application` review `vendor_applications`.
  `submit_vendor_application` inserts a new 'Pending' application.
  `approve_vendor_application` marks the application 'Approved', provisions
  a new `vendors` row (deriving city/state from `location`, default rating
  4.0, `avg_turnaround_days` 5, `avg_cost` 1000, `verified`=1, `license_valid`
  based on whether `license_expiry_date` is in the future), and a
  corresponding `vendor_master_input` row (`vendor_id` = `VEN-00<id>`,
  status 'Active', `assignment_eligible` 'Yes', `vis_score` 70).
  `reject_vendor_application` sets status 'Rejected' and stores
  `rejection_reason`.
- **VendorMatchingAgent**: `match_vendor_for_claim` reads the claim's
  `loss_type`/`location`, maps `loss_type` to a vendor specialty
  heuristically (e.g. "Water Damage" → "Plumbing", "Fire" → "Roofing",
  "Structural" → "Contractor", "Motor"/"Auto" → "Auto Body"), and returns the
  top 3 `vendors` ranked by `rating` desc then `avg_turnaround_days` asc.
  `assign_vendor_to_claim` upserts a `vendor_assignment` row
  (`assignment_status` 'Assigned', `sla_status` 'On Track').
- **VendorCostBenchmarkAgent**: `record_vendor_cost` inserts
  `vendor_cost_input` rows. `compute_cost_variance` aggregates all rows for
  a vendor with a non-null `actual_cost`, computes `avg_estimate`,
  `avg_actual`, and `variance` (%), upserts `cost_variance_output`, and
  compares the result against `vendor_benchmarks.avg_repair_cost`.
- **DispatchAgent**: `create_work_order` inserts a `work_orders` row
  (`work_order_id` like `WO-<random6>`, status 'Scheduled') and a 'Created'
  `dispatch_logs` row. `update_work_order_status` updates `work_orders.status`
  (setting `started_at`/`completed_at`/`canceled_at` as appropriate for
  'In Progress'/'Completed'/'Canceled') and logs the transition in
  `dispatch_logs`. `get_dispatch_logs` returns the full audit trail.
- **VendorPerformanceAgent**: `compute_vendor_performance_score` derives
  `sla_score` from job completion rate in `vendor_jobs_input` (penalized if
  any job is 'Overdue'), `quality` from the average `vendor_rating_input`
  rating (scaled to 0-100), and `cost_efficiency` from the latest
  `cost_variance_output.variance` (`100 - abs(variance)`); `vis` is the
  average of the three (missing components default to 70). Upserts
  `vendor_performance_score_output` and updates
  `vendor_master_input.vis_score`.
- **SLAComplianceAgent**: `compute_sla_compliance` computes the percentage of
  `vendor_jobs_input` rows with `sla_status != 'Overdue'`, derives
  `avg_response_time`/`avg_completion_time` placeholder strings from the
  vendor's `avg_turnaround_days`, and upserts `sla_tracker_output`.
- **EscalationAgent**: `escalate_overdue_jobs` scans `vendor_jobs_input` for
  rows with `sla_status='Overdue'` and `active='Yes'` (optionally filtered by
  `vendor_id`), creates an `escalation_log_output` row (`escalation_id` like
  `VESC-<random6>`, severity 'High') for each, and upserts a
  `job_status_update_output` row (`escalation_flag` 'Yes', `priority` 'High')
  for each affected claim.
- **ETAPredictionAgent**: `predict_eta` reads `vendor_benchmarks.eta_days`
  (falling back to `vendors.avg_turnaround_days`) as a baseline, and the
  claim's `loss_type`/`complexity`, then uses an LLM (JSON response format)
  to adjust the baseline and return `predicted_eta_days`, `confidence`, and
  `factors`. If the LLM call fails, falls back to a heuristic
  (`baseline * 1.2` for "Structural"/"Fire" loss types, else `baseline * 1.0`,
  `confidence=0.6`, `factors="heuristic fallback"`). Inserts a row into the
  new `eta_predictions` table.

### Placeholder notes

- **VendorQualificationAgent**: only `get_vendor_master` (real read of
  `vendor_master_input`, including `license_valid`/`license_expiry_date`) is
  implemented. Full qualification scoring against compliance criteria
  (license expiry checks, insurance documentation, certifications,
  background checks) and updating `assignment_eligible` is TODO.
- **VendorCapacityManagementAgent**: only `get_vendor_active_jobs` (real read
  of `vendor_jobs_input` where `active='Yes'`) is implemented.
  Capacity/workload balancing logic that throttles new assignments
  (`assignment_eligible='No'`) when a vendor's active job count exceeds a
  configurable threshold, and re-enables when capacity frees up, is TODO.

## Configuration

Each agent reads Azure OpenAI credentials from its own `.env` (chat
deployment `gpt-4.1-jarvis`, API version `2025-01-01-preview`), plus
`MCP_URL` (pointing at its MCP sub-app's `/mcp` endpoint on port 9100) and
`AGENT_PORT`. The root `VendorManagerAgents/.env` holds the shared Azure
OpenAI config (copied verbatim from `SIUAgents/.env`) plus
`MCP_BASE_URL="http://0.0.0.0:9100"`.

`PHOENIX_ENDPOINT` / `PHOENIX_API_KEY` are left blank — all agents fall back
to their built-in `_FALLBACK_PROMPT` when Phoenix is not configured.

## Running

```bash
# 1. Install dependencies (from VendorManagerAgents/)
pip install -r requirements.txt

# 2. Initialize the shared SQLite DB (idempotent/defensive — safe to run
#    first, or after PolicyholderAgents'/AdjusterAgents'/SIUAgents' init_db)
python MCP/common/init_db.py

# 3. Start the MCP tool server (also re-runs init_db on startup)
python MCP/main.py

# 4. In separate terminals, start any of the agents
python VendorOnboardingAgent/server.py          # 9101
python VendorMatchingAgent/server.py            # 9102
python VendorQualificationAgent/server.py       # 9103 - placeholder
python VendorCapacityManagementAgent/server.py  # 9104 - placeholder
python VendorCostBenchmarkAgent/server.py       # 9105
python DispatchAgent/server.py                  # 9106
python VendorPerformanceAgent/server.py         # 9107
python SLAComplianceAgent/server.py             # 9108
python EscalationAgent/server.py                # 9109
python ETAPredictionAgent/server.py             # 9110
```

Each agent exposes:
- `POST /chat` — SSE streaming chat endpoint (`{"message": "..."}`)
- `GET /health` — health check

## Shared sample data

This platform shares `PolicyholderAgents/data/policyholder.db`, including:

- Policy `POL-1001` (Homeowners, Active, deductible 1000, limit 250000)
- Claim `CLM-2026-1001` (policy `POL-1001`, loss_type "Water Damage",
  location "123 Main St, Springfield", status `Open`)

`VendorManagerAgents/MCP/common/init_db.py` additionally seeds:

- `vendors`: `VEN-001` Springfield Plumbing Pros (Plumbing, Springfield IL,
  rating 4.6), `VEN-002` Apex Roofing Co (Roofing, Springfield IL, rating
  4.5), `VEN-003` Precision Auto Body (Auto Body, Chicago IL, rating 4.7),
  `VEN-004` Reliable Electric Services (Electrical, Springfield IL, rating
  4.4), `VEN-005` Midwest General Contractors (Contractor, Chicago IL,
  rating 4.3).
- `vendor_master_input`: one row per seeded vendor (`VEN-001`..`VEN-005`),
  status 'Active', `assignment_eligible` 'Yes', `vis_score` 80,
  `license_expiry_date` '2027-12-31'.
- `vendor_benchmarks`: `VEN-001` (Plumbing, avg_repair_cost 800,
  eta_days 3) and `VEN-002` (Roofing, avg_repair_cost 4000, eta_days 6).
- `vendor_jobs_input`: two rows for claim `CLM-2026-1001` — `VEN-001`
  (Completed, On Track) and `VEN-002` (In Progress, On Track).
- `vendor_applications`: one 'Pending' application from "Hometown Water
  Mitigation" (Water Mitigation, Springfield IL).
- `vendor_assignment`: `CLM-2026-1001` assigned to `VEN-001` (Plumbing,
  'Assigned', 'On Track').
