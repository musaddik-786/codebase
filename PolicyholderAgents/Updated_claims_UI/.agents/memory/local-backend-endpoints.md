---
name: Local backend endpoints (FNOL)
description: The FNOL app calls localhost backends that are NOT reachable from the Replit dev container; how to reason about success/failure behavior.
---

# Local backend endpoints (FNOL)

The Hexaware FNOL app's frontend calls services on the user's local machine
(e.g. `localhost:2239`, `localhost:8801`). These are NOT reachable from the
Replit dev container — curl to them returns connection refused (exit 7 / HTTP
000). So any feature wired to them cannot be exercised end-to-end in Replit.

**Why:** the backends are the user's own local services, not part of this repo
or environment.

**How to apply:**
- Don't try to "fix" a failing call by probing the endpoint from Replit — it
  will always fail here. Verify wiring/logic and graceful fallback instead.
- Request shapes for these endpoints are assumptions (REST naming). The Stage 1
  policy lookup assumes GET `.../get_by_policy/<policyNumber>`. If the live
  service expects a query param or POST body, only the fetch call needs
  changing; the success→valid / failure→invalid popup behavior is independent.
- By design, in this environment the lookup always shows the invalid popup
  (because the call fails) — that is expected, not a bug.

## Policy details now come from Azure Postgres (not localhost)
The Stage 2 "Your Policy Information" card is served by a Vite dev-server
middleware (`vite-plugins/policy-details.ts`) that connects to an Azure Postgres
DB via the `AZURE_DATABASE_URL` secret. Unlike the user's localhost backends,
the Azure DB **is** reachable from the Replit container, so this path can be
exercised end-to-end here (`curl localhost:$PORT/api/policy-details?policyNumber=POL-1001`).
The `policy_details` table keys on `policy_id` (e.g. "POL-1001"); many descriptive
columns (insured_name, policy_address, dates) may be NULL in seed data.
