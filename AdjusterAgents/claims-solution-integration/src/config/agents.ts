// ─────────────────────────────────────────────────────────────────────────────
// Single source of truth for all agent / orchestrator / MCP service base URLs.
//
// To change a port, change it HERE (or via the matching VITE_* env var) — every
// component imports these constants instead of hard-coding a URL.
// ─────────────────────────────────────────────────────────────────────────────

import type { PersonaId } from "@/lib/personas";

const env = import.meta.env as Record<string, string | undefined>;

// MCP tool servers — the policyholder and adjuster personas talk to different
// MCP backends, so there is one base URL per persona.
export const POLICYHOLDER_MCP_URL =
  env.VITE_POLICYHOLDER_MCP_URL ?? "http://localhost:7720";
export const ADJUSTER_MCP_URL =
  env.VITE_ADJUSTER_MCP_URL ?? "http://localhost:6190";

// Resolve the MCP base for the active persona. Components shared across personas
// should call this with the current persona id (from usePersona()).
export function mcpUrlForPersona(personaId: PersonaId): string {
  return personaId === "adjuster" ? ADJUSTER_MCP_URL : POLICYHOLDER_MCP_URL;
}

// FNOL intake orchestrator / agent (Smart Loss Reporting flow)
export const FNOL_ORCHESTRATOR_URL =
  env.VITE_FNOL_ORCHESTRATOR_URL ?? "http://localhost:7730";
export const FNOL_AGENT_URL = env.VITE_FNOL_AGENT_URL ?? "http://localhost:7730";

// Adjuster orchestrator — full Claim Intake → Settlement journey (15 agents + HITL gates)
export const ADJUSTER_ORCHESTRATOR_URL =
  env.VITE_ADJUSTER_ORCHESTRATOR_URL ?? "http://localhost:8920";

// HITL approval gate endpoints (GET .../approvals/pending, POST .../approvals/{id}/decide).
// As of 2026-07-16 these are hosted locally in AdjusterAgents' own MCP server
// (port 5800, same process as the 15 agent tools) — no longer OrchestratorAgent
// (port 9200). Deliberately a separate constant from ADJUSTER_MCP_URL above
// (which defaults to a different, currently-incorrect port) rather than reusing it.
export const ADJUSTER_ORCHESTRATION_MCP_URL =
  env.VITE_ADJUSTER_ORCHESTRATION_MCP_URL ?? "http://localhost:5800/api/v1/orchestration";
