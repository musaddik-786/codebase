---
name: Vite middleware API plugins
description: How the backend APIs are served in this repo and a key dev-loop gotcha
---

This root Vite React app has NO separate backend server. API routes are implemented
as Vite plugins under `vite-plugins/` using `configureServer(server)` +
`server.middlewares.use("/api/...", handler)`, registered in `vite.config.ts`.
They query Azure Postgres via `pg` using the `AZURE_DATABASE_URL` secret
(shared pool/helpers in `vite-plugins/db.ts`).

**Gotcha:** Editing a `configureServer` plugin does NOT hot-reload — Vite HMR only
updates client modules. You MUST restart the "Start application" workflow for any
backend/plugin change to take effect, then curl `http://localhost:8080/api/...`
to verify (the external `$REPLIT_DEV_DOMAIN` proxy can return 502 right after a
restart even when localhost works).

**Scoping rule:** Identifier-scoped endpoints must REQUIRE their query param and
return 400 when missing. Avoid `WHERE ($1 = '' OR col = $1)` — a blank param then
silently returns the latest row of another user/policy (a privacy/correctness bug).

**FNOL data shape:** `fnol_submissions` has per-field `<field>_source` columns and a
single `overall_confidence` — there is NO per-field confidence. So the Stage 2
"What AI Extracted" grid shows per-field SOURCE (AI-Inferred / Customer-Confirmed /
Customer-Provided) plus one overall-confidence figure; do not fake per-row confidence.
`fnol_voice_text_extraction` links to a submission via `fnol_id` (no policy_number of
its own), so scope voice lookups by joining to `fnol_submissions.policy_number`.
