// ─────────────────────────────────────────────────────────────────────────────
// Client helpers for the Adjuster Orchestrator.
//
// Wraps the 3 real endpoints the UI talks to (base URLs come from
// src/config/agents.ts so ports live in ONE place):
//   1. POST {ADJUSTER_ORCHESTRATOR_URL}/chat                          — run/continue the workflow (SSE)
//   2. GET  {ADJUSTER_ORCHESTRATION_MCP_URL}/approvals/pending        — list pending HITL gates
//   3. POST {ADJUSTER_ORCHESTRATION_MCP_URL}/approvals/{id}/decide    — approve/reject a gate
// ─────────────────────────────────────────────────────────────────────────────

import {
  ADJUSTER_ORCHESTRATOR_URL,
  ADJUSTER_ORCHESTRATION_MCP_URL,
} from "@/config/agents";

export interface Approval {
  approval_id: string;
  claim_id: string;
  gate_type: string;
  status: string;
  summary: string;
  requested_by: string;
  requested_at: string;
  decided_by?: string;
  decision_notes?: string;
}

export interface ChatStreamOptions {
  history?: Array<{ role: string; content: string }>;
  onText?: (chunk: string) => void;
  onToolEvent?: (tool: string, state: "Starting" | "Done") => void;
  signal?: AbortSignal;
}

const TOOL_EVENT_RE = /\[Tool:\s*([^\]]+)\]\s*(Starting|Done)/g;

// ─── Per-claim conversation history ──────────────────────────────────────────
// The orchestrator is stateless: the client must send the full prior
// conversation as `history` with each /chat call, otherwise "Continue the
// adjuster workflow..." starts a brand-new run from the first agent instead of
// resuming after the last HITL gate. We keep one conversation per claim in
// sessionStorage so it survives page navigation between the adjuster screens.

type ChatTurn = { role: string; content: string };

const HISTORY_KEY_PREFIX = "adjuster-orch-history:";

function historyKey(claimId: string): string {
  return `${HISTORY_KEY_PREFIX}${claimId}`;
}

