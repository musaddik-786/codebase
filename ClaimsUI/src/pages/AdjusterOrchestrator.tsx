import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send, Loader2, Wrench, ShieldAlert, FileSearch, Gavel, GitBranch,
  Calculator, Landmark, HandCoins, Wallet, CircleDollarSign,
  CheckCircle2, XCircle, RefreshCw, Clock,
  Hammer, CloudSun, BadgeCheck, Route, TrendingDown,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { ORCHESTRATION_MCP_BASE } from "@/config/agents";

// ─── Markdown renderer for chat bubbles (tables, bold, lists) ────────────────

function ChatMarkdown({ content }: { content: string }) {
  return (
    <div className="text-sm [&_p]:my-1 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4 [&_strong]:font-semibold">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ children }) => (
            <div className="overflow-x-auto my-2 rounded-md border border-border">
              <table className="w-full border-collapse text-xs">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border-b border-border bg-muted/60 px-3 py-1.5 text-left font-semibold whitespace-nowrap">{children}</th>
          ),
          td: ({ children }) => (
            <td className="border-b border-border px-3 py-1.5 align-top">{children}</td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

// ─── Constants ────────────────────────────────────────────────────────────────

const ORCHESTRATOR_URL = "http://localhost:8920";

// One entry per agent (not grouped) so each agent gets its own row in the
// tracker below — a row only turns green once THAT agent's own tool call
// completes, not when its whole phase-group finishes.
const TOOL_TO_PHASE: Record<string, string> = {
  run_fraud_screening: "fraud_screening", write_fraud_flag: "fraud_screening",
  write_ai_fraud_signal: "fraud_screening", write_fraud_risk_snapshot: "fraud_screening",
  get_fraud_flags: "fraud_screening", get_ai_fraud_signals: "fraud_screening",
  get_fraud_risk_snapshot: "fraud_screening",

  analyze_damage_from_description: "damage_assessment", write_damage_item: "damage_assessment",
  get_condition_assessments: "damage_assessment", write_condition_assessment: "damage_assessment",
  get_damage_items: "damage_assessment",

  run_external_data_checks: "external_data", get_weather_alignment: "external_data",
  get_drone_authenticity: "external_data", get_drone_evidence_summary: "external_data",

  run_verification: "verification", create_verification: "verification",
  get_external_verifications: "verification", write_verification_detail: "verification",
  get_verification_details: "verification",

  classify_claim: "claim_classification", save_classification: "claim_classification",
  get_claim_classification: "claim_classification", get_claim_details: "claim_classification",

  run_evidence_validation: "evidence_validation", save_validation_result: "evidence_validation",
  get_evidence_items: "evidence_validation", get_claim_documents: "evidence_validation",

  run_triage: "triage", get_claim_triage: "triage",

  assign_claim: "routing", get_auto_assignment_log: "routing",

  run_loss_assessment: "loss_assessment", write_loss_assessment: "loss_assessment",
  get_loss_estimation: "loss_assessment", write_loss_estimation: "loss_assessment",
  get_loss_assessment: "loss_assessment",

  compare_repair_vs_replace: "repair_vs_replacement",
  write_repair_vs_replacement_decision: "repair_vs_replacement",
  update_repair_vs_replacement_decision: "repair_vs_replacement",

  recommend_reserve: "reserve_recommendation", get_adjuster_findings: "reserve_recommendation",

  recommend_settlement: "settlement_recommendation", get_ai_decision_recommendation: "settlement_recommendation",

  check_eligibility: "payment_eligibility", get_auto_adjudication_thresholds: "payment_eligibility",
  get_auto_adjudication_record: "payment_eligibility",

  score_leakage: "financial_leakage", get_cost_variance: "financial_leakage",

  create_payment_disbursement: "payment_trigger", check_claim_approved: "payment_trigger",
  get_payment_eligibility: "payment_trigger", update_payment_status: "payment_trigger",
  get_payment_disbursements: "payment_trigger",
};

interface PhaseDefinition {
  id: string;
  label: string;
  agentNames: string;
  icon: React.ElementType;
  gate?: { type: string; blocking: boolean };
}

// One row per agent, in the exact order the prompt calls them. Gate badges
// attach to the LAST agent that runs before that gate opens.
const PHASES: PhaseDefinition[] = [
  { id: "fraud_screening",         label: "Fraud Screening",          agentNames: "FraudScreeningAgent",         icon: ShieldAlert },
  { id: "damage_assessment",       label: "Damage Assessment",        agentNames: "DamageAssessmentAgent",       icon: Hammer },
  { id: "external_data",           label: "External Data",           agentNames: "ExternalDataAgent",           icon: CloudSun },
  { id: "verification",            label: "Verification",             agentNames: "VerificationAgent",           icon: BadgeCheck },
  { id: "claim_classification",    label: "Claim Classification",     agentNames: "ClaimClassificationAgent",    icon: Gavel },
  { id: "evidence_validation",     label: "Evidence Validation",      agentNames: "EvidenceValidationAgent",     icon: FileSearch },
  { id: "triage",                  label: "Triage",                   agentNames: "TriageAgent",                 icon: GitBranch },
  { id: "routing",                 label: "Routing",                  agentNames: "RoutingAgent",                icon: Route,
    gate: { type: "triage_approval", blocking: false } },
  { id: "loss_assessment",         label: "Loss Assessment",          agentNames: "LossAssessmentAgent",         icon: Calculator },
  { id: "repair_vs_replacement",   label: "Repair vs Replacement",    agentNames: "RepairVsReplacementAgent",    icon: Wrench,
    gate: { type: "damage_assessment_review", blocking: true } },
  { id: "reserve_recommendation",  label: "Reserve Recommendation",   agentNames: "ReserveRecommendationAgent",  icon: Landmark,
    gate: { type: "reserve_approval", blocking: true } },
  { id: "settlement_recommendation", label: "Settlement Recommendation", agentNames: "SettlementRecommendationAgent", icon: HandCoins,
    gate: { type: "settlement_approval", blocking: true } },
  { id: "payment_eligibility",     label: "Payment Eligibility",      agentNames: "PaymentEligibilityAgent",     icon: Wallet },
  { id: "financial_leakage",       label: "Financial Leakage",        agentNames: "FinancialLeakageAgent",       icon: TrendingDown,
    gate: { type: "payment_approval", blocking: true } },
  { id: "payment_trigger",         label: "Payment Trigger",          agentNames: "PaymentTriggerAgent",         icon: CircleDollarSign },
];

const TOOL_REGEX = /\[Tool:\s*([^\]]+)\]\s*(Starting|Done)/gi;

