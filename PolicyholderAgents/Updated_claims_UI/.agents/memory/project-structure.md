---
name: Project structure (flattened, not a monorepo)
description: This repo is a single root-level standalone Vite app by deliberate choice; the Replit artifact/monorepo system was intentionally dropped.
---

# Flattened standalone structure

This project is a single standalone Vite + React app at the workspace root
(`src/`, `public/`, `index.html`, `attached_assets/`, root config files). It is
**not** a Replit pnpm monorepo and has no `artifacts/<slug>/` layout.

**Why:** The user explicitly wanted the simplest possible structure for external
deployment and accepted that this breaks the in-Replit preview pane, canvas
embed, and one-click Deploy. The app is built/deployed externally
(`npm install && npm run build` → `dist/`), served at domain root.

**How to apply:**
- Do not try to recreate or assume the Replit artifact preview/workflow/deploy
  system, a pnpm workspace, catalog versions, or `@workspace/*` packages.
- If deploying to a subpath instead of domain root, update `base` in
  `vite.config.ts` and verify the Wouter router base.
- Verify changes with `pnpm run typecheck` and `pnpm run build` (no Replit
  preview to rely on).
