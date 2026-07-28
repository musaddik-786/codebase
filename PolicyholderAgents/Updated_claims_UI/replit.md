# Hexaware Agentic Claims Solution

A frontend-only insurance claims portal prototype that demonstrates an AI-powered, agentic claims experience across four user personas.

## Run & Operate

- `pnpm --filter @workspace/claims-portal run dev` — run the claims portal web app
- `pnpm --filter @workspace/claims-portal run typecheck` — typecheck the claims portal
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Web: React + Vite, wouter (routing), Tailgrid/shadcn-style UI components, lucide-react icons
- Fonts: Inter

## Where things live

- `artifacts/claims-portal/` — the claims portal web app
  - `src/App.tsx` — router + persona-based route selection
  - `src/lib/persona-context.tsx` — active persona React Context
  - `src/lib/personas.ts` — persona definitions (4 personas)
  - `src/components/layout/` — Layout, Sidebar, Header (persona switcher + logo)
  - `src/pages/` — Policyholder screens + PlaceholderDashboard for other personas
  - `vite.config.ts` — `@assets` alias → `attached_assets/`, PORT/BASE_PATH config
- `attached_assets/image_1782114370781.png` — Hexaware wordmark logo

## Architecture decisions

- Frontend-only: no backend, no database. All data is mock data defined in-app.
- Persona-driven routing: `RoleBasedRouter` in `App.tsx` swaps the available routes based on the active persona. Policyholder has 4 full screens; other personas render an on-brand placeholder dashboard.
- Switching persona navigates to `/` to avoid landing on a route that doesn't exist for the new persona.

## Product

- Four personas via a role switcher (top-right): John Davis (Policyholder, default), Michael Chen (Adjuster), Rachel Martinez (Vendor Manager), David Wilson (SIU/Fraud).
- Policyholder screens: Smart Loss Reporting (Intelligent FNOL), My Claims, Follow My Claims (Claim Journey Workspace), Document Hub.
- Other three personas show on-brand placeholder dashboards.

## User preferences

- No emojis in the UI.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
