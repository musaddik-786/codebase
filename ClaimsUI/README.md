# Jarvis Claims UI

A React + Vite + TypeScript + Tailwind v4 frontend for the Jarvis insurance
claims LangGraph agent platform. Talks directly to the Python agent servers
via SSE `/chat` streaming and the Orchestration MCP REST API — no backend
proxy required (CORS is open with `allow_origins=["*"]` on every agent).

## Prerequisites

- Node.js 18+
- The Python agent backends running (see ports below)

## Install & run

```bash
npm install
npm run dev
```

The dev server runs on `http://localhost:5173`.

## Backend services to start

Each persona folder has an `MCP/main.py` (tool server) and per-agent
`server.py` files (LangGraph brain agents exposing `/chat` SSE + `/health`).
Start them all from `Jarvis_claims_agents/`:

```bash
# MCP tool servers (one per persona)
py -3 PolicyholderAgents/MCP/main.py     # port 8800
py -3 AdjusterAgents/MCP/main.py         # port 8900
py -3 SIUAgents/MCP/main.py              # port 9000
py -3 VendorManagerAgents/MCP/main.py    # port 9100
py -3 OrchestratorAgent/MCP/main.py      # port 9200

# Orchestrator brain agent
py -3 OrchestratorAgent/server.py        # port 9201

# Individual persona agent servers (each has its own server.py + AGENT_PORT)
py -3 PolicyholderAgents/<Agent>/server.py
py -3 AdjusterAgents/<Agent>/server.py
py -3 SIUAgents/<Agent>/server.py
py -3 VendorManagerAgents/<Agent>/server.py
```

### Agent ports

| Persona | MCP port | Agent ports |
|---|---|---|
| Policyholder | 8800 | 8801-8809 |
| Adjuster | 8900 | 8901-8915 |
| SIU | 9000 | 9001-9012 |
| Vendor Manager | 9100 | 9101-9110 |
| Orchestrator | 9200 (MCP) | 9201 (brain agent) |

See `src/config/agents.ts` for the full registry (name, slug, port, status —
`full` vs `placeholder`).

## HITL Orchestration REST API

The `/orchestrator` page's approval queue calls the Orchestration MCP sub-app
mounted at:

```
http://localhost:9200/api/v1/orchestration/api/orchestration/...
```

Endpoints used:
- `GET  /approvals/pending` — list pending HITL approvals
- `POST /approvals/{approval_id}/decide` — body `{ decision, decided_by, notes? }`
- `GET  /state/{claim_id}` — current orchestration stage/status for a claim

REQUIRED gates: `damage_assessment_review`, `reserve_approval`,
`settlement_approval`, `siu_decision_approval`, `payment_approval`,
`claim_closure_approval`.

OPTIONAL gates: `fnol_review`, `triage_approval`, `vendor_assignment_approval`.

## Project structure

- `src/config/agents.ts` — typed registry of all ~47 agents, grouped by persona, with persona-specific groupings matching the architecture diagram
- `src/components/AgentChatPanel.tsx` — reusable SSE chat panel (fetch + ReadableStream), shows `[Tool: ...]` events as inline badges
- `src/components/Layout.tsx` — top nav / persona switcher
- `src/pages/` — `Home`, `Policyholder`, `Adjuster`, `SIU`, `VendorManager`, `Orchestrator`

## Notes

- Voice intake (Policyholder > File a New Claim) uses the browser
  `SpeechRecognition` Web Speech API where available, falling back to typed
  text. The agent only ever receives plain text.
- Adjuster/SIU/Vendor Manager pages include a Claim ID field; messages sent
  from those pages are prefixed `For claim {claim_id}: ...`.
