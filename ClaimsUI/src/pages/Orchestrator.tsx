import { useState, useEffect, useCallback } from "react";
import { RefreshCw } from "lucide-react";
import { personas, ORCHESTRATION_MCP_BASE, REQUIRED_GATES } from "@/config/agents";
import { AgentChatPanel } from "@/components/AgentChatPanel";

const persona = personas.orchestrator;
const brainAgent = persona.agents[0];

interface Approval {
  id: number;
  approval_id: string;
  claim_id: string;
  gate_type: string;
  status: string;
  summary: string;
  requested_by: string;
  requested_at?: string;
}

interface OrchestrationState {
  claim_id: string;
  current_stage: string | null;
  status: string | null;
  last_action: string | null;
  found: boolean;
}

export function Orchestrator() {
  const [claimId, setClaimId] = useState("CLM-2026-1001");
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [state, setState] = useState<OrchestrationState | null>(null);
  const [decidedBy, setDecidedBy] = useState("Demo User");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchApprovals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${ORCHESTRATION_MCP_BASE}/approvals/pending`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setApprovals(Array.isArray(data) ? data : []);
    } catch (e: any) {
      setError(e?.message ?? "Failed to fetch approvals");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchState = useCallback(async () => {
    try {
      const resp = await fetch(`${ORCHESTRATION_MCP_BASE}/state/${encodeURIComponent(claimId)}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setState(await resp.json());
    } catch {
      setState(null);
    }
  }, [claimId]);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  useEffect(() => {
    fetchState();
  }, [fetchState]);

  async function decide(approvalId: string, decision: "Approved" | "Rejected") {
    try {
      const resp = await fetch(`${ORCHESTRATION_MCP_BASE}/approvals/${approvalId}/decide`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, decided_by: decidedBy, notes: notes[approvalId] || undefined }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      await fetchApprovals();
      await fetchState();
    } catch (e: any) {
      setError(e?.message ?? "Failed to record decision");
    }
  }

  return (
    <div>
      <h1 className="text-2xl mb-1" style={{ color: `hsl(var(--${persona.color}))` }}>
        Orchestrator / HITL
      </h1>
      <p className="text-muted-foreground mb-4">{persona.description}</p>

      {/* Brain agent chat */}
      <section className="mb-8">
        <h2 className="text-lg mb-2">Brain Agent</h2>
        <div className="flex items-center gap-2 mb-3">
          <label className="text-sm font-medium">Claim ID:</label>
          <input
            className="rounded-md border px-3 py-1.5 text-sm bg-background w-48"
            value={claimId}
            onChange={(e) => setClaimId(e.target.value)}
          />
          <button
            className="rounded-md px-3 py-1.5 text-sm text-white"
            style={{ backgroundColor: `hsl(var(--${persona.color}))` }}
            onClick={() => setRunMessage(`Continue orchestration for claim ${claimId}`)}
          >
            Run Orchestration
          </button>
        </div>
        <AgentChatPanel
          agentName={brainAgent.name}
          baseUrl={brainAgent.baseUrl}
          placeholder={`Message the orchestrator brain agent...`}
          externalMessage={runMessage}
          onExternalMessageSent={() => setRunMessage(null)}
        />
      </section>

      {/* Claim orchestration state */}
      <section className="mb-8">
        <h2 className="text-lg mb-2">Claim Orchestration State</h2>
        <div className="border rounded-lg p-4 bg-card text-sm">
          {state ? (
            state.found ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <div className="text-muted-foreground text-xs">Claim ID</div>
                  <div className="font-medium">{state.claim_id}</div>
                </div>
                <div>
                  <div className="text-muted-foreground text-xs">Current Stage</div>
                  <div className="font-medium">{state.current_stage}</div>
                </div>
                <div>
                  <div className="text-muted-foreground text-xs">Status</div>
                  <div className="font-medium">{state.status}</div>
                </div>
                <div>
                  <div className="text-muted-foreground text-xs">Last Action</div>
                  <div className="font-medium">{state.last_action}</div>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">No orchestration state found for {state.claim_id}.</p>
            )
          ) : (
            <p className="text-muted-foreground">Loading...</p>
          )}
        </div>
      </section>

      {/* HITL approval queue */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg">HITL Approval Queue</h2>
          <div className="flex items-center gap-2">
            <label className="text-sm">Decided by:</label>
            <input
              className="rounded-md border px-2 py-1 text-sm bg-background w-36"
              value={decidedBy}
              onChange={(e) => setDecidedBy(e.target.value)}
            />
            <button
              onClick={fetchApprovals}
              className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm bg-muted"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
        <div className="border rounded-lg overflow-x-auto bg-card">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-3 py-2">Approval ID</th>
                <th className="text-left px-3 py-2">Claim ID</th>
                <th className="text-left px-3 py-2">Gate Type</th>
                <th className="text-left px-3 py-2">Summary</th>
                <th className="text-left px-3 py-2">Status</th>
                <th className="text-left px-3 py-2">Requested At</th>
                <th className="text-left px-3 py-2">Notes</th>
                <th className="text-left px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {approvals.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-3 py-4 text-center text-muted-foreground">
                    No pending approvals.
                  </td>
                </tr>
              )}
              {approvals.map((a) => (
                <tr key={a.approval_id} className="border-t">
                  <td className="px-3 py-2 font-mono">{a.approval_id}</td>
                  <td className="px-3 py-2 font-mono">{a.claim_id}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-full border ${
                        REQUIRED_GATES.includes(a.gate_type)
                          ? "bg-red-100 text-red-800 border-red-300"
                          : "bg-blue-100 text-blue-800 border-blue-300"
                      }`}
                    >
                      {REQUIRED_GATES.includes(a.gate_type) ? "REQUIRED" : "OPTIONAL"}
                    </span>{" "}
                    {a.gate_type}
                  </td>
                  <td className="px-3 py-2 max-w-[280px]">{a.summary}</td>
                  <td className="px-3 py-2">{a.status}</td>
                  <td className="px-3 py-2">{a.requested_at ?? "-"}</td>
                  <td className="px-3 py-2">
                    <input
                      className="rounded-md border px-2 py-1 text-xs bg-background w-32"
                      placeholder="optional notes"
                      value={notes[a.approval_id] ?? ""}
                      onChange={(e) => setNotes((n) => ({ ...n, [a.approval_id]: e.target.value }))}
                    />
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <button
                      className="rounded-md bg-green-600 text-white px-2 py-1 text-xs mr-1"
                      onClick={() => decide(a.approval_id, "Approved")}
                    >
                      Approve
                    </button>
                    <button
                      className="rounded-md bg-red-600 text-white px-2 py-1 text-xs"
                      onClick={() => decide(a.approval_id, "Rejected")}
                    >
                      Reject
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
