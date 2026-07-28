---
name: App architecture & rendering notes
description: How this insurance portal app is served and verified in Replit.
---

# App architecture & rendering notes

- This is a **root-level Vite React app**, NOT a registered Replit artifact
  (`listArtifacts()` returns empty). Therefore the `app_preview` screenshot tool
  fails ("Artifact not found"), and `external_url` screenshots of the dev domain
  hit Replit's private-app login wall. **Visual verification is done by the user
  in the preview pane**, not by the agent's screenshot tools. Rely on `tsc
  --noEmit` + browser console logs for agent-side verification.
- The app runs via the `Start application` workflow (`PORT=8080 pnpm run dev`).
- All claim screens are now wired to the live Azure Postgres DB via Vite
  middleware APIs (`/api/claims`, `/api/claim-journey`, `/api/fnol-submission`,
  `/api/policy-details`, `/api/documents`). `src/data/mock.ts` was deleted — no
  more mock claim records. Frontend response types live in `src/lib/*` (e.g.
  `claims-data.ts` `ClaimRecord`, `journey-data.ts` `ClaimJourney`).
- Journey/workspace data: `claim_journey_master` holds `current_stage` (1-based;
  stageIndex = current_stage-1), `sub_status`, `overall_sla_status`. The 8-stage
  pipeline list is a constant in `vite-plugins/claim-journey.ts` (stage narrative
  tables are empty in DB). Latest-update text comes from `communication_history`.
