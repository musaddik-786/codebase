import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowLeftRight,
  BarChart3,
  Calendar,
  CheckCircle2,
  Camera,
  ChevronLeft,
  ChevronRight,
  Clock,
  FileText,
  Loader2,
  Mail,
  MapPin,
  Phone,
  ScanSearch,
  Send,
  ShieldCheck,
  Sparkles,
  Video,
  Wrench,
  X,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  type Approval,
  decideApproval,
  decideClaimGate,
  fetchPendingApprovals,
  runAdjusterWorkflow,
} from "@/lib/adjuster-orchestrator";

// Human-readable labels for gate_type — falls back to the raw value for any
// gate not listed here (e.g. a new gate added later).
const GATE_LABELS: Record<string, string> = {
  coverage_verification_review: "Coverage Verification Review",
  triage_approval: "Triage Approval",
  damage_assessment_review: "Damage Assessment Review",
  reserve_approval: "Reserve Approval",
  settlement_approval: "Settlement Approval",
  payment_approval: "Payment Approval",
};

// Gates the orchestrator opens as a visible record only — they never pause
// the workflow, unlike everything else in GATE_LABELS above (which the
// orchestrator's own code/prompt actually waits on before proceeding). Used
// to keep "paused" language limited to gates that are genuinely blocking.
//
// damage_assessment_review moved here 2026-07-23: nothing downstream reads
// its approval status anymore (Reserve/Settlement/etc. now run through their
// own independent endpoints, not gated on this), and Loss Assessment's Save
// button already auto-approves it as a side effect — the blocking banner's
// direct Approve/Reject buttons just let the adjuster rubber-stamp it without
// ever reviewing Loss Assessment. Audit-only still surfaces the AI's
// recommendation for visibility, without a redundant/bypassable action.
const AUDIT_ONLY_GATES = new Set(["triage_approval", "damage_assessment_review"]);

function isBlockingApproval(a: Approval): boolean {
  return !AUDIT_ONLY_GATES.has(a.gate_type);
}

interface CaseData {
  claim: {
    claimNumber: string;
    policyholder: string;
    lossType: string;
    severity: string;
    status: string;
    location: string;
  };
  evidencePhotos: Array<{ documentId: string; fileName: string; url: string }>;
  intakeValidation: {
    status: "NotRun" | "Complete" | "Incomplete";
    completenessScore: number | null;
    blockingFailure: boolean;
    failureReasons: string[];
    overridden: boolean;
    overriddenBy: string;
    overriddenNotes: string;
  };
  investigationCompletion: {
    completed: boolean;
    completedBy: string;
    completedAt: string;
  };
  tools: {
    fraudScore: number | null;
    damageSeverity: string;
    stormEvent: string;
    coverageVerdict: string;
    claimComplexity: string;
    evidenceSummary: string;
    triageFraudRiskScore: number | null;
    routing: string;
    lossNetPayable: number | null;
    lossEstimatedTotal: number | null;
    repairVsReplaceRecommendation: string;
    repairCost: number | null;
    replacementCost: number | null;
  };
  comparison: {
    similarClaims: Array<{
      claimNumber: string;
      matchScore: number;
      claimAmount: number;
      settlement: number;
      outcome: string;
      outcomeTone: "green" | "orange" | "red";
      days: number;
      fraudRisk: string;
      matchingFactors: string[];
    }>;
    stats: {
      similarCount: number;
      avgApprovalRate: number;
      avgSettlement: number;
      avgResolutionDays: number;
    };
    insights: {
      settlementLow: number;
      settlementHigh: number;
      resolutionDays: number;
      approvalRate: number;
    };
  };
}

function money(n: number): string {
  return `$${n.toLocaleString("en-US")}`;
}

function severityBadge(severity: string): string {
  const s = severity.toLowerCase();
  if (s.includes("high") || s.includes("critical")) return "bg-rose-500";
  if (s.includes("medium") || s.includes("moderate")) return "bg-amber-400";
  return "bg-emerald-500";
}

function matchCircle(score: number): string {
  if (score >= 85) return "bg-emerald-500";
  if (score >= 70) return "bg-amber-500";
  return "bg-slate-400";
}

function outcomePill(tone: "green" | "orange" | "red"): string {
  if (tone === "green") return "bg-emerald-500";
  if (tone === "red") return "bg-rose-500";
  return "bg-amber-500";
}

function fraudPill(risk: string): string {
  const r = risk.toLowerCase();
  if (r === "high") return "border-rose-300 text-rose-600 bg-rose-50";
  if (r === "medium") return "border-amber-300 text-amber-600 bg-amber-50";
  return "border-emerald-300 text-emerald-600 bg-emerald-50";
}

// ── Schedule Interview slot picker ──────────────────────────────────────────
const MORNING_SLOTS = ["9:00 AM", "10:00 AM", "11:00 AM"];
const AFTERNOON_SLOTS = ["1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM"];
const INTERVIEW_DAYS_AHEAD = 14;
const INTERVIEW_PAGE_SIZE = 3;

interface InterviewDay {
  iso: string;
  weekday: string;
  monthDay: string;
  label: string;
}

// Rolling window of candidate interview days starting tomorrow — computed at
// render time (not cached at module load) so the list stays correct across
// midnight without a page refresh.
function buildInterviewDays(): InterviewDay[] {
  const days: InterviewDay[] = [];
  const today = new Date();
  for (let i = 1; i <= INTERVIEW_DAYS_AHEAD; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() + i);
    const weekday = d.toLocaleDateString("en-US", { weekday: "short" });
    const monthDay = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    days.push({
      iso: d.toISOString().slice(0, 10),
      weekday: weekday.toUpperCase(),
      monthDay,
      label: `${weekday}, ${monthDay}, ${d.getFullYear()}`,
    });
  }
  return days;
}

