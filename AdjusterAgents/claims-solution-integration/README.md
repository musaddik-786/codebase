# Hexaware Agentic Claims Solution

React 19 + Vite 7 + Tailwind CSS v4 insurance claims portal. All `/api/*` endpoints
are implemented as Vite server plugins (`vite-plugins/`) that talk directly to an
external Azure PostgreSQL database.

## Requirements

- Node.js 20+
- pnpm 10 (`corepack enable && corepack prepare pnpm@10.26.1 --activate`)
  - The `preinstall` hook enforces pnpm; npm/yarn installs will fail by design.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `AZURE_DATABASE_URL` | Yes | Azure PostgreSQL connection string — all `/api/*` data |
| `AZURE_STORAGE_SAS` | No | SAS token or storage connection string for viewing claim evidence blobs in the Document Hub |
| `PORT` | No | Server port (defaults to 7133; set e.g. `PORT=5000`) |

## Run locally

```bash
pnpm install
AZURE_DATABASE_URL="postgres://..." PORT=5000 pnpm exec vite --config vite.config.ts
```

Then open http://localhost:5000

## Deploy

IMPORTANT: the `/api/*` routes only exist on the Vite dev server (server plugins).
A static `vite build` output would lose every API route — production must run the
same Vite server. The included Dockerfile does exactly that.

### Docker

```bash
docker build -t hexaware-claims-solution .
docker run -p 5000:5000 -e AZURE_DATABASE_URL="postgres://..." hexaware-claims-solution
```

### Docker Compose

```bash
export AZURE_DATABASE_URL="postgres://..."
# optional: export AZURE_STORAGE_SAS="..."
docker compose up --build
```

## Project layout

- `index.html`, `src/` — React app (aliases: `@` → `./src`, `@assets` → `./attached_assets`)
- `vite-plugins/` — server-side API endpoints (policy-details, voice-extraction,
  fnol-submission, claims, claim-journey, documents, claim-insights)
- `public/`, `attached_assets/` — static assets
- `lib/`, `scripts/`, `pnpm-workspace.yaml` — workspace scaffolding referenced by the
  pnpm lockfile; keep them in place for `pnpm install --frozen-lockfile`

## API notes

- `claim-journey` and `claim-insights` take `claimNumber` as the query param; `documents` takes `claimId`.