// ─── Types ────────────────────────────────────────────────────────────────────

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  tools?: string[];
}

interface Approval {
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

// ─── Phase Tracker sidebar ────────────────────────────────────────────────────

function PhaseTracker({
  completedPhases,
  currentPhase,
  pendingGates,
  phaseTools,
}: {
  completedPhases: Set<string>;
  currentPhase: string | null;
  pendingGates: Set<string>;
  phaseTools: Record<string, string[]>;
}) {
  return (
    <div className="w-56 shrink-0 flex flex-col gap-1">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
        Adjuster Journey
      </p>
      {PHASES.map((phase, i) => {
        const isDone = completedPhases.has(phase.id);
        const isActive = currentPhase === phase.id && !isDone;
        const isBlocked = !!phase.gate && pendingGates.has(phase.gate.type);
        const Icon = phase.icon;

        return (
          <div
            key={phase.id}
            className={cn(
              "flex items-start gap-2 rounded-md px-2 py-2 text-xs transition-all border",
              isDone
                ? "bg-green-50 border-green-200 text-green-800"
                : isBlocked
                ? "bg-amber-50 border-amber-300 text-amber-800"
                : isActive
                ? "bg-primary/10 border-primary/40 text-primary animate-pulse"
                : "bg-muted/30 border-transparent text-muted-foreground"
            )}
          >
            <div className="flex flex-col items-center gap-0.5 shrink-0 mt-0.5">
              <span
                className={cn(
                  "h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold",
                  isDone
                    ? "bg-green-500 text-white"
                    : isBlocked
                    ? "bg-amber-500 text-white"
                    : isActive
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {isDone ? "✓" : isBlocked ? "⏸" : i + 1}
              </span>
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1">
                <Icon className="h-3 w-3 shrink-0" />
                <span className="font-medium truncate">{phase.label}</span>
                {isActive && <Loader2 className="h-3 w-3 animate-spin shrink-0" />}
              </div>
              <p className="text-[10px] opacity-70 leading-tight mt-0.5">{phase.agentNames}</p>
              {(phaseTools[phase.id]?.length ?? 0) > 0 && (
                <p className="text-[9px] font-mono opacity-60 leading-tight mt-0.5 truncate">
                  → {phaseTools[phase.id].join(", ")}
                </p>
              )}
              {phase.gate && (
                <span
                  className={cn(
                    "inline-block mt-1 text-[9px] font-semibold uppercase tracking-wide rounded-full px-1.5 py-0.5",
                    isBlocked
                      ? "bg-amber-100 text-amber-800 border border-amber-300"
                      : "bg-muted text-muted-foreground border border-transparent"
                  )}
                >
                  {phase.gate.blocking ? "HITL · blocking" : "HITL · audit-only"}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Approvals panel ──────────────────────────────────────────────────────────

function ApprovalsPanel({
  claimId,
  onDecided,
}: {
  claimId: string;
  onDecided: () => void;
}) {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(false);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [decidedBy, setDecidedBy] = useState("adjuster_1");

  const fetchApprovals = useCallback(async () => {
    if (!claimId.trim()) return;
    setLoading(true);
    try {
      const resp = await fetch(`${ORCHESTRATION_MCP_BASE}/approvals/pending?claim_id=${encodeURIComponent(claimId)}`);
      const data = await resp.json();
      setApprovals(Array.isArray(data) ? data : []);
    } catch {
      setApprovals([]);
    } finally {
      setLoading(false);
    }
  }, [claimId]);

  useEffect(() => {
    fetchApprovals();
    const interval = setInterval(fetchApprovals, 5000);
    return () => clearInterval(interval);
  }, [fetchApprovals]);

  async function decide(approvalId: string, decision: "Approved" | "Rejected") {
    await fetch(`${ORCHESTRATION_MCP_BASE}/approvals/${approvalId}/decide`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, decided_by: decidedBy, notes: notes[approvalId] || undefined }),
    });
    await fetchApprovals();
    onDecided();
  }

  return (
    <div className="border rounded-lg bg-card overflow-hidden">
      <div className="px-4 py-2 border-b bg-muted/50 flex items-center justify-between text-sm">
        <span className="font-medium flex items-center gap-1.5">
          <Clock className="h-4 w-4" style={{ color: "hsl(var(--adjuster))" }} />
          Pending HITL Approvals — claim {claimId || "—"}
        </span>
        <div className="flex items-center gap-2">
          <input
            className="rounded-md border px-2 py-1 text-xs bg-background w-32"
            value={decidedBy}
            onChange={(e) => setDecidedBy(e.target.value)}
            placeholder="decided_by"
          />
          <button
            onClick={fetchApprovals}
            className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs hover:bg-muted"
          >
            <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} /> Refresh
          </button>
        </div>
      </div>
      <div className="p-3">
        {approvals.length === 0 ? (
          <p className="text-xs text-muted-foreground italic">No pending approvals for this claim right now.</p>
        ) : (
          <div className="space-y-2">
            {approvals.map((a) => (
              <div key={a.approval_id} className="rounded-md border p-3 text-xs bg-amber-50/50 border-amber-200">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold uppercase tracking-wide text-amber-800">{a.gate_type}</span>
                  <span className="text-muted-foreground">{a.requested_at}</span>
                </div>
                <p className="mb-2">{a.summary}</p>
                <div className="flex items-center gap-2">
                  <input
                    className="flex-1 rounded-md border px-2 py-1 text-xs bg-background"
                    placeholder="Decision notes (optional)"
                    value={notes[a.approval_id] || ""}
                    onChange={(e) => setNotes((prev) => ({ ...prev, [a.approval_id]: e.target.value }))}
                  />
                  <button
                    onClick={() => decide(a.approval_id, "Approved")}
                    className="inline-flex items-center gap-1 rounded-md border border-green-300 bg-green-100 text-green-800 px-2 py-1 hover:bg-green-200"
                  >
                    <CheckCircle2 className="h-3 w-3" /> Approve
                  </button>
                  <button
                    onClick={() => decide(a.approval_id, "Rejected")}
                    className="inline-flex items-center gap-1 rounded-md border border-red-300 bg-red-100 text-red-800 px-2 py-1 hover:bg-red-200"
                  >
                    <XCircle className="h-3 w-3" /> Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function AdjusterOrchestrator() {
  const [claimId, setClaimId] = useState("CLM-2026-1001");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const [completedPhases, setCompletedPhases] = useState<Set<string>>(new Set());
  const [currentPhase, setCurrentPhase] = useState<string | null>(null);
  const [pendingGates, setPendingGates] = useState<Set<string>>(new Set());
  const [phaseTools, setPhaseTools] = useState<Record<string, string[]>>({});

  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(rawText: string) {
    const text = rawText.trim();
    if (!text || loading) return;

    const historySnapshot = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: rawText }]);
    setInput("");
    setLoading(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "", tools: [] }]);

    try {
      const resp = await fetch(`${ORCHESTRATOR_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: historySnapshot }),
      });

      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          const chunk = line.startsWith("data: ") ? line.slice(6) : line.slice(5);
          if (!chunk || chunk === "[DONE]") continue;
          appendToAssistant(chunk);
        }
      }
    } catch (err: any) {
      appendToAssistant(`\n\n[Error: ${err?.message ?? "request failed"}]`);
    } finally {
      setLoading(false);
      setCurrentPhase(null);
    }
  }

  function appendToAssistant(chunk: string) {
    const toolStartMatch = chunk.match(/\[Tool:\s*([^\]]+)\]\s*Starting/);
    const toolDoneMatch = chunk.match(/\[Tool:\s*([^\]]+)\]\s*Done/);

    if (toolStartMatch) {
      const toolName = toolStartMatch[1].trim();
      const phase = TOOL_TO_PHASE[toolName];
      if (phase) setCurrentPhase(phase);
      if (toolName === "create_approval_request") {
        // A gate was just opened — surface it as pending until the next approvals refresh confirms.
      }
    }
    if (toolDoneMatch) {
      const toolName = toolDoneMatch[1].trim();
      const phase = TOOL_TO_PHASE[toolName];
      if (phase) {
        setCompletedPhases((prev) => new Set([...prev, phase]));
        setCurrentPhase((cur) => (cur === phase ? null : cur));
        setPhaseTools((prev) => {
          const existing = prev[phase] ?? [];
          if (existing.includes(toolName)) return prev;
          return { ...prev, [phase]: [...existing, toolName] };
        });
      }
    }

    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (!last || last.role !== "assistant") return prev;

      const tools = [...(last.tools ?? [])];
      let content = last.content;
      const remaining = chunk;
      TOOL_REGEX.lastIndex = 0;
      let cleaned = "";
      let lastEnd = 0;
      let m: RegExpExecArray | null;
      while ((m = TOOL_REGEX.exec(remaining)) !== null) {
        cleaned += remaining.slice(lastEnd, m.index);
        tools.push(`${m[1].trim()}: ${m[2]}`);
        lastEnd = TOOL_REGEX.lastIndex;
      }
      cleaned += remaining.slice(lastEnd);
      content += cleaned;

      next[next.length - 1] = { ...last, content, tools };
      return next;
    });
  }

  function refreshPendingGateSet() {
    fetch(`${ORCHESTRATION_MCP_BASE}/approvals/pending?claim_id=${encodeURIComponent(claimId)}`)
      .then((r) => r.json())
      .then((data: Approval[]) => {
        setPendingGates(new Set(Array.isArray(data) ? data.map((a) => a.gate_type) : []));
      })
      .catch(() => {});
  }

  useEffect(() => {
    refreshPendingGateSet();
  }, [claimId, messages.length]);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "hsl(var(--adjuster))" }}>
            Adjuster Orchestrator
          </h1>
          <p className="text-sm text-muted-foreground">
            Full Claim Intake → Settlement journey — 15 agents + 4 HITL gates orchestrated in one conversation (port 8920)
          </p>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-lg border bg-muted/30">
          <label className="text-sm font-medium whitespace-nowrap">Claim ID:</label>
          <input
            className="rounded-md border px-3 py-1.5 text-sm bg-background w-44"
            value={claimId}
            onChange={(e) => setClaimId(e.target.value)}
            placeholder="CLM-2026-1001"
          />
        </div>
      </div>

      {/* Main layout: phase tracker + chat */}
      <div className="flex gap-4 mb-4">
        <PhaseTracker completedPhases={completedPhases} currentPhase={currentPhase} pendingGates={pendingGates} phaseTools={phaseTools} />

        <div className="flex-1 flex flex-col border rounded-lg bg-card overflow-hidden" style={{ height: 620 }}>
          <div className="px-4 py-2 border-b bg-muted/50 flex items-center justify-between text-sm">
            <span className="font-medium">AdjusterOrchestrator</span>
            <span className="text-xs text-muted-foreground font-mono">{ORCHESTRATOR_URL}</span>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
            {messages.length === 0 && (
              <div className="text-sm text-muted-foreground italic space-y-2">
                <p>
                  Start by asking the orchestrator to run the adjuster workflow for a claim. It will move through
                  fraud screening, damage/enrichment, classification, triage, loss assessment, reserve, settlement,
                  and payment — pausing at each HITL gate until you decide it in the panel below.
                </p>
                <p className="text-[11px]">
                  Tip: after approving or rejecting a gate below, click "Continue Workflow" to resume the same conversation.
                </p>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                <div
                  className={cn(
                    "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                    m.role === "user" ? "bg-primary text-primary-foreground whitespace-pre-wrap" : "bg-muted"
                  )}
                >
                  {m.tools && m.tools.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {m.tools.map((t, ti) => (
                        <span
                          key={ti}
                          className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300"
                        >
                          <Wrench className="h-2.5 w-2.5" />
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  {m.content ? (
                    m.role === "assistant" ? <ChatMarkdown content={m.content} /> : m.content
                  ) : (m.role === "assistant" && loading && i === messages.length - 1 ? (
                    <Loader2 className="h-3 w-3 animate-spin inline" />
                  ) : "")}
                </div>
              </div>
            ))}
          </div>

          <form
            className="flex gap-2 p-2 border-t"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <input
              className="flex-1 rounded-md border px-3 py-2 text-sm bg-background"
              placeholder={`Run the adjuster workflow for claim ${claimId || "..."}`}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </form>

          <div className="px-3 py-2 border-t bg-muted/20 flex gap-2">
            <button
              onClick={() => send(`Run the adjuster workflow for claim ${claimId}`)}
              disabled={loading || !claimId.trim()}
              className="rounded-md border px-3 py-1.5 text-xs bg-muted hover:bg-muted/80 disabled:opacity-40"
            >
              Start Workflow
            </button>
            <button
              onClick={() => send(`Continue the adjuster workflow for claim ${claimId}`)}
              disabled={loading || !claimId.trim()}
              className="rounded-md border px-3 py-1.5 text-xs bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-40 font-medium"
            >
              Continue Workflow (after a HITL decision)
            </button>
          </div>
        </div>
      </div>

      <ApprovalsPanel claimId={claimId} onDecided={refreshPendingGateSet} />
    </div>
  );
}