export function getClaimConversation(claimId: string): ChatTurn[] {
  try {
    const raw = sessionStorage.getItem(historyKey(claimId));
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

// Keep the stored conversation bounded so sessionStorage quota is never hit
// (each turn can carry a long streamed reply). 20 turns = 10 exchanges, far
// more than the workflow's run/continue cycle needs.
const MAX_STORED_TURNS = 20;

function saveClaimConversation(claimId: string, turns: ChatTurn[]) {
  try {
    sessionStorage.setItem(historyKey(claimId), JSON.stringify(turns.slice(-MAX_STORED_TURNS)));
  } catch {
    // sessionStorage unavailable/full — history just won't persist.
  }
}

export function resetClaimConversation(claimId: string) {
  try {
    sessionStorage.removeItem(historyKey(claimId));
  } catch {
    // ignore
  }
}

// Send one message in the claim's ongoing conversation: snapshots the stored
// history, streams the reply, and appends the {user, assistant} pair to the
// stored conversation once a reply (even partial) has been received.
async function chatForClaim(
  claimId: string,
  message: string,
  opts: ChatStreamOptions = {}
): Promise<string> {
  const history = getClaimHistorySnapshot(claimId, opts);
  let accumulated = "";
  try {
    const full = await streamOrchestratorChat(message, {
      ...opts,
      history,
      onText: (chunk) => {
        accumulated += chunk;
        opts.onText?.(chunk);
      },
    });
    appendClaimTurns(claimId, history, message, full || accumulated);
    return full;
  } catch (err) {
    // If the stream was cut off (timeout/abort) after the orchestrator already
    // produced output, keep the partial reply so the next "continue" resumes
    // from the right place instead of restarting the whole workflow.
    if (accumulated) appendClaimTurns(claimId, history, message, accumulated);
    throw err;
  }
}

function getClaimHistorySnapshot(claimId: string, opts: ChatStreamOptions): ChatTurn[] {
  // An explicit history option overrides the stored conversation.
  return opts.history ?? getClaimConversation(claimId);
}

function appendClaimTurns(
  claimId: string,
  history: ChatTurn[],
  userMessage: string,
  assistantReply: string
) {
  if (!assistantReply) return;
  saveClaimConversation(claimId, [
    ...history,
    { role: "user", content: userMessage },
    { role: "assistant", content: assistantReply },
  ]);
}

// POST {ADJUSTER_ORCHESTRATOR_URL}/chat — streams the orchestrator response (SSE).
// Resolves with the full accumulated text once the stream ends.
export async function streamOrchestratorChat(
  message: string,
  opts: ChatStreamOptions = {}
): Promise<string> {
  const resp = await fetch(`${ADJUSTER_ORCHESTRATOR_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history: opts.history ?? [] }),
    signal: opts.signal,
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`Orchestrator error (HTTP ${resp.status})`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let full = "";

  const handleChunk = (chunk: string) => {
    if (opts.onToolEvent) {
      TOOL_EVENT_RE.lastIndex = 0;
      let m: RegExpExecArray | null;
      while ((m = TOOL_EVENT_RE.exec(chunk)) !== null) {
        opts.onToolEvent(m[1].trim(), m[2] as "Starting" | "Done");
      }
    }
    full += chunk;
    opts.onText?.(chunk);
  };

  const processLine = (line: string) => {
    if (!line.startsWith("data:")) return;
    // Strip the "data:" prefix (with or without a leading space) and any trailing CR.
    const chunk = (line.startsWith("data: ") ? line.slice(6) : line.slice(5)).replace(/\r$/, "");
    if (!chunk || chunk === "[DONE]") return;
    handleChunk(chunk);
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) processLine(line);
  }
  // Flush the decoder and any buffered remainder that lacked a trailing newline.
  buffer += decoder.decode();
  if (buffer) processLine(buffer);
  return full;
}

// Kick off the full 15-agent adjuster workflow for a claim. Starts a fresh
// conversation for the claim (any previous history is discarded).
export function runAdjusterWorkflow(claimId: string, opts?: ChatStreamOptions) {
  resetClaimConversation(claimId);
  return chatForClaim(claimId, `Run the adjuster workflow for claim ${claimId}`, opts);
}

// Resume the workflow after a HITL gate decision. Sends the stored per-claim
// conversation as history so the orchestrator continues from where it paused
// (e.g. loss assessment) instead of rerunning all agents from the start.
export function continueAdjusterWorkflow(claimId: string, opts?: ChatStreamOptions) {
  return chatForClaim(claimId, `Continue the adjuster workflow for claim ${claimId}`, opts);
}

// GET {ADJUSTER_ORCHESTRATION_MCP_URL}/approvals/pending?claim_id=...
export async function fetchPendingApprovals(claimId: string): Promise<Approval[]> {
  const resp = await fetch(
    `${ADJUSTER_ORCHESTRATION_MCP_URL}/approvals/pending?claim_id=${encodeURIComponent(claimId)}`
  );
  if (!resp.ok) throw new Error(`Could not load approvals (HTTP ${resp.status})`);
  const data = await resp.json();
  return Array.isArray(data) ? data : [];
}

// POST {ADJUSTER_ORCHESTRATION_MCP_URL}/approvals/{approval_id}/decide
export async function decideApproval(
  approvalId: string,
  decision: "Approved" | "Rejected",
  decidedBy: string,
  notes?: string
): Promise<void> {
  const resp = await fetch(
    `${ADJUSTER_ORCHESTRATION_MCP_URL}/approvals/${encodeURIComponent(approvalId)}/decide`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, decided_by: decidedBy, notes: notes || undefined }),
    }
  );
  if (!resp.ok) throw new Error(`Decision failed (HTTP ${resp.status})`);
}

export interface DecideGateResult {
  decided: number;
  gates: string[];
}

// Convenience: find pending approval(s) for a claim and decide them.
// If gateType is provided only that gate is decided; otherwise every pending gate.
export async function decideClaimGate(
  claimId: string,
  decision: "Approved" | "Rejected",
  opts: { gateType?: string; decidedBy?: string; notes?: string } = {}
): Promise<DecideGateResult> {
  const decidedBy = opts.decidedBy ?? "adjuster_1";
  const pending = await fetchPendingApprovals(claimId);
  const targets = opts.gateType
    ? pending.filter((a) => a.gate_type === opts.gateType)
    : pending;
  for (const a of targets) {
    await decideApproval(a.approval_id, decision, decidedBy, opts.notes);
  }
  return { decided: targets.length, gates: targets.map((a) => a.gate_type) };
}