export default function CaseInvestigation({
  claimNumber,
  onBack,
}: {
  claimNumber: string;
  onBack: () => void;
}) {
  const { toast } = useToast();
  const [data, setData] = useState<CaseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [brokenPhotos, setBrokenPhotos] = useState<Record<string, boolean>>({});
  const [running, setRunning] = useState(false);
  const [pendingApprovals, setPendingApprovals] = useState<Approval[]>([]);
  const [decidingId, setDecidingId] = useState<string | null>(null);
  const [proofModalOpen, setProofModalOpen] = useState(false);
  const [proofMessage, setProofMessage] = useState(
    "Please provide additional documentation (e.g. receipts, photos, police report) to support your claim."
  );
  const [sendingProof, setSendingProof] = useState(false);

  const [interviewModalOpen, setInterviewModalOpen] = useState(false);
  const [interviewDays] = useState<InterviewDay[]>(() => buildInterviewDays());
  const [interviewPage, setInterviewPage] = useState(0);
  const [interviewMode, setInterviewMode] = useState<"Video Call" | "Phone Call">("Video Call");
  const [interviewSlot, setInterviewSlot] = useState<{ iso: string; time: string } | null>(null);
  const [interviewNotesOpen, setInterviewNotesOpen] = useState(false);
  const [interviewNotes, setInterviewNotes] = useState("");
  const [sendingInterview, setSendingInterview] = useState(false);

  const [intakeOverrideModalOpen, setIntakeOverrideModalOpen] = useState(false);
  const [intakeOverrideNotes, setIntakeOverrideNotes] = useState("");
  const [overridingIntake, setOverridingIntake] = useState(false);
  const [completingInvestigation, setCompletingInvestigation] = useState(false);

  const fetchCaseData = async (opts: { showSpinner: boolean } = { showSpinner: true }) => {
    if (opts.showSpinner) {
      setLoading(true);
      setError(null);
      setData(null);
    }
    try {
      const res = await fetch(
        `/api/adjuster/case-investigation?claimNumber=${encodeURIComponent(claimNumber)}`
      );
      const json = await res.json().catch(() => null);
      if (!res.ok) throw new Error(json?.error || "Could not load case investigation.");
      setData(json);
      return true;
    } catch (err) {
      if (opts.showSpinner)
        setError(err instanceof Error ? err.message : "Could not load case investigation.");
      return false;
    } finally {
      if (opts.showSpinner) setLoading(false);
    }
  };

  // Surfaces whatever HITL gate(s) are actually pending for this claim — e.g.
  // the code-level coverage_verification_review hard-stop, or triage_approval.
  // Non-fatal on failure: the banner just won't show, same as before this existed.
  const refreshApprovals = async (): Promise<Approval[]> => {
    try {
      const approvals = await fetchPendingApprovals(claimNumber);
      setPendingApprovals(approvals);
      return approvals;
    } catch {
      return [];
    }
  };

  useEffect(() => {
    void fetchCaseData({ showSpinner: true });
    void refreshApprovals();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [claimNumber]);

  const recordAction = (action: string) => {
    toast({ title: "Action Recorded", description: `Successfully executed: ${action}` });
  };

  const overrideIntakeValidation = async () => {
    const notes = intakeOverrideNotes.trim();
    if (!notes) {
      toast({
        title: "Reason Required",
        description: "Enter a reason for overriding intake validation.",
        variant: "destructive",
      });
      return;
    }
    setOverridingIntake(true);
    try {
      const res = await fetch(
        `/api/adjuster/override-intake-validation?claimNumber=${encodeURIComponent(claimNumber)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ notes }),
        }
      );
      const json = await res.json().catch(() => null);
      if (!res.ok) throw new Error(json?.error || "Could not override intake validation.");
      toast({ title: "Intake Validation Overridden", description: "Marked complete by manual override." });
      setIntakeOverrideModalOpen(false);
      setIntakeOverrideNotes("");
      await fetchCaseData({ showSpinner: false });
    } catch (err) {
      toast({
        title: "Override Failed",
        description: err instanceof Error ? err.message : "Could not override intake validation.",
        variant: "destructive",
      });
    } finally {
      setOverridingIntake(false);
    }
  };

  const completeInvestigation = async () => {
    // Gated on Complete Claim Intake Validation being done first — button is
    // disabled in that case too, this is defense in depth. The real
    // enforcement is server-side in /complete-investigation.
    if (completingInvestigation || !data || data.intakeValidation.status !== "Complete" || data.investigationCompletion.completed) {
      return;
    }
    setCompletingInvestigation(true);
    try {
      const res = await fetch(
        `/api/adjuster/complete-investigation?claimNumber=${encodeURIComponent(claimNumber)}`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) }
      );
      const json = await res.json().catch(() => null);
      if (!res.ok) throw new Error(json?.error || "Could not complete the investigation.");
      recordAction("Complete Investigation");
      await fetchCaseData({ showSpinner: false });

      // Best-effort, fire-and-forget: approve the routing agent's pending
      // HITL gate (triage_approval) on the orchestrator. Never block the UI
      // — short timeout, errors only produce an informational follow-up toast.
      void (async () => {
        let gateNote: string;
        try {
          const result = await Promise.race([
            decideClaimGate(claimNumber, "Approved", { gateType: "triage_approval" }),
            new Promise<never>((_, reject) =>
              setTimeout(() => reject(new Error("timeout")), 4000)
            ),
          ]);
          gateNote =
            result.decided > 0
              ? "Routing gate (triage approval) approved."
              : "No pending routing gate to approve.";
        } catch {
          gateNote = "Orchestrator unreachable — gate approval skipped.";
        }
        toast({ title: "Workflow Gate", description: gateNote });
        void refreshApprovals();
      })();
    } catch (err) {
      toast({
        title: "Could Not Complete Investigation",
        description: err instanceof Error ? err.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setCompletingInvestigation(false);
    }
  };

  // Sends the Request Additional Proof message — lands as an outbound,
  // pending-follow-up entry in communication_history, which the policyholder
  // sees in Follow My Claims under "Latest Actions" (same table the
  // CommunicationAgent writes to for its own notifications).
  const sendAdditionalProofRequest = async () => {
    const message = proofMessage.trim();
    if (!message) return;
    setSendingProof(true);
    try {
      const res = await fetch(
        `/api/adjuster/request-additional-proof?claimNumber=${encodeURIComponent(claimNumber)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message }),
        }
      );
      const json = await res.json().catch(() => null);
      if (!res.ok) throw new Error(json?.error || "Could not send the request.");
      toast({
        title: "Additional Proof Requested",
        description: `The policyholder has been notified and will see this in Follow My Claims.`,
      });
      setProofModalOpen(false);
    } catch (err) {
      toast({
        title: "Request Failed",
        description: err instanceof Error ? err.message : "Could not send the request.",
        variant: "destructive",
      });
    } finally {
      setSendingProof(false);
    }
  };

  const visibleInterviewDays = interviewDays.slice(
    interviewPage,
    interviewPage + INTERVIEW_PAGE_SIZE
  );

  const closeInterviewModal = () => {
    setInterviewModalOpen(false);
    setInterviewPage(0);
    setInterviewMode("Video Call");
    setInterviewSlot(null);
    setInterviewNotesOpen(false);
    setInterviewNotes("");
  };

  // Sends the Schedule Interview details — same communication_history
  // notification pattern as Request Additional Proof above.
  const sendScheduleInterview = async () => {
    if (!interviewSlot) return;
    const day = interviewDays.find((d) => d.iso === interviewSlot.iso);
    if (!day) return;
    setSendingInterview(true);
    try {
      const res = await fetch(
        `/api/adjuster/schedule-interview?claimNumber=${encodeURIComponent(claimNumber)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mode: interviewMode,
            dateLabel: day.label,
            time: interviewSlot.time,
            notes: interviewNotes.trim(),
          }),
        }
      );
      const json = await res.json().catch(() => null);
      if (!res.ok) throw new Error(json?.error || "Could not schedule the interview.");
      toast({
        title: "Interview Scheduled",
        description: `The policyholder has been notified and will see this in Follow My Claims.`,
      });
      closeInterviewModal();
    } catch (err) {
      toast({
        title: "Scheduling Failed",
        description: err instanceof Error ? err.message : "Could not schedule the interview.",
        variant: "destructive",
      });
    } finally {
      setSendingInterview(false);
    }
  };

  // Approve/reject any gate shown in the pending-approvals banner below —
  // generic, unlike completeInvestigation's triage_approval-specific action.
  const handleDecide = async (approval: Approval, decision: "Approved" | "Rejected") => {
    setDecidingId(approval.approval_id);
    try {
      await decideApproval(approval.approval_id, decision, "adjuster_1");
      toast({
        title: decision,
        description: `${GATE_LABELS[approval.gate_type] ?? approval.gate_type} ${decision.toLowerCase()}.`,
      });
      await Promise.all([refreshApprovals(), fetchCaseData({ showSpinner: false })]);
    } catch (err) {
      toast({
        title: "Decision Failed",
        description: err instanceof Error ? err.message : "Could not record the decision.",
        variant: "destructive",
      });
    } finally {
      setDecidingId(null);
    }
  };

  const runInvestigation = async () => {
    if (running) return;
    setRunning(true);
    try {
      await runAdjusterWorkflow(claimNumber);
      // Refresh so the AI Investigation Tools "Output" column reflects what the
      // orchestrator just wrote — without this the panel keeps showing whatever
      // was on screen before the run, even though new data landed in Postgres.
      const [, approvals] = await Promise.all([
        fetchCaseData({ showSpinner: false }),
        refreshApprovals(),
      ]);
      // Only a genuinely blocking gate means the workflow is actually paused —
      // audit-only gates (triage_approval) are just a visible record and never
      // stopped anything, so they shouldn't produce a "paused" message.
      const blocking = approvals.filter(isBlockingApproval);
      if (blocking.length > 0) {
        const gateNames = blocking.map((a) => GATE_LABELS[a.gate_type] ?? a.gate_type).join(", ");
        toast({
          title: "Workflow Paused — Approval Needed",
          description: `Claim ${claimNumber} stopped and is waiting on your review: ${gateNames}.`,
        });
      } else {
        toast({
          title: "AI Investigation Complete",
          description: `Orchestrator finished the workflow for claim ${claimNumber}.`,
        });
      }
    } catch (err) {
      toast({
        title: "AI Investigation Failed",
        description:
          err instanceof Error ? err.message : "Could not reach the adjuster orchestrator.",
        variant: "destructive",
      });
    } finally {
      setRunning(false);
    }
  };

  const aiTools = data
    ? [
        {
          name: "Fraud Screening Tool",
          purpose: "Scores likelihood of fraud from claim and policy signals",
          output: data.tools.fraudScore !== null ? `Fraud score: ${data.tools.fraudScore}` : "—",
          tone:
            data.tools.fraudScore === null
              ? "text-slate-500"
              : data.tools.fraudScore >= 70
                ? "text-rose-500"
                : data.tools.fraudScore >= 40
                  ? "text-orange-500"
                  : "text-emerald-600",
        },
        {
          name: "Damage Assessment Tool",
          purpose: "Analyzes the loss description and catalogs damage items",
          output: data.tools.damageSeverity || "—",
          tone: !data.tools.damageSeverity
            ? "text-slate-500"
            : /high|critical/i.test(data.tools.damageSeverity)
              ? "text-orange-500"
              : "text-emerald-600",
        },
        {
          name: "External Data Tool",
          purpose: "Cross-checks the claim against weather and drone imagery",
          output: data.tools.stormEvent || "—",
          tone: data.tools.stormEvent ? "text-slate-700" : "text-slate-500",
        },
        {
          name: "Verification Tool",
          purpose: "Confirms policy status, coverage window, and coverage type match",
          output: data.tools.coverageVerdict || "—",
          tone:
            data.tools.coverageVerdict === "Flagged"
              ? "text-rose-500"
              : data.tools.coverageVerdict === "Confirmed"
                ? "text-emerald-600"
                : "text-slate-500",
        },
        {
          name: "Claim Classification Tool",
          purpose: "Assigns claim complexity and a routing recommendation",
          output: data.tools.claimComplexity || "—",
          tone: data.tools.claimComplexity ? "text-slate-700" : "text-slate-500",
        },
        {
          name: "Evidence Validation Tool",
          purpose: "Flags suspicious or inauthentic evidence submissions",
          output: data.tools.evidenceSummary || "—",
          tone: !data.tools.evidenceSummary || /not yet run/i.test(data.tools.evidenceSummary)
            ? "text-slate-500"
            : /flagged/i.test(data.tools.evidenceSummary)
              ? "text-orange-500"
              : "text-emerald-600",
        },
        {
          name: "Triage Tool",
          purpose: "Prioritizes the claim from severity, complexity, fraud risk, and age",
          output:
            data.tools.triageFraudRiskScore !== null
              ? `Priority Score: ${data.tools.triageFraudRiskScore}`
              : "—",
          tone: data.tools.triageFraudRiskScore === null ? "text-slate-500" : "text-slate-700",
        },
        {
          name: "Routing Tool",
          purpose: "Assigns the claim to an adjuster based on triage results",
          output: data.tools.routing || "—",
          tone: data.tools.routing ? "text-slate-700" : "text-slate-500",
        },
        {
          name: "Loss Assessment Tool",
          purpose: "Computes total estimated loss, deductible, and net payable",
          output: data.tools.lossNetPayable !== null ? money(data.tools.lossNetPayable) : "—",
          tone: data.tools.lossNetPayable !== null ? "text-slate-700" : "text-slate-500",
        },
        {
          name: "Repair vs Replace Tool",
          purpose: "Recommends repairing or replacing the damaged item",
          output: data.tools.repairVsReplaceRecommendation
            ? `${data.tools.repairVsReplaceRecommendation} (repair ${data.tools.repairCost !== null ? money(data.tools.repairCost) : "—"} / replace ${data.tools.replacementCost !== null ? money(data.tools.replacementCost) : "—"})`
            : "—",
          tone: data.tools.repairVsReplaceRecommendation ? "text-slate-700" : "text-slate-500",
        },
      ]
    : [];

  return (
    <div className="animate-in fade-in duration-500 pb-12">
      {/* Header row */}
      <div className="flex items-center gap-4 mb-5">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 text-sm font-bold text-slate-800 hover:text-violet-700 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Cases
        </button>
        <span className="h-6 w-px bg-slate-300" />
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Case Investigation</h1>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24 text-slate-500 gap-3">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span className="font-medium">Loading case...</span>
        </div>
      ) : error || !data ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-8 text-center text-red-700 font-medium">
          {error || "Failed to load case"}
        </div>
      ) : (
        <>
          {/* Claim header card */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm px-6 py-5 mb-6">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-xl font-extrabold text-slate-900">
                Claim #{data.claim.claimNumber}
              </h2>
              <span
                className={`inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white ${severityBadge(data.claim.severity)}`}
              >
                {data.claim.severity}
              </span>
              <span className="inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white bg-sky-500">
                {data.claim.status}
              </span>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm font-medium text-slate-500">
              <span className="font-bold text-slate-800">{data.claim.policyholder}</span>
              <span className="text-slate-300">•</span>
              <span>{data.claim.lossType}</span>
              <span className="text-slate-300">•</span>
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" /> {data.claim.location}
              </span>
            </div>
          </div>

          {/* Pending HITL gate(s) — split so "paused" only ever describes a
              gate that actually blocks the workflow (e.g. coverage_verification_review).
              Audit-only gates (triage_approval) never stopped anything, so they
              get their own calmer, clearly-labeled section instead. */}
          {(() => {
            const blockingApprovals = pendingApprovals.filter(isBlockingApproval);
            const auditApprovals = pendingApprovals.filter((a) => !isBlockingApproval(a));
            return (
              <>
                {blockingApprovals.length > 0 && (
                  <div className="rounded-xl border border-amber-300 bg-amber-50 px-6 py-5 mb-6">
                    <h3 className="flex items-center gap-2 text-sm font-extrabold text-amber-800">
                      <AlertTriangle className="h-4 w-4" />
                      {blockingApprovals.length > 1 ? "Pending Approvals" : "Pending Approval"} —
                      workflow is paused for this claim
                    </h3>
                    <div className="mt-3 space-y-3">
                      {blockingApprovals.map((a) => (
                        <div
                          key={a.approval_id}
                          className="rounded-lg border border-amber-200 bg-white p-4"
                        >
                          <p className="text-[11px] font-extrabold uppercase tracking-wide text-amber-700">
                            {GATE_LABELS[a.gate_type] ?? a.gate_type}
                          </p>
                          <p className="mt-1 text-sm text-slate-700">{a.summary}</p>
                          <div className="mt-3 flex gap-2">
                            <button
                              onClick={() => handleDecide(a, "Approved")}
                              disabled={decidingId === a.approval_id}
                              className="inline-flex items-center gap-1.5 rounded-md bg-emerald-600 hover:bg-emerald-700 px-3 py-1.5 text-xs font-bold text-white transition-colors disabled:opacity-60"
                            >
                              <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                            </button>
                            <button
                              onClick={() => handleDecide(a, "Rejected")}
                              disabled={decidingId === a.approval_id}
                              className="inline-flex items-center gap-1.5 rounded-md bg-rose-600 hover:bg-rose-700 px-3 py-1.5 text-xs font-bold text-white transition-colors disabled:opacity-60"
                            >
                              <X className="h-3.5 w-3.5" /> Reject
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {auditApprovals.length > 0 && (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-6 py-5 mb-6">
                    <h3 className="flex items-center gap-2 text-sm font-extrabold text-slate-600">
                      <CheckCircle2 className="h-4 w-4" />
                      Audit Note{auditApprovals.length > 1 ? "s" : ""} — informational only, does
                      not block this claim
                    </h3>
                    <div className="mt-3 space-y-3">
                      {auditApprovals.map((a) => (
                        <div
                          key={a.approval_id}
                          className="rounded-lg border border-slate-200 bg-white p-4"
                        >
                          <p className="text-[11px] font-extrabold uppercase tracking-wide text-slate-500">
                            {GATE_LABELS[a.gate_type] ?? a.gate_type}
                          </p>
                          <p className="mt-1 text-sm text-slate-700">{a.summary}</p>
                          <div className="mt-3 flex gap-2">
                            <button
                              onClick={() => handleDecide(a, "Approved")}
                              disabled={decidingId === a.approval_id}
                              className="inline-flex items-center gap-1.5 rounded-md bg-slate-600 hover:bg-slate-700 px-3 py-1.5 text-xs font-bold text-white transition-colors disabled:opacity-60"
                            >
                              <CheckCircle2 className="h-3.5 w-3.5" /> Acknowledge
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            );
          })()}

          {/* Evidence + AI tools */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Evidence Review Panel */}
            <div className="rounded-xl overflow-hidden shadow-md border border-slate-200 bg-white">
              <div className="bg-gradient-to-r from-blue-600 via-sky-500 to-cyan-400 px-6 py-4">
                <h3 className="flex items-center gap-2.5 text-white font-extrabold text-lg">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/20">
                    <Camera className="h-4 w-4" />
                  </span>
                  Evidence Review Panel
                </h3>
                <p className="mt-0.5 text-xs text-sky-100/90 font-medium">
                  Review and manage case evidence
                </p>
              </div>
              <div className="p-5">
                <div className="rounded-full bg-gradient-to-r from-blue-600 to-cyan-500 px-5 py-2.5 mb-5 flex items-center gap-2 text-white text-sm font-bold">
                  <Camera className="h-4 w-4" /> Uploaded Evidence Photos ({data.evidencePhotos.length})
                </div>
                {data.evidencePhotos.length === 0 ? (
                  <div className="rounded-xl border-2 border-dashed border-sky-200 bg-sky-50/50 py-12 text-center">
                    <Camera className="h-10 w-10 mx-auto text-sky-300 mb-3" />
                    <p className="text-sm font-semibold text-slate-500">No evidence photos uploaded</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    {data.evidencePhotos.map((p, i) => (
                      <div
                        key={p.documentId}
                        className="rounded-2xl border border-sky-200 bg-sky-50 p-2 shadow-sm"
                      >
                        <div className="rounded-xl bg-sky-100/70 h-28 flex items-center justify-center overflow-hidden">
                          {brokenPhotos[p.documentId] ? (
                            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-200/80">
                              <Camera className="h-5 w-5 text-sky-500" />
                            </span>
                          ) : (
                            <img
                              src={p.url}
                              alt={p.fileName}
                              className="h-full w-full object-cover rounded-xl"
                              onError={() =>
                                setBrokenPhotos((prev) => ({ ...prev, [p.documentId]: true }))
                              }
                            />
                          )}
                        </div>
                        <p className="mt-2 text-center text-[11px] font-bold text-sky-700">
                          Evidence Photo {i + 1}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* AI Investigation Tools */}
            <div className="rounded-xl overflow-hidden shadow-md border border-slate-200 bg-white">
              <div className="bg-gradient-to-r from-violet-600 via-purple-600 to-fuchsia-500 px-6 py-4">
                <h3 className="flex items-center gap-2.5 text-white font-extrabold text-lg">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/20">
                    <ScanSearch className="h-4 w-4" />
                  </span>
                  AI Investigation Tools
                </h3>
                <p className="mt-0.5 text-xs text-fuchsia-100/90 font-medium">
                  Run AI-powered analysis on this case
                </p>
              </div>
              <div className="p-5">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="pb-2.5 text-xs font-bold text-slate-500">Tool</th>
                      <th className="pb-2.5 text-xs font-bold text-slate-500">Purpose</th>
                      <th className="pb-2.5 text-xs font-bold text-slate-500">Output</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {aiTools.map((tool) => (
                      <tr key={tool.name}>
                        <td className="py-3.5 pr-2 align-top">
                          <span className="flex items-start gap-1.5 text-[13px] font-bold text-slate-800">
                            <Sparkles className="h-3.5 w-3.5 mt-0.5 shrink-0 text-violet-500" />
                            {tool.name}
                          </span>
                        </td>
                        <td className="py-3.5 pr-2 align-top text-xs font-medium text-slate-500">
                          {tool.purpose}
                        </td>
                        <td className={`py-3.5 pr-2 align-top text-xs font-bold ${tool.tone}`}>
                          {tool.output}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="mt-4 flex items-center justify-end gap-3">
                  <p className="mr-auto text-[11px] italic text-slate-500">
                    Runs the full AI investigation through the adjuster orchestrator.
                  </p>
                  <button
                    onClick={runInvestigation}
                    disabled={running}
                    className="inline-flex items-center gap-2 rounded-md bg-gradient-to-r from-violet-600 to-fuchsia-500 hover:from-violet-700 hover:to-fuchsia-600 px-4 py-2 text-xs font-bold text-white shadow-sm transition-colors disabled:opacity-60"
                  >
                    {running ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5" />
                    )}
                    {running ? "Running..." : "Run AI Investigation"}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Smart Comparison */}
          <div className="rounded-xl overflow-hidden shadow-md border border-slate-200 bg-white mb-6">
            <div className="bg-gradient-to-r from-emerald-600 via-emerald-500 to-green-500 px-6 py-4">
              <h3 className="flex items-center gap-2.5 text-white font-extrabold text-lg">
                <ArrowLeftRight className="h-4.5 w-4.5" /> Smart Comparison
                <span className="inline-flex rounded-full bg-white/20 px-3 py-0.5 text-[10px] font-bold">
                  AI-Powered
                </span>
              </h3>
              <p className="mt-0.5 text-xs text-emerald-50/90 font-medium">
                Similar historical claims and their final settlements for benchmarking
              </p>
            </div>

            <div className="p-6">
              {/* Stat tiles */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <div className="rounded-xl border border-teal-200 bg-teal-50/60 px-5 py-4">
                  <p className="flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-wider text-teal-600">
                    <ArrowLeftRight className="h-3 w-3" /> Similar Claims
                  </p>
                  <p className="mt-1 text-2xl font-extrabold text-slate-900">
                    {data.comparison.stats.similarCount}
                  </p>
                </div>
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 px-5 py-4">
                  <p className="flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-wider text-emerald-600">
                    <CheckCircle2 className="h-3 w-3" /> Avg Approval Rate
                  </p>
                  <p className="mt-1 text-2xl font-extrabold text-slate-900">
                    {data.comparison.stats.avgApprovalRate}%
                  </p>
                </div>
                <div className="rounded-xl border border-blue-200 bg-blue-50/60 px-5 py-4">
                  <p className="flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-wider text-blue-600">
                    <BarChart3 className="h-3 w-3" /> Avg Settlement
                  </p>
                  <p className="mt-1 text-2xl font-extrabold text-slate-900">
                    {money(data.comparison.stats.avgSettlement)}
                  </p>
                </div>
                <div className="rounded-xl border border-fuchsia-200 bg-fuchsia-50/50 px-5 py-4">
                  <p className="flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-wider text-fuchsia-600">
                    <Calendar className="h-3 w-3" /> Avg Resolution
                  </p>
                  <p className="mt-1 text-2xl font-extrabold text-slate-900">
                    {data.comparison.stats.avgResolutionDays} days
                  </p>
                </div>
              </div>

              {/* Similar claims table */}
              {data.comparison.similarClaims.length === 0 ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 py-10 text-center text-sm font-medium text-slate-500 mb-6">
                  No similar historical claims found
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-slate-200 mb-6">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-slate-200">
                        <th className="px-4 py-3 text-xs font-bold text-slate-600">Claim #</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-600">Match Score</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-600">Claim Amount</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-600">Settlement</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-600">Outcome</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-600">Days</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-600">Fraud Risk</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-600">Matching Factors</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {data.comparison.similarClaims.map((s) => (
                        <tr key={s.claimNumber} className={s.matchScore >= 85 ? "bg-emerald-50/50" : "bg-white"}>
                          <td className="px-4 py-4 text-sm font-bold text-slate-900 whitespace-nowrap">
                            {s.claimNumber}
                          </td>
                          <td className="px-4 py-4">
                            <span className="flex items-center gap-2">
                              <span
                                className={`flex h-10 w-10 items-center justify-center rounded-full text-[11px] font-extrabold text-white ${matchCircle(s.matchScore)}`}
                              >
                                {s.matchScore}%
                              </span>
                              {s.matchScore >= 85 && (
                                <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-bold text-emerald-700">
                                  High Match
                                </span>
                              )}
                            </span>
                          </td>
                          <td className="px-4 py-4 text-sm font-bold text-slate-900">
                            {money(s.claimAmount)}
                          </td>
                          <td
                            className={`px-4 py-4 text-sm font-bold ${s.settlement > 0 ? "text-emerald-600" : "text-rose-500"}`}
                          >
                            {money(s.settlement)}
                          </td>
                          <td className="px-4 py-4">
                            <span
                              className={`inline-flex rounded-full px-3 py-1 text-[10px] font-bold text-white whitespace-nowrap ${outcomePill(s.outcomeTone)}`}
                            >
                              {s.outcome}
                            </span>
                          </td>
                          <td
                            className={`px-4 py-4 text-sm font-bold ${s.days > 30 ? "text-rose-500" : "text-orange-500"}`}
                          >
                            {s.days > 0 ? s.days : "—"}
                          </td>
                          <td className="px-4 py-4">
                            <span
                              className={`inline-flex rounded-full border px-3 py-0.5 text-[10px] font-bold ${fraudPill(s.fraudRisk)}`}
                            >
                              {s.fraudRisk}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <div className="flex flex-col items-start gap-1">
                              {s.matchingFactors.slice(0, 2).map((f) => (
                                <span
                                  key={f}
                                  className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-600"
                                >
                                  {f}
                                </span>
                              ))}
                              {s.matchingFactors.length > 2 && (
                                <span className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">
                                  +{s.matchingFactors.length - 2} more
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* AI Settlement Insights */}
              <div className="rounded-xl bg-slate-900 px-6 py-5 flex items-start gap-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-teal-500/20">
                  <BarChart3 className="h-5 w-5 text-teal-400" />
                </span>
                <div>
                  <p className="flex items-center gap-2 text-sm font-extrabold text-white">
                    AI Settlement Insights
                    <span className="inline-flex rounded-full bg-teal-500/20 px-2.5 py-0.5 text-[10px] font-bold text-teal-300">
                      Smart Analysis
                    </span>
                  </p>
                  <p className="mt-1.5 text-[13px] font-medium leading-relaxed text-slate-300">
                    Based on {data.comparison.stats.similarCount} similar claims, the predicted
                    settlement range is{" "}
                    <span className="font-bold text-emerald-400">
                      {money(data.comparison.insights.settlementLow)} -{" "}
                      {money(data.comparison.insights.settlementHigh)}
                    </span>{" "}
                    with an estimated resolution time of{" "}
                    <span className="font-bold text-emerald-400">
                      {data.comparison.insights.resolutionDays} days
                    </span>
                    . Claims with similar profiles have a{" "}
                    <span className="font-bold text-amber-400">
                      {data.comparison.insights.approvalRate}% approval rate.
                    </span>
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Adjuster Actions */}
          <div className="rounded-xl overflow-hidden shadow-md border border-slate-200 bg-white">
            <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-700 px-6 py-4">
              <h3 className="flex items-center gap-2.5 text-white font-extrabold text-lg">
                <Wrench className="h-4.5 w-4.5" /> Adjuster Actions
              </h3>
              <p className="mt-0.5 text-xs text-slate-300 font-medium">
                Take action on this investigation
              </p>
            </div>
            <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {(() => {
                const iv = data.intakeValidation;
                const investigationDone = data.investigationCompletion.completed;

                // Once the investigation is marked complete, BOTH actions in
                // this panel are locked — the intake check no longer needs
                // acting on regardless of its own status.
                let intakeButton;
                if (iv.status === "Complete" || investigationDone) {
                  const title = iv.overridden
                    ? `Manually overridden by ${iv.overriddenBy || "adjuster"}${iv.overriddenNotes ? `: ${iv.overriddenNotes}` : ""}`
                    : iv.status === "Complete"
                      ? `Passed automatically — ${iv.completenessScore ?? 100}% complete`
                      : "Investigation already completed";
                  intakeButton = (
                    <button
                      disabled
                      title={title}
                      className="flex flex-col items-center justify-center gap-2 rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-5 text-sm font-bold text-emerald-700 cursor-not-allowed"
                    >
                      <ShieldCheck className="h-4.5 w-4.5" />
                      Claim Intake Validated
                    </button>
                  );
                } else if (iv.status === "Incomplete") {
                  intakeButton = (
                    <button
                      onClick={() => setIntakeOverrideModalOpen(true)}
                      title={iv.failureReasons.join("; ") || "Claim data completeness check did not pass"}
                      className="flex flex-col items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 px-4 py-5 text-sm font-bold text-white shadow-md transition-colors"
                    >
                      <ShieldCheck className="h-4.5 w-4.5" />
                      Complete Claim Intake Validation
                    </button>
                  );
                } else {
                  intakeButton = (
                    <button
                      disabled
                      title="Run the AI investigation first to check claim data completeness"
                      className="flex flex-col items-center justify-center gap-2 rounded-xl bg-slate-100 px-4 py-5 text-sm font-bold text-slate-400 cursor-not-allowed"
                    >
                      <ShieldCheck className="h-4.5 w-4.5" />
                      Complete Claim Intake Validation
                    </button>
                  );
                }

                let investigationButton;
                if (investigationDone) {
                  investigationButton = (
                    <button
                      disabled
                      title={`Completed by ${data.investigationCompletion.completedBy || "adjuster"}`}
                      className="flex flex-col items-center justify-center gap-2 rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-5 text-sm font-bold text-emerald-700 cursor-not-allowed"
                    >
                      <ShieldCheck className="h-4.5 w-4.5" />
                      Investigation Completed
                    </button>
                  );
                } else if (iv.status !== "Complete") {
                  investigationButton = (
                    <button
                      disabled
                      title="Complete Claim Intake Validation first"
                      className="flex flex-col items-center justify-center gap-2 rounded-xl bg-slate-100 px-4 py-5 text-sm font-bold text-slate-400 cursor-not-allowed"
                    >
                      <ShieldCheck className="h-4.5 w-4.5" />
                      Complete Investigation
                    </button>
                  );
                } else {
                  investigationButton = (
                    <button
                      onClick={completeInvestigation}
                      disabled={completingInvestigation}
                      className="flex flex-col items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 px-4 py-5 text-sm font-bold text-white shadow-md transition-colors disabled:opacity-60"
                    >
                      {completingInvestigation ? (
                        <Loader2 className="h-4.5 w-4.5 animate-spin" />
                      ) : (
                        <ShieldCheck className="h-4.5 w-4.5" />
                      )}
                      {completingInvestigation ? "Completing..." : "Complete Investigation"}
                    </button>
                  );
                }

                return (
                  <>
                    {intakeButton}
                    {investigationButton}
                  </>
                );
              })()}
              <button
                onClick={() => setProofModalOpen(true)}
                className="flex flex-col items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 px-4 py-5 text-sm font-bold text-white shadow-md transition-colors"
              >
                <Mail className="h-4.5 w-4.5" />
                Request Additional Proof
              </button>
              <button
                onClick={() => setInterviewModalOpen(true)}
                className="flex flex-col items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 px-4 py-5 text-sm font-bold text-white shadow-md transition-colors"
              >
                <Calendar className="h-4.5 w-4.5" />
                Schedule Interview
              </button>
            </div>
          </div>
        </>
      )}

      {/* Request Additional Proof modal */}
      {proofModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-lg rounded-xl bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
              <h3 className="flex items-center gap-2 text-sm font-extrabold text-slate-900">
                <Mail className="h-4 w-4 text-orange-500" /> Request Additional Proof
              </h3>
              <button
                onClick={() => setProofModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="px-6 py-5">
              <label className="text-xs font-bold text-slate-500">Message to policyholder</label>
              <textarea
                value={proofMessage}
                onChange={(e) => setProofMessage(e.target.value)}
                rows={4}
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 focus:border-orange-400 focus:outline-none focus:ring-1 focus:ring-orange-400"
                placeholder="Describe the documents or evidence needed..."
              />
              <p className="mt-2 text-[11px] text-slate-500">
                This will appear in the policyholder's Follow My Claims — Latest Actions.
              </p>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-6 py-4">
              <button
                onClick={() => setProofModalOpen(false)}
                disabled={sendingProof}
                className="rounded-md border border-slate-300 px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                onClick={sendAdditionalProofRequest}
                disabled={sendingProof || !proofMessage.trim()}
                className="inline-flex items-center gap-1.5 rounded-md bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 px-4 py-2 text-xs font-bold text-white disabled:opacity-60"
              >
                {sendingProof ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5" />}
                {sendingProof ? "Sending..." : "Send Request"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Complete Claim Intake Validation — manual override modal */}
      {intakeOverrideModalOpen && data && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-lg rounded-xl bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
              <h3 className="flex items-center gap-2 text-sm font-extrabold text-slate-900">
                <ShieldCheck className="h-4 w-4 text-amber-500" /> Override Claim Intake Validation
              </h3>
              <button
                onClick={() => setIntakeOverrideModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="px-6 py-5">
              {data.intakeValidation.failureReasons.length > 0 && (
                <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
                  <p className="font-bold mb-1">The automated check did not pass:</p>
                  <ul className="list-disc list-inside space-y-0.5">
                    {data.intakeValidation.failureReasons.map((reason, i) => (
                      <li key={i}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}
              <label className="text-xs font-bold text-slate-500">Reason for override</label>
              <textarea
                value={intakeOverrideNotes}
                onChange={(e) => setIntakeOverrideNotes(e.target.value)}
                rows={4}
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400"
                placeholder="Explain why intake validation is being marked complete despite the failed check..."
              />
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-6 py-4">
              <button
                onClick={() => setIntakeOverrideModalOpen(false)}
                disabled={overridingIntake}
                className="rounded-md border border-slate-300 px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                onClick={overrideIntakeValidation}
                disabled={overridingIntake || !intakeOverrideNotes.trim()}
                className="inline-flex items-center gap-1.5 rounded-md bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 px-4 py-2 text-xs font-bold text-white disabled:opacity-60"
              >
                {overridingIntake ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
                {overridingIntake ? "Saving..." : "Confirm Override"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Schedule Interview modal */}
      {interviewModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-3xl rounded-2xl border border-emerald-100 bg-gradient-to-br from-emerald-50/60 to-white shadow-xl">
            <div className="flex items-center justify-between px-6 pt-6">
              <h3 className="flex items-center gap-2.5 text-base font-extrabold text-slate-900">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-600 text-white">
                  <Calendar className="h-4.5 w-4.5" />
                </span>
                Schedule Interview
              </h3>
              <button
                onClick={closeInterviewModal}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="px-6 pt-5">
              <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">Mode:</p>
              <div className="mt-2 flex gap-2">
                <button
                  onClick={() => setInterviewMode("Video Call")}
                  className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-bold transition-colors ${
                    interviewMode === "Video Call"
                      ? "bg-emerald-500 text-white"
                      : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                  }`}
                >
                  <Video className="h-4 w-4" /> Video Call
                </button>
                <button
                  onClick={() => setInterviewMode("Phone Call")}
                  className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-bold transition-colors ${
                    interviewMode === "Phone Call"
                      ? "bg-emerald-500 text-white"
                      : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                  }`}
                >
                  <Phone className="h-4 w-4" /> Phone Call
                </button>
              </div>
            </div>

            <div className="px-6 pt-5">
              <div className="flex items-center justify-between">
                <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-slate-500">
                  <Clock className="h-3.5 w-3.5" /> Select Available Slots
                </p>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setInterviewPage((p) => Math.max(0, p - INTERVIEW_PAGE_SIZE))}
                    disabled={interviewPage === 0}
                    className="rounded-full p-1 text-slate-400 hover:text-slate-600 disabled:opacity-30 disabled:hover:text-slate-400"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() =>
                      setInterviewPage((p) =>
                        Math.min(interviewDays.length - INTERVIEW_PAGE_SIZE, p + INTERVIEW_PAGE_SIZE)
                      )
                    }
                    disabled={interviewPage + INTERVIEW_PAGE_SIZE >= interviewDays.length}
                    className="rounded-full p-1 text-slate-400 hover:text-slate-600 disabled:opacity-30 disabled:hover:text-slate-400"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-4">
                {visibleInterviewDays.map((day) => {
                  const daySelected = interviewSlot?.iso === day.iso;
                  return (
                    <div
                      key={day.iso}
                      className="overflow-hidden rounded-xl border border-slate-200 bg-white"
                    >
                      <div className="flex items-center justify-between bg-slate-50 px-4 py-3">
                        <div>
                          <p className="text-[11px] font-extrabold uppercase tracking-wide text-emerald-600">
                            {day.weekday}
                          </p>
                          <p className="text-sm font-extrabold text-slate-800">{day.monthDay}</p>
                        </div>
                        <span
                          className={`h-4 w-4 rounded-full border-2 ${
                            daySelected ? "border-emerald-500 bg-emerald-500" : "border-emerald-300"
                          }`}
                        />
                      </div>
                      <div className="px-4 py-3">
                        <p className="text-[10px] font-extrabold uppercase tracking-wide text-orange-500">
                          Morning
                        </p>
                        <div className="mt-1.5 space-y-1.5">
                          {MORNING_SLOTS.map((time) => (
                            <SlotButton
                              key={time}
                              time={time}
                              selected={interviewSlot?.iso === day.iso && interviewSlot?.time === time}
                              onClick={() => setInterviewSlot({ iso: day.iso, time })}
                            />
                          ))}
                        </div>
                        <p className="mt-3 text-[10px] font-extrabold uppercase tracking-wide text-violet-500">
                          Afternoon
                        </p>
                        <div className="mt-1.5 space-y-1.5">
                          {AFTERNOON_SLOTS.map((time) => (
                            <SlotButton
                              key={time}
                              time={time}
                              selected={interviewSlot?.iso === day.iso && interviewSlot?.time === time}
                              onClick={() => setInterviewSlot({ iso: day.iso, time })}
                            />
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="px-6 pt-4">
              <button
                onClick={() => setInterviewNotesOpen((v) => !v)}
                className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-700"
              >
                <FileText className="h-4 w-4" /> Add additional notes
              </button>
              {interviewNotesOpen && (
                <textarea
                  value={interviewNotes}
                  onChange={(e) => setInterviewNotes(e.target.value)}
                  rows={3}
                  placeholder="Anything the policyholder should know ahead of the interview..."
                  className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
                />
              )}
            </div>

            <div className="flex items-center gap-4 px-6 py-5">
              <button
                onClick={sendScheduleInterview}
                disabled={!interviewSlot || sendingInterview}
                className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 px-5 py-2.5 text-sm font-bold text-white shadow-md transition-colors disabled:opacity-60"
              >
                {sendingInterview ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                {sendingInterview ? "Sending..." : "Send"}
              </button>
              <button
                onClick={closeInterviewModal}
                disabled={sendingInterview}
                className="text-sm font-semibold text-slate-500 hover:text-slate-700 disabled:opacity-60"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SlotButton({
  time,
  selected,
  onClick,
}: {
  time: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${
        selected
          ? "bg-emerald-500 text-white"
          : "bg-slate-50 text-slate-600 hover:bg-slate-100"
      }`}
    >
      <span
        className={`h-3.5 w-3.5 rounded-full border-2 ${
          selected ? "border-white bg-white/30" : "border-emerald-300"
        }`}
      />
      {time}
    </button>
  );
}
