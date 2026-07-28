import { useState, useEffect, useMemo, useRef } from "react";
import { useToast } from "@/hooks/use-toast";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  ClipboardList,
  Clock,
  DollarSign,
  FileText,
  Loader2,
  MessageSquare,
  Plus,
  Save,
  Scale,
  Search,
  Send,
  Shield,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wand2,
  Wrench,
  XCircle,
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { continueAdjusterWorkflow, decideClaimGate } from "@/lib/adjuster-orchestrator";
import { ADJUSTER_ORCHESTRATOR_URL } from "@/config/agents";

interface ReserveAnalysis {
  systemRecommendedReserve: number | null;
  adjusterSetReserve: number | null;
  variancePercent: number | string | null;
  severityBufferPercent: number | null;
  fraudBufferPercent: number | null;
  rationale: string;
}

interface SettlementAnalysis {
  settlementAmount: number | null;
  deductible: number | null;
  remainingCoverageLimit: number | null;
  recommendedAction: string;
  stpScore: number | null;
  notes: string;
}

interface RiskFlag {
  // item_type is the current shape (score_leakage now compares FNOL estimate
  // against repair/replacement item costs, not vendor invoices); vendor_id
  // kept for back-compat with any flags saved before that change.
  item_type?: string;
  vendor_id?: string;
  issue?: string;
  severity?: string;
}

interface LeakageAnalysis {
  totalEstimatedCost: number | null;
  totalActualCost: number | null;
  overallVariancePercent: number | null;
  leakageScore: number | null;
  leakageRisk: string;
  riskFlags: RiskFlag[];
  recommendation: string;
}

interface EligibilityGate {
  pass: boolean;
  value: unknown;
  threshold: unknown;
  skip?: boolean;
}

interface EligibilityAnalysis {
  eligibleForAutoAdjudication: boolean | null;
  decision: string;
  stpCategory: string;
  gates: Record<string, EligibilityGate> | null;
  failedGates: string[];
  recommendation: string;
}

interface PaymentPreview {
  approved: boolean | null;
  coverageConfirmed: string;
  availableAmount: number | null;
  amountSource: string;
  reason: string;
}

const LEAKAGE_RISK_LEVELS = ["Low", "Medium", "High", "Critical"];

const formatCurrency = (val: number | null | undefined) => {
  if (val == null) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }).format(val);
};

function severityPill(severity: string): string {
  const s = severity.toLowerCase();
  if (s.includes("critical") || s.includes("severe")) return "bg-red-600";
  if (s.includes("high")) return "bg-orange-500";
  if (s.includes("medium") || s.includes("moderate")) return "bg-amber-500";
  return "bg-emerald-500";
}

export default function LossAssessment() {
  const [claims, setClaims] = useState<any[]>([]);
  const [selectedClaimId, setSelectedClaimId] = useState<string>("");
  const [claimSearch, setClaimSearch] = useState("");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showSummary, setShowSummary] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [analysisRun, setAnalysisRun] = useState(false);
  const [calcInputs, setCalcInputs] = useState({ parts: 0, labor: 0, depreciation: 0, deductible: 0, subrogation: "Low" });
  const [adjusterOverride, setAdjusterOverride] = useState("Accept System Recommendation");
  const [adjusterNotes, setAdjusterNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [reserveRun, setReserveRun] = useState(false);
  const [reserveBusy, setReserveBusy] = useState(false);
  const [reserveRejected, setReserveRejected] = useState(false);
  const [reserveInput, setReserveInput] = useState("");
  const [reserveSaving, setReserveSaving] = useState(false);
  const [reserveAnalysis, setReserveAnalysis] = useState<ReserveAnalysis | null>(null);
  const [settlementRun, setSettlementRun] = useState(false);
  const [settlementBusy, setSettlementBusy] = useState(false);
  const [settlementRejected, setSettlementRejected] = useState(false);
  const [settlementInput, setSettlementInput] = useState("");
  const [settlementSaving, setSettlementSaving] = useState(false);
  const [settlementAnalysis, setSettlementAnalysis] = useState<SettlementAnalysis | null>(null);
  const [leakageRun, setLeakageRun] = useState(false);
  const [leakageBusy, setLeakageBusy] = useState(false);
  const [leakageAnalysis, setLeakageAnalysis] = useState<LeakageAnalysis | null>(null);
  const [leakageRiskOverride, setLeakageRiskOverride] = useState("");
  const [leakageNotes, setLeakageNotes] = useState("");
  const [leakageSaving, setLeakageSaving] = useState(false);
  const [eligibilityAnalysis, setEligibilityAnalysis] = useState<EligibilityAnalysis | null>(null);
  const [paymentPreview, setPaymentPreview] = useState<PaymentPreview | null>(null);
  const [paymentDeciding, setPaymentDeciding] = useState(false);
  const [paymentDecisionResult, setPaymentDecisionResult] = useState<"" | "approved" | "rejected">("");
  const [explainOpen, setExplainOpen] = useState(false);
  const [summaryOpen, setSummaryOpen] = useState(true);
  const { toast } = useToast();
  // Tracks the currently selected claim so late-arriving loadAssessment
  // responses for a previously selected claim are discarded.
  const selectedClaimRef = useRef<string>("");

  const loadAssessment = async (claimId: string, opts?: { hydrateLeakage?: boolean }) => {
    const res = await fetch(`/api/adjuster/loss-assessment?claimNumber=${claimId}`);
    if (!res.ok) throw new Error("Failed to load loss assessment data");
    const json = await res.json();
    // Guard against a stale response landing after the user switched claims.
    if (selectedClaimRef.current && selectedClaimRef.current !== claimId) return json;
    setData(json);
    if (json.assessment) {
      setCalcInputs({
        parts: json.assessment.partsCost ?? 0,
        labor: json.assessment.laborCost ?? 0,
        depreciation: json.assessment.depreciationPercent ?? 0,
        deductible: json.assessment.deductible ?? 0,
        subrogation: json.assessment.subrogationLikelihood || "Low",
      });
      setAdjusterOverride(json.assessment.adjusterOverride || "Accept System Recommendation");
      setAdjusterNotes(json.assessment.notes || "");
    } else {
      setCalcInputs({ parts: 0, labor: 0, depreciation: 0, deductible: 0, subrogation: "Low" });
      setAdjusterOverride("Accept System Recommendation");
      setAdjusterNotes("");
    }
    // Hydrate the leakage decision fields from previously saved values so a
    // persisted override/notes reappear after reload. Only runs on the
    // initial claim load (opts.hydrateLeakage) — never on the generic
    // reloads triggered by other save/analysis actions, so in-progress
    // leakage edits are never overwritten by last-saved DB values.
    if (opts?.hydrateLeakage) {
      if (json.leakage?.adjusterRiskOverride) {
        setLeakageRiskOverride(json.leakage.adjusterRiskOverride);
      }
      if (json.leakage?.adjusterNotes) {
        setLeakageNotes(json.leakage.adjusterNotes);
      }
      // A saved decision implies the analysis was already run — open the
      // Financial Leakage panel so the persisted values are visible on reload.
      if (json.leakage?.adjusterRiskOverride || json.leakage?.adjusterNotes) {
        setLeakageRun(true);
      }
    }
    return json;
  };

  // Best-effort: ask the orchestrator to continue the adjuster workflow for
  // this claim. Waits up to `waitMs` for the run to finish so fresh results
  // land in the DB before we reload, but never cancels the stream — it keeps
  // running (and the conversation history keeps recording) in the background.
  const continueWorkflowBestEffort = async (claimId: string, waitMs = 8000) => {
    try {
      const run = continueAdjusterWorkflow(claimId).catch(() => {
        // Orchestrator unreachable — proceed with DB values.
      });
      await Promise.race([run, new Promise((resolve) => setTimeout(resolve, waitMs))]);
    } catch {
      // Never block the page on the orchestrator.
    }
  };

  const runOrchestrator = async (label: string, fn: () => Promise<string>) => {
    if (busyAction) return;
    setBusyAction(label);
    try {
      const description = await fn();
      toast({ title: label, description });
    } catch (err) {
      toast({
        title: label,
        description:
          err instanceof Error ? err.message : "The action could not be completed.",
        variant: "destructive",
      });
    } finally {
      setBusyAction(null);
    }
  };

  useEffect(() => {
    fetch("/api/claims")
      .then((res) => res.json())
      .then((json) => {
        const claimsList = json.claims || [];
        setClaims(claimsList);
        if (claimsList.length > 0) {
          const urlParams = new URLSearchParams(window.location.search);
          const claimParam = urlParams.get("claim");
          if (claimParam && claimsList.find((c: any) => c.id === claimParam)) {
            setSelectedClaimId(claimParam);
          } else {
            setSelectedClaimId(claimsList[0].id);
          }
        } else {
          setLoading(false);
        }
      })
      .catch(() => {
        setError("Failed to load claims list.");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedClaimId) return;
    setLoading(true);
    setError(null);
    setAnalysisRun(false);
    setReserveRun(false);
    setReserveRejected(false);
    setReserveInput("");
    setReserveAnalysis(null);
    setSettlementRun(false);
    setSettlementBusy(false);
    setSettlementRejected(false);
    setSettlementInput("");
    setSettlementAnalysis(null);
    setLeakageRun(false);
    setLeakageBusy(false);
    setLeakageAnalysis(null);
    setLeakageRiskOverride("");
    setLeakageNotes("");
    setEligibilityAnalysis(null);
    setPaymentPreview(null);
    setPaymentDeciding(false);
    setPaymentDecisionResult("");
    selectedClaimRef.current = selectedClaimId;
    loadAssessment(selectedClaimId, { hydrateLeakage: true })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedClaimId]);

  const filteredClaims = useMemo(() => {
    if (!claimSearch.trim()) return claims;
    const q = claimSearch.toLowerCase();
    return claims.filter((c: any) =>
      String(c.id).toLowerCase().includes(q) || String(c.policyholder || "").toLowerCase().includes(q)
    );
  }, [claims, claimSearch]);

  const handleAction = (action: string) => {
    toast({ title: "Action Recorded", description: `Successfully executed: ${action}` });
  };

  const steps = ["Initial Assessment", "AI Analysis", "Market Validation", "Final Estimate"];
  const isSiu = String(data?.decision?.recommendedAction || "").toLowerCase().includes("siu");

  // Derived loss calculation outputs
  const grossLoss = calcInputs.parts + calcInputs.labor;
  const depreciationAmt = Math.round(grossLoss * (calcInputs.depreciation / 100));
  const netLoss = grossLoss - depreciationAmt;
  const totalEstimate = Math.max(0, netLoss - calcInputs.deductible);
  // Final Recommendation ← repair_vs_replacement_decisions.decision (saved
  // value), unless the adjuster has picked a non-Accept override locally.
  const finalRecommendation =
    adjusterOverride && !/^accept/i.test(adjusterOverride)
      ? adjusterOverride
      : data?.finalDecision || data?.systemRecommendation || data?.assessment?.systemRecommendation || "—";

  const levelChip = (value: string) => {
    const v = value.toLowerCase();
    if (v.includes("high") || v.includes("critical") || v.includes("severe") || v.includes("complex")) return "bg-red-500";
    if (v.includes("medium") || v.includes("moderate")) return "bg-amber-500";
    return "bg-emerald-500";
  };

  const saveLossAssessment = async () => {
    if (saving || !selectedClaimId) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/adjuster/save-loss-assessment?claimNumber=${selectedClaimId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ adjusterOverride, notes: adjusterNotes }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || "Failed to save loss assessment");

      await loadAssessment(selectedClaimId);
      const decisionNote = json.decisionUpdated
        ? " Repair vs Replace decision recorded."
        : json.decisionNote
          ? ` (${json.decisionNote}.)`
          : "";
      toast({
        title: "Loss Assessment Saved",
        description: `Final recommendation: ${json.finalRecommendation || finalRecommendation}.${decisionNote}`,
      });

      // Best-effort, fire-and-forget: approve the pending Repair vs Replacement
      // HITL gate on the orchestrator. Never block or fail the save — short
      // timeout, errors only produce an informational follow-up toast.
      void (async () => {
        let gateNote: string;
        try {
          const result = await Promise.race([
            decideClaimGate(selectedClaimId, "Approved", { gateType: "damage_assessment_review" }),
            new Promise<never>((_, reject) =>
              setTimeout(() => reject(new Error("timeout")), 4000)
            ),
          ]);
          gateNote =
            result.decided > 0
              ? "Repair vs Replacement gate approved."
              : "No pending Repair vs Replacement gate to approve.";
        } catch {
          gateNote = "Orchestrator unreachable — gate approval skipped.";
        }
        toast({ title: "Workflow Gate", description: gateNote });
      })();
    } catch (err) {
      toast({
        title: "Save Failed",
        description: err instanceof Error ? err.message : "Could not save the loss assessment.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const runReserveAnalysis = async () => {
    if (reserveBusy || !selectedClaimId) return;
    setReserveBusy(true);
    try {
      // Runs through the orchestrator's own /reserve-analysis endpoint — a
      // small, dedicated flow (scoped tools + prompt, single awaited JSON
      // response) separate from /chat's full Phase A-F conversation, which
      // still hard-stops after Phase B and never reaches this agent. Unlike
      // the old continueWorkflowBestEffort, this is a real, deterministic
      // request/response — no racing an 8s timeout against a run that might
      // still be in flight.
      const res = await fetch(`${ADJUSTER_ORCHESTRATOR_URL}/reserve-analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_number: selectedClaimId }),
      });
      const json = await res.json().catch(() => null);
      if (!res.ok) throw new Error(json?.detail || "Could not compute the reserve recommendation.");
      setReserveAnalysis({
        systemRecommendedReserve: json.system_recommended_reserve ?? null,
        adjusterSetReserve: json.adjuster_set_reserve ?? null,
        variancePercent: json.variance_percent ?? null,
        severityBufferPercent: json.severity_buffer_percent ?? null,
        fraudBufferPercent: json.fraud_buffer_percent ?? null,
        rationale: json.rationale ?? "",
      });
      await loadAssessment(selectedClaimId);
      setReserveRun(true);
      setReserveRejected(false);
      setReserveInput("");
      toast({ title: "Reserve Recommendation", description: `Reserve recommendation computed for claim ${selectedClaimId}.` });
    } catch (err) {
      toast({
        title: "Reserve Recommendation",
        description: err instanceof Error ? err.message : "Could not load the reserve recommendation.",
        variant: "destructive",
      });
    } finally {
      setReserveBusy(false);
    }
  };

  const runSettlementAnalysis = async () => {
    if (settlementBusy || !selectedClaimId) return;
    setSettlementBusy(true);
    try {
      // Runs through the orchestrator's own /settlement-analysis endpoint —
      // same pattern as Reserve: scoped tools + a dedicated prompt, single
      // awaited JSON response, not the old continueWorkflowBestEffort race.
      const res = await fetch(`${ADJUSTER_ORCHESTRATOR_URL}/settlement-analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_number: selectedClaimId }),
      });
      const json = await res.json().catch(() => null);
      if (!res.ok) throw new Error(json?.detail || "Could not compute the settlement recommendation.");
      setSettlementAnalysis({
        settlementAmount: json.settlement_amount ?? null,
        deductible: json.deductible ?? null,
        remainingCoverageLimit: json.remaining_coverage_limit ?? null,
        recommendedAction: json.recommended_action ?? "",
        stpScore: json.stp_score ?? null,
        notes: json.notes ?? "",
      });
      await loadAssessment(selectedClaimId);
      setSettlementRun(true);
      setSettlementRejected(false);
      setSettlementInput("");
      toast({
        title: "Settlement Recommendation",
        description: `Settlement recommendation computed for claim ${selectedClaimId}.`,
      });
    } catch (err) {
      toast({
        title: "Settlement Recommendation",
        description: err instanceof Error ? err.message : "Could not load the settlement recommendation.",
        variant: "destructive",
      });
    } finally {
      setSettlementBusy(false);
    }
  };

  const runLeakageAnalysis = async () => {
    if (leakageBusy || !selectedClaimId) return;
    setLeakageBusy(true);
    try {
      // Runs through the orchestrator's own /financial-leakage-analysis
      // endpoint — which now also runs Payment Eligibility and a read-only
      // Payment Trigger preview in the same call (see server.py). Nothing
      // here commits anything; the adjuster's own Approve/Reject Payment
      // buttons below are the only thing that can actually disburse.
      const res = await fetch(`${ADJUSTER_ORCHESTRATOR_URL}/financial-leakage-analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_number: selectedClaimId }),
      });
      const json = await res.json().catch(() => null);
      if (!res.ok) throw new Error(json?.detail || "Could not compute the financial leakage analysis.");
      const leakage = json.leakage ?? {};
      const eligibility = json.eligibility ?? {};
      const preview = json.paymentPreview ?? {};
      setLeakageAnalysis({
        totalEstimatedCost: leakage.total_estimated_cost ?? null,
        totalActualCost: leakage.total_actual_cost ?? null,
        overallVariancePercent: leakage.overall_variance_percent ?? null,
        leakageScore: leakage.leakage_score ?? null,
        leakageRisk: leakage.leakage_risk ?? "",
        riskFlags: Array.isArray(leakage.risk_flags) ? leakage.risk_flags : [],
        recommendation: leakage.recommendation ?? "",
      });
      setLeakageRiskOverride(leakage.leakage_risk ?? "");
      setLeakageNotes("");
      setEligibilityAnalysis({
        eligibleForAutoAdjudication: eligibility.eligible_for_auto_adjudication ?? null,
        decision: eligibility.decision ?? "",
        stpCategory: eligibility.stp_category ?? "",
        gates: eligibility.gates ?? null,
        failedGates: Array.isArray(eligibility.failed_gates) ? eligibility.failed_gates : [],
        recommendation: eligibility.recommendation ?? "",
      });
      setPaymentPreview({
        approved: preview.approved ?? null,
        coverageConfirmed: preview.coverage_confirmed ?? "",
        availableAmount: preview.available_amount ?? null,
        amountSource: preview.amount_source ?? "",
        reason: preview.reason ?? "",
      });
      setPaymentDecisionResult("");
      await loadAssessment(selectedClaimId);
      setLeakageRun(true);
      toast({
        title: "Financial Leakage",
        description: `Financial leakage, payment eligibility, and payment readiness computed for claim ${selectedClaimId}.`,
      });
    } catch (err) {
      toast({
        title: "Financial Leakage",
        description: err instanceof Error ? err.message : "Could not run the financial leakage analysis.",
        variant: "destructive",
      });
    } finally {
      setLeakageBusy(false);
    }
  };

  const saveLeakageDecision = async () => {
    if (leakageSaving || !selectedClaimId) return;
    setLeakageSaving(true);
    try {
      const res = await fetch(`/api/adjuster/save-financial-leakage?claimNumber=${selectedClaimId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ riskOverride: leakageRiskOverride, notes: leakageNotes }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || "Failed to save the financial leakage decision");
      await loadAssessment(selectedClaimId);
      toast({ title: "Financial Leakage Saved", description: `Risk level ${leakageRiskOverride || "unchanged"} recorded.` });

      // Best-effort, fire-and-forget: approve the pending financial_leakage_review
      // HITL gate on the orchestrator — same pattern as saveReserveAmount/saveSettlementAmount.
      void (async () => {
        let gateNote: string;
        try {
          const result = await Promise.race([
            decideClaimGate(selectedClaimId, "Approved", { gateType: "financial_leakage_review" }),
            new Promise<never>((_, reject) =>
              setTimeout(() => reject(new Error("timeout")), 4000)
            ),
          ]);
          gateNote =
            result.decided > 0
              ? "Financial leakage review gate approved."
              : "No pending financial leakage review gate to approve.";
        } catch {
          gateNote = "Orchestrator unreachable — gate approval skipped.";
        }
        toast({ title: "Workflow Gate", description: gateNote });
      })();
    } catch (err) {
      toast({
        title: "Save Failed",
        description: err instanceof Error ? err.message : "Could not save the financial leakage decision.",
        variant: "destructive",
      });
    } finally {
      setLeakageSaving(false);
    }
  };

  // The adjuster's final payment decision — the only action in this whole
  // page that can actually disburse money. Calls the orchestrator's
  // deterministic (non-LLM) /payment-decision endpoint directly; see
  // server.py's payment_decision() for why this is never an LLM turn.
  const decidePayment = async (decision: "Approved" | "Rejected") => {
    if (paymentDeciding || !selectedClaimId) return;
    if (decision === "Approved" && (paymentPreview?.availableAmount == null || paymentPreview.availableAmount <= 0)) {
      toast({
        title: "Cannot Approve Payment",
        description: "No valid available amount was found for this claim — run the analysis again once loss assessment data exists.",
        variant: "destructive",
      });
      return;
    }
    setPaymentDeciding(true);
    try {
      const res = await fetch(`${ADJUSTER_ORCHESTRATOR_URL}/payment-decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_number: selectedClaimId,
          decision,
          amount: decision === "Approved" ? paymentPreview?.availableAmount : undefined,
        }),
      });
      const json = await res.json().catch(() => null);
      if (!res.ok) throw new Error(json?.detail || "Could not record the payment decision.");

      if (decision === "Rejected") {
        setPaymentDecisionResult("rejected");
        toast({ title: "Payment Rejected", description: `Payment rejected for claim ${selectedClaimId}.` });
      } else if (json.disbursed) {
        setPaymentDecisionResult("approved");
        toast({
          title: "Payment Approved & Disbursed",
          description: `Disbursement ${json.disbursement?.payment_id ?? ""} created for ${formatCurrency(json.disbursement?.amount)}.`,
        });
      } else {
        // Approved by the adjuster, but create_payment_disbursement's own
        // internal safety checks blocked it (e.g. Full-STP eligibility
        // failed, coverage not confirmed, or amount is zero) — report why,
        // don't claim success.
        toast({
          title: "Payment Not Disbursed",
          description: json.reason || json.error || "The disbursement could not be created.",
          variant: "destructive",
        });
      }
      await loadAssessment(selectedClaimId);

      // Best-effort, fire-and-forget: decide the payment_approval gate —
      // reuses the gate label already scaffolded in case-investigation.tsx.
      void (async () => {
        let gateNote: string;
        try {
          const result = await Promise.race([
            decideClaimGate(selectedClaimId, decision, { gateType: "payment_approval" }),
            new Promise<never>((_, reject) => setTimeout(() => reject(new Error("timeout")), 4000)),
          ]);
          gateNote =
            result.decided > 0
              ? `Payment approval gate ${decision.toLowerCase()}.`
              : "No pending payment approval gate to decide.";
        } catch {
          gateNote = "Orchestrator unreachable — gate decision skipped.";
        }
        toast({ title: "Workflow Gate", description: gateNote });
      })();
    } catch (err) {
      toast({
        title: "Payment Decision Failed",
        description: err instanceof Error ? err.message : "Could not record the payment decision.",
        variant: "destructive",
      });
    } finally {
      setPaymentDeciding(false);
    }
  };

  const saveReserveAmount = async (amount: number, successMessage: string) => {
    if (reserveSaving || !selectedClaimId) return;
    setReserveSaving(true);
    try {
      const res = await fetch(`/api/adjuster/save-reserve?claimNumber=${selectedClaimId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ adjustedReserve: amount }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || "Failed to save the reserve amount");
      await loadAssessment(selectedClaimId);
      // Deliberately NOT resetting reserveRejected here (unlike other save
      // flows): reserveAnalysis still holds the variance computed against the
      // PRE-save adjuster reserve (often "not applicable" on the first run).
      // Keeping the rejected section open lets the adjuster hit "Rerun
      // Analysis" right after saving to get a real variance against the
      // amount they just persisted, instead of navigating away and back
      // (which was the only way to force reserveRun back to false before).
      setReserveInput("");
      toast({ title: "Reserve Saved", description: successMessage });

      // Best-effort, fire-and-forget: approve the pending reserve_approval
      // HITL gate on the orchestrator — saving the reserve amount is the
      // adjuster's decision, same pattern as saveLossAssessment above for
      // damage_assessment_review. Never block or fail the save.
      void (async () => {
        let gateNote: string;
        try {
          const result = await Promise.race([
            decideClaimGate(selectedClaimId, "Approved", { gateType: "reserve_approval" }),
            new Promise<never>((_, reject) =>
              setTimeout(() => reject(new Error("timeout")), 4000)
            ),
          ]);
          gateNote =
            result.decided > 0
              ? "Reserve approval gate approved."
              : "No pending reserve approval gate to approve.";
        } catch {
          gateNote = "Orchestrator unreachable — gate approval skipped.";
        }
        toast({ title: "Workflow Gate", description: gateNote });
      })();
    } catch (err) {
      toast({
        title: "Save Failed",
        description: err instanceof Error ? err.message : "Could not save the reserve amount.",
        variant: "destructive",
      });
    } finally {
      setReserveSaving(false);
    }
  };

  const saveSettlementAmount = async (amount: number, successMessage: string) => {
    if (settlementSaving || !selectedClaimId) return;
    setSettlementSaving(true);
    try {
      const res = await fetch(`/api/adjuster/save-settlement?claimNumber=${selectedClaimId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ finalSettlement: amount }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || "Failed to save the settlement amount");
      await loadAssessment(selectedClaimId);
      setSettlementRejected(false);
      setSettlementInput("");
      toast({ title: "Settlement Saved", description: successMessage });

      // Best-effort, fire-and-forget: approve the pending settlement_approval
      // HITL gate on the orchestrator — same pattern as saveReserveAmount above.
      void (async () => {
        let gateNote: string;
        try {
          const result = await Promise.race([
            decideClaimGate(selectedClaimId, "Approved", { gateType: "settlement_approval" }),
            new Promise<never>((_, reject) =>
              setTimeout(() => reject(new Error("timeout")), 4000)
            ),
          ]);
          gateNote =
            result.decided > 0
              ? "Settlement approval gate approved."
              : "No pending settlement approval gate to approve.";
        } catch {
          gateNote = "Orchestrator unreachable — gate approval skipped.";
        }
        toast({ title: "Workflow Gate", description: gateNote });
      })();
    } catch (err) {
      toast({
        title: "Save Failed",
        description: err instanceof Error ? err.message : "Could not save the settlement amount.",
        variant: "destructive",
      });
    } finally {
      setSettlementSaving(false);
    }
  };

  return (
    <div className="animate-in fade-in duration-500 pb-16">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-violet-950 to-purple-800 px-7 py-5 shadow-md mb-5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
            <ClipboardList className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-white">Loss Assessment</h1>
            <p className="mt-0.5 text-sm text-violet-200/80 font-medium">Evaluate damages and calculate loss estimates</p>
          </div>
        </div>
        <button
          onClick={() => setShowSummary(!showSummary)}
          className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-4 py-2 text-xs font-bold text-white hover:bg-white/20 transition-colors whitespace-nowrap"
        >
          <ChevronRight className={`h-3.5 w-3.5 transition-transform ${showSummary ? "" : "rotate-180"}`} />
          {showSummary ? "Hide Summary" : "Show Summary"}
        </button>
      </div>

      <div className={`grid grid-cols-1 gap-6 ${showSummary ? "xl:grid-cols-[1fr_300px]" : ""}`}>
        <div className="space-y-5 min-w-0">
          {/* Progress stepper */}
          <div className="rounded-xl bg-gradient-to-r from-rose-50 via-violet-50 to-rose-50 border border-violet-100 px-8 py-5">
            <div className="flex items-center">
              {steps.map((step, i) => (
                <div key={step} className={`flex items-center ${i < steps.length - 1 ? "flex-1" : ""}`}>
                  <div className="flex flex-col items-center gap-1.5">
                    <div className="w-9 h-9 rounded-full bg-emerald-500 text-white flex items-center justify-center shadow-sm">
                      <CheckCircle2 className="w-5 h-5" />
                    </div>
                    <span className="text-[11px] font-semibold text-slate-600 text-center whitespace-nowrap">{step}</span>
                  </div>
                  {i < steps.length - 1 && (
                    <div className="flex-1 h-0.5 bg-emerald-400 mx-3 -mt-5" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Claim Selection */}
          <div className="rounded-xl bg-slate-950 border border-slate-800 px-6 py-5 shadow-lg">
            <h2 className="flex items-center gap-2 text-white font-extrabold mb-4">
              <FileText className="h-4 w-4 text-violet-300" /> Claim Selection
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <div>
                <label className="block text-[11px] font-bold text-slate-300 mb-1.5">Search Claim</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
                  <input
                    value={claimSearch}
                    onChange={(e) => setClaimSearch(e.target.value)}
                    placeholder="Search claim #"
                    className="w-full rounded-lg bg-slate-900 border border-slate-700 pl-8 pr-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-300 mb-1.5">Claim Number</label>
                <Select value={selectedClaimId} onValueChange={setSelectedClaimId}>
                  <SelectTrigger className="w-full rounded-lg bg-slate-900 border-violet-400/60 text-white font-semibold text-sm h-9">
                    <SelectValue placeholder="Select claim" />
                  </SelectTrigger>
                  <SelectContent>
                    {filteredClaims.map((c: any) => (
                      <SelectItem key={c.id} value={c.id}>{c.id}{c.policyholder ? ` - ${c.policyholder}` : ""}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-300 mb-1.5">Customer Name</label>
                <div className="rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-white font-semibold truncate">
                  {data?.claim?.customerName || "—"}
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-300 mb-1.5">Policy Type</label>
                <div className="rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-white font-semibold truncate">
                  {data?.claim?.policyType || "—"}
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-300 mb-1.5">Claim Status</label>
                <span className="inline-flex rounded-full bg-violet-500 px-3 py-1.5 text-[11px] font-bold text-white whitespace-nowrap mt-0.5">
                  {data?.claim?.status || "—"}
                </span>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-violet-600" /></div>
          ) : error ? (
            <div className="bg-red-50 text-red-600 p-4 rounded-xl border border-red-200 font-medium">{error}</div>
          ) : (
            <>
              {/* Damage Snapshot */}
              <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 flex items-center justify-between border-b border-slate-100">
                  <h2 className="flex items-center gap-2 font-extrabold text-slate-900">
                    <AlertTriangle className="h-5 w-5 text-amber-500" /> Damage Snapshot
                  </h2>
                  <button
                    onClick={() => handleAction("Add New Damage")}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 px-4 py-2 text-xs font-bold text-white shadow-sm transition-colors"
                  >
                    <Plus className="h-3.5 w-3.5" /> Add New Damage
                  </button>
                </div>
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-sm text-slate-500 border-b border-slate-100">
                      <th className="px-6 py-3 font-semibold">Damage ID</th>
                      <th className="px-6 py-3 font-semibold">Category</th>
                      <th className="px-6 py-3 font-semibold">Severity</th>
                      <th className="px-6 py-3 font-semibold text-right">Est. Cost</th>
                      <th className="px-6 py-3 font-semibold">Adjuster Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data?.damages && data.damages.length > 0 ? (
                      data.damages.map((d: any) => (
                        <tr key={d.damageId} className="hover:bg-slate-50 transition-colors">
                          <td className="px-6 py-4 text-sm font-semibold text-slate-800">{d.damageId}</td>
                          <td className="px-6 py-4 text-sm text-slate-800">{d.category}</td>
                          <td className="px-6 py-4">
                            <span className={`inline-flex rounded px-2.5 py-1 text-[11px] font-bold text-white ${severityPill(d.severity)}`}>
                              {d.severity}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right text-sm font-bold text-slate-900">{formatCurrency(d.estimatedCost)}</td>
                          <td className="px-6 py-4 text-sm text-slate-500 max-w-xs truncate" title={d.notes}>{d.notes}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="px-6 py-10 text-center text-slate-500 text-sm">No damage records for this claim yet</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* No AI data notice (shown after AI analysis when nothing is available) */}
              {analysisRun && !data?.analysis && (
                <div className="rounded-xl border border-amber-200 bg-amber-50/60 px-6 py-4 flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5" />
                  <p className="text-xs text-amber-700/90 leading-relaxed">
                    No AI analysis data is available for this claim in the database yet — placeholder values are shown below.
                  </p>
                </div>
              )}

              {/* Loss Calculation Engine (always visible) */}
              {data && (
                <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
                  <div className={`px-6 py-4 flex items-center gap-3 border-b border-slate-100 ${analysisRun ? "" : "bg-amber-50/60"}`}>
                    <DollarSign className={`h-5 w-5 ${analysisRun ? "text-blue-600" : "text-amber-600"}`} />
                    <h2 className="font-extrabold text-slate-900">Loss Calculation Engine</h2>
                    {!analysisRun && (
                      <span className="inline-flex rounded-full bg-amber-400/80 px-3 py-1 text-[10px] font-bold text-white">
                        Under Review
                      </span>
                    )}
                  </div>
                  {!analysisRun ? (
                    <div className="bg-gradient-to-b from-amber-50/70 to-orange-50/40 px-6 py-10 flex flex-col items-center text-center">
                      <div className="relative mb-4">
                        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-500 shadow-md">
                          <Activity className="h-7 w-7 text-white" />
                        </div>
                        <div className="absolute -top-1 -right-2 flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 shadow">
                          <FileText className="h-3 w-3 text-white" />
                        </div>
                      </div>
                      <h3 className="text-base font-extrabold text-amber-700 mb-2">Review in Progress</h3>
                      <p className="max-w-md text-sm text-amber-700/90 leading-relaxed mb-6">
                        This claim is currently under review. The assessment team is validating the submitted
                        information before final calculations can be made.
                      </p>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-xl">
                        {[
                          { label: "Data Collection", status: "Complete", chip: "bg-emerald-500", icon: ClipboardList },
                          { label: "Review", status: "Active", chip: "bg-teal-500", icon: Search },
                          { label: "Calculation", status: "Pending", chip: "bg-amber-400", icon: FileText },
                        ].map((s) => (
                          <div key={s.label} className="rounded-xl border border-amber-200/70 bg-white/80 px-4 py-4 flex flex-col items-center gap-2">
                            <s.icon className="h-5 w-5 text-amber-600" />
                            <span className="text-[11px] font-bold text-slate-700">{s.label}</span>
                            <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-bold text-white ${s.chip}`}>
                              {s.status}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                  <div className="p-6">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <div>
                        <h3 className="flex items-center gap-2 text-sm font-extrabold text-slate-800 mb-4">
                          <Wrench className="h-4 w-4 text-slate-500" /> Calculation Inputs
                        </h3>
                        <div className="grid grid-cols-2 gap-3">
                          {[
                            { key: "parts", label: "Parts Cost ($)" },
                            { key: "labor", label: "Labor Cost ($)" },
                            { key: "depreciation", label: "Depreciation (%)" },
                            { key: "deductible", label: "Deductible ($)" },
                          ].map((f) => (
                            <div key={f.key}>
                              <label className="block text-[11px] font-bold text-slate-600 mb-1">{f.label}</label>
                              <input
                                type="number"
                                value={calcInputs[f.key as keyof typeof calcInputs] as number}
                                onChange={(e) =>
                                  setCalcInputs((prev) => ({ ...prev, [f.key]: Number(e.target.value) || 0 }))
                                }
                                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-500"
                              />
                            </div>
                          ))}
                        </div>
                        <div className="mt-3">
                          <label className="block text-[11px] font-bold text-slate-600 mb-1">Subrogation Likelihood</label>
                          <Select
                            value={calcInputs.subrogation}
                            onValueChange={(v) => setCalcInputs((prev) => ({ ...prev, subrogation: v }))}
                          >
                            <SelectTrigger className="w-full rounded-lg border-slate-200 text-sm font-semibold h-9">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {["Low", "Medium", "High"].map((o) => (
                                <SelectItem key={o} value={o}>{o}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div>
                        <h3 className="flex items-center gap-2 text-sm font-extrabold text-slate-800 mb-4">
                          <TrendingUp className="h-4 w-4 text-slate-500" /> Calculated Outputs
                        </h3>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="rounded-xl bg-slate-100 px-4 py-3.5">
                            <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Gross Loss</div>
                            <div className="mt-1 text-lg font-extrabold text-slate-900">{formatCurrency(grossLoss)}</div>
                          </div>
                          <div className="rounded-xl bg-amber-50 px-4 py-3.5">
                            <div className="text-[10px] font-bold uppercase tracking-wide text-amber-600">Depreciation</div>
                            <div className="mt-1 text-lg font-extrabold text-amber-600">-{formatCurrency(depreciationAmt)}</div>
                          </div>
                          <div className="rounded-xl bg-blue-50 px-4 py-3.5">
                            <div className="text-[10px] font-bold uppercase tracking-wide text-blue-600">Net Loss</div>
                            <div className="mt-1 text-lg font-extrabold text-blue-700">{formatCurrency(netLoss)}</div>
                          </div>
                          <div className="rounded-xl bg-emerald-50 px-4 py-3.5">
                            <div className="text-[10px] font-bold uppercase tracking-wide text-emerald-600">Total Estimate</div>
                            <div className="mt-1 text-lg font-extrabold text-emerald-600">{formatCurrency(totalEstimate)}</div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* System Recommendation banner */}
                    <div className="mt-5 rounded-xl border border-violet-100 bg-gradient-to-r from-violet-50 to-indigo-50 px-5 py-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">System Recommendation</div>
                          <div className="mt-1.5 flex items-center gap-2">
                            <Wrench className="h-4 w-4 text-violet-600" />
                            <span className="text-base font-extrabold text-violet-700">
                              {data?.systemRecommendation || data?.assessment?.systemRecommendation || "—"}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          {data?.assessment?.confidence != null && (
                            <span className="text-xs font-bold text-slate-500">{data?.assessment?.confidence}% confidence</span>
                          )}
                          {data?.analysis?.recommendation && (
                            <button
                              onClick={() => setExplainOpen((v) => !v)}
                              className="inline-flex items-center gap-1 text-xs font-bold text-violet-600 hover:text-violet-800"
                            >
                              <ChevronDown className={`h-3.5 w-3.5 transition-transform ${explainOpen ? "rotate-180" : ""}`} />
                              Explain
                            </button>
                          )}
                        </div>
                      </div>
                      {explainOpen && data?.analysis?.recommendation && (
                        <p className="mt-3 border-t border-violet-100 pt-3 text-sm text-slate-700">
                          {data.analysis.recommendation}
                        </p>
                      )}
                    </div>
                  </div>
                  )}
                </div>
              )}

              {/* Adjuster Decision Panel (always visible) */}
              {data && (
                <div className="rounded-xl overflow-hidden shadow-md border border-slate-800">
                  <div className="bg-gradient-to-r from-stone-900 via-red-950 to-stone-900 px-6 py-3.5 flex items-center gap-3">
                    <ShieldCheck className={`h-4.5 w-4.5 ${analysisRun ? "text-emerald-400" : "text-amber-400"}`} />
                    <h2 className="font-extrabold text-white">Adjuster Decision Panel</h2>
                    {!analysisRun && (
                      <span className="inline-flex rounded-full bg-amber-500 px-3 py-1 text-[10px] font-bold text-white">
                        Review Active
                      </span>
                    )}
                  </div>
                  {!analysisRun ? (
                    <div className="bg-slate-900 px-6 py-10 flex flex-col items-center text-center">
                      <div className="flex h-16 w-16 items-center justify-center rounded-full border-2 border-amber-400/60 bg-amber-400/10 mb-4">
                        <Shield className="h-7 w-7 text-amber-400" />
                      </div>
                      <h3 className="text-base font-extrabold text-white mb-2">Awaiting Review Completion</h3>
                      <p className="max-w-md text-sm text-slate-400 leading-relaxed mb-6">
                        The decision panel is temporarily locked while the review team validates claim
                        documentation. You will be notified when the review is complete.
                      </p>
                      <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-2 text-xs font-semibold">
                        <span className="flex items-center gap-2 text-amber-400">
                          <AlertTriangle className="h-3.5 w-3.5" /> Status: Under Review
                        </span>
                        <span className="flex items-center gap-2 text-slate-400">
                          <Calendar className="h-3.5 w-3.5" /> Est. Completion: 2-3 Business Days
                        </span>
                      </div>
                    </div>
                  ) : (
                  <div className="bg-slate-900 px-6 py-6">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-5">
                      <div>
                        <label className="block text-[11px] font-bold text-slate-400 mb-1.5">System Recommendation</label>
                        <div className="flex items-center gap-2 rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm font-bold text-blue-400">
                          <Wrench className="h-4 w-4 shrink-0" />
                          {data?.systemRecommendation || data?.assessment?.systemRecommendation || "—"}
                        </div>
                      </div>
                      <div>
                        <label className="block text-[11px] font-bold text-slate-400 mb-1.5">Adjuster Override</label>
                        <Select value={adjusterOverride} onValueChange={setAdjusterOverride}>
                          <SelectTrigger className="w-full rounded-lg bg-slate-800 border-slate-700 text-white font-semibold text-sm h-9">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {["Accept System Recommendation", "Repair", "Replace", "Cash Settlement", "Deny"].map((o) => (
                              <SelectItem key={o} value={o}>{o}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <label className="block text-[11px] font-bold text-slate-400 mb-1.5">Final Recommendation</label>
                        <div className="flex items-center gap-2 rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm font-bold text-emerald-400">
                          <CheckCircle2 className="h-4 w-4 shrink-0" />
                          {finalRecommendation}
                        </div>
                      </div>
                    </div>
                    <div className="mb-5">
                      <label className="block text-[11px] font-bold text-slate-400 mb-1.5">Adjuster Notes</label>
                      <textarea
                        value={adjusterNotes}
                        onChange={(e) => setAdjusterNotes(e.target.value)}
                        rows={3}
                        placeholder="Add notes about this loss assessment..."
                        className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500"
                      />
                    </div>
                    <button
                      onClick={saveLossAssessment}
                      disabled={saving}
                      className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 px-5 py-2.5 text-sm font-bold text-white shadow-md transition-colors disabled:opacity-60"
                    >
                      {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                      {saving ? "Saving..." : "Save Loss Assessment"}
                    </button>
                  </div>
                  )}
                </div>
              )}

              {/* Run AI Analysis */}
              <div className="flex flex-wrap items-center gap-4">
                <button
                  onClick={() =>
                    runOrchestrator("Run AI Analysis", async () => {
                      // Best-effort: resume the orchestrator workflow from loss
                      // assessment (same as "Continue Workflow" after a HITL
                      // decision). Never block the UI — bounded wait, ignore errors.
                      await continueWorkflowBestEffort(selectedClaimId);
                      await loadAssessment(selectedClaimId);
                      setAnalysisRun(true);
                      return `AI analysis results loaded for claim ${selectedClaimId}.`;
                    })
                  }
                  disabled={busyAction !== null}
                  className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-fuchsia-600 to-purple-600 hover:from-fuchsia-700 hover:to-purple-700 px-5 py-2.5 text-sm font-bold text-white shadow-md transition-colors disabled:opacity-60"
                >
                  {busyAction === "Run AI Analysis" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  {busyAction === "Run AI Analysis" ? "Running..." : "Run AI Analysis"}
                </button>
                <p className="text-xs italic text-slate-500">
                  Execute automated loss evaluation, coverage validation, and decision recommendation.
                </p>
              </div>

              {/* AI Claim Analysis Summary (shown after AI analysis) */}
              {analysisRun && (
                <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
                  <div className="bg-gradient-to-r from-violet-50 to-purple-50 px-6 py-4 flex items-center gap-3">
                    <Brain className="h-5 w-5 text-violet-600" />
                    <h2 className="font-extrabold text-violet-900">AI Claim Analysis Summary</h2>
                    <span className="inline-flex rounded-full bg-violet-600 px-3 py-1 text-[11px] font-bold text-white">
                      Complete
                    </span>
                    <button
                      onClick={() => setSummaryOpen((v) => !v)}
                      className="ml-auto text-violet-500 hover:text-violet-700"
                    >
                      {summaryOpen ? <ChevronUp className="h-4.5 w-4.5" /> : <ChevronDown className="h-4.5 w-4.5" />}
                    </button>
                  </div>
                  {summaryOpen && (
                  <div className="p-6">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                      <div className="rounded-xl border border-violet-200 bg-violet-50/60 px-4 py-4">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-violet-700 mb-1.5">
                          <DollarSign className="h-3.5 w-3.5" /> Estimated Loss (AI)
                        </div>
                        <div className="text-lg font-extrabold text-violet-900">{formatCurrency(data?.analysis?.estimatedLoss)}</div>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-4">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 mb-1.5">
                          <TrendingDown className="h-3.5 w-3.5" /> Deductible Applied
                        </div>
                        <div className="text-lg font-extrabold text-slate-900">{formatCurrency(data?.analysis?.deductibleApplied)}</div>
                      </div>
                      <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 px-4 py-4">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-700 mb-1.5">
                          <DollarSign className="h-3.5 w-3.5" /> Net Payable Amount
                        </div>
                        <div className="text-lg font-extrabold text-emerald-700">{formatCurrency(data?.analysis?.netPayable)}</div>
                      </div>
                      <div className="rounded-xl border border-amber-200 bg-amber-50/60 px-4 py-4">
                        <div className="text-[11px] font-semibold text-amber-700 mb-1.5">Reserve Recommendation</div>
                        <div className="text-lg font-extrabold text-amber-800">{formatCurrency(data?.analysis?.reserveRecommendation)}</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                      <div className="rounded-xl border border-cyan-200 bg-cyan-50/50 px-4 py-4">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-cyan-700 mb-2">
                          <Wrench className="h-3.5 w-3.5" /> Repair vs Replace
                        </div>
                        <span className="inline-flex rounded-full bg-emerald-600 px-3 py-1.5 text-xs font-bold text-white">
                          {String(data?.analysis?.repairRecommended).toLowerCase().startsWith("y")
                            ? "Repair Recommended"
                            : data?.analysis?.repairRecommended || "—"}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                      <div className="rounded-xl border border-blue-200 bg-blue-50/50 px-4 py-4">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-blue-700 mb-1.5">
                          <BarChart3 className="h-3.5 w-3.5" /> STP Readiness Score
                        </div>
                        <div className="text-lg font-extrabold text-slate-900 mb-2">{data?.analysis?.stpReadiness ?? "—"}</div>
                        {data?.analysis?.stpCategory && (
                          <span className="inline-flex rounded-full bg-blue-600 px-3 py-1 text-[11px] font-bold text-white">
                            {data?.analysis?.stpCategory}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                      <div className="rounded-xl border border-slate-200 bg-white px-4 py-4">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 mb-2">
                          <Shield className="h-3.5 w-3.5 text-emerald-600" /> Fraud Risk Level
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white ${levelChip(String(data?.analysis?.fraudRiskLevel || ""))}`}>
                            {data?.analysis?.fraudRiskLevel || "—"}
                          </span>
                          {data?.analysis?.fraudRiskScore != null && (
                            <span className="text-[11px] font-semibold text-slate-500">Score: {data?.analysis?.fraudRiskScore}</span>
                          )}
                        </div>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-white px-4 py-4">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 mb-2">
                          <Scale className="h-3.5 w-3.5 text-violet-500" /> Subrogation Risk
                        </div>
                        <span className={`inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white ${levelChip(String(data?.analysis?.subrogationRisk || ""))}`}>
                          {data?.analysis?.subrogationRisk || "—"}
                        </span>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-white px-4 py-4">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 mb-2">
                          <Activity className="h-3.5 w-3.5 text-orange-500" /> Complexity Level
                        </div>
                        <span className={`inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white ${levelChip(String(data?.analysis?.complexity || ""))}`}>
                          {data?.analysis?.complexity || "—"}
                        </span>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-white px-4 py-4">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 mb-2">
                          <AlertTriangle className="h-3.5 w-3.5 text-emerald-600" /> Severity Level
                        </div>
                        <span className={`inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white ${severityPill(String(data?.analysis?.severity || ""))}`}>
                          {data?.analysis?.severity || "—"}
                        </span>
                      </div>
                    </div>
                    {data?.analysis?.eligibilityRules?.length > 0 && (
                      <div className="border-t border-slate-100 pt-4">
                        <div className="flex items-center gap-2 text-xs font-bold text-violet-700 mb-3">
                          <ClipboardList className="h-3.5 w-3.5" /> Eligibility Rules Evaluated
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {data?.analysis?.eligibilityRules.map((r: any) => (
                            <span
                              key={r.label}
                              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-bold border ${
                                r.pass
                                  ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                                  : "bg-red-50 border-red-200 text-red-600"
                              }`}
                            >
                              {r.pass ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                              {r.label}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  )}
                </div>
              )}

              {/* AI Recommendation (shown after AI analysis) */}
              {analysisRun && (
                <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
                  <div className="px-6 py-4 flex items-center gap-3 border-b border-slate-100 bg-indigo-50/60">
                    <Wand2 className="h-5 w-5 text-indigo-600" />
                    <h2 className="font-extrabold text-slate-900">AI Recommendation</h2>
                  </div>
                  <div className="p-6">
                    <p className="text-sm font-semibold text-slate-800 mb-5">
                      {data?.analysis?.recommendation || "No AI recommendation available for this claim yet."}
                    </p>
                    {data?.analysis?.confidence != null && (
                      <div>
                        <div className="flex items-center justify-between text-xs font-bold text-slate-600 mb-1.5">
                          <span>AI Confidence Score</span>
                          <span className="text-indigo-600">{data?.analysis?.confidence}%</span>
                        </div>
                        <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all"
                            style={{ width: `${Math.min(100, Math.max(0, data?.analysis?.confidence))}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Reserve Recommendation */}
              <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 flex items-center justify-between gap-3 border-b border-slate-100 bg-blue-50/60">
                  <h2 className="flex items-center gap-3 font-extrabold text-slate-900">
                    <DollarSign className="h-5 w-5 text-blue-600" /> Reserve Recommendation
                  </h2>
                  {!reserveRun && (
                    <button
                      onClick={runReserveAnalysis}
                      disabled={reserveBusy}
                      className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 px-4 py-2 text-xs font-bold text-white shadow-sm transition-colors disabled:opacity-60"
                    >
                      {reserveBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                      {reserveBusy ? "Running..." : "Run AI Analysis"}
                    </button>
                  )}
                </div>
                {reserveRun && (
                  <div className="p-6">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
                      <div className="rounded-xl border border-blue-200 bg-blue-50/40 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">System Recommended Reserve</div>
                        <div className="text-xl font-extrabold text-blue-600">
                          {formatCurrency(reserveAnalysis?.systemRecommendedReserve ?? data?.reserve?.systemRecommendedReserve)}
                        </div>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Adjusted Reserve</div>
                        <div className="text-xl font-extrabold text-slate-900">
                          {formatCurrency(data?.reserve?.adjustedReserve)}
                        </div>
                      </div>
                    </div>

                    {reserveAnalysis && (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
                        <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3.5">
                          <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Variance</div>
                          <div className="mt-1 text-sm font-extrabold text-slate-900">
                            {typeof reserveAnalysis.variancePercent === "number"
                              ? `${reserveAnalysis.variancePercent}%`
                              : reserveAnalysis.variancePercent || "Not applicable — no adjuster reserve set yet"}
                          </div>
                        </div>
                        <div className="rounded-xl border border-amber-200 bg-amber-50/40 px-4 py-3.5">
                          <div className="text-[10px] font-bold uppercase tracking-wide text-amber-700">Severity Buffer</div>
                          <div className="mt-1 text-sm font-extrabold text-amber-800">
                            {reserveAnalysis.severityBufferPercent ?? "—"}%
                          </div>
                        </div>
                        <div className="rounded-xl border border-rose-200 bg-rose-50/40 px-4 py-3.5">
                          <div className="text-[10px] font-bold uppercase tracking-wide text-rose-700">Fraud Buffer</div>
                          <div className="mt-1 text-sm font-extrabold text-rose-800">
                            {reserveAnalysis.fraudBufferPercent ?? "—"}%
                          </div>
                        </div>
                      </div>
                    )}

                    {reserveAnalysis?.rationale && (
                      <div className="rounded-xl border border-blue-100 bg-blue-50/40 px-4 py-3.5 mb-5">
                        <div className="text-[10px] font-bold uppercase tracking-wide text-blue-700 mb-1">Rationale</div>
                        <p className="text-sm text-slate-700">{reserveAnalysis.rationale}</p>
                      </div>
                    )}

                    {reserveAnalysis?.systemRecommendedReserve == null && data?.reserve?.systemRecommendedReserve == null && (
                      <p className="text-xs text-amber-700/90 bg-amber-50/60 border border-amber-200 rounded-lg px-4 py-3 mb-5">
                        No system reserve recommendation is available for this claim in the database yet.
                      </p>
                    )}
                    <div className="flex flex-wrap gap-3">
                      <button
                        onClick={() =>
                          saveReserveAmount(
                            Number(reserveAnalysis?.systemRecommendedReserve ?? data?.reserve?.systemRecommendedReserve ?? 0),
                            "System recommended reserve approved and saved."
                          )
                        }
                        disabled={
                          reserveSaving ||
                          (reserveAnalysis?.systemRecommendedReserve == null && data?.reserve?.systemRecommendedReserve == null)
                        }
                        className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 px-6 py-2.5 text-sm font-bold text-white shadow-sm transition-colors disabled:opacity-60"
                      >
                        {reserveSaving && !reserveRejected ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <CheckCircle2 className="h-4 w-4" />
                        )}
                        Approve
                      </button>
                      <button
                        onClick={() => setReserveRejected(true)}
                        disabled={reserveSaving}
                        className="inline-flex items-center gap-2 rounded-full border border-red-300 bg-white hover:bg-red-50 px-6 py-2.5 text-sm font-bold text-red-600 transition-colors disabled:opacity-60"
                      >
                        <XCircle className="h-4 w-4" /> Reject
                      </button>
                    </div>
                    {reserveRejected && (
                      <div className="mt-5 border-t border-slate-100 pt-5">
                        <label className="block text-[11px] font-bold text-slate-600 mb-1.5">
                          Enter Reserve Amount ($)
                        </label>
                        <div className="flex flex-wrap items-center gap-3">
                          <input
                            type="number"
                            min="0"
                            value={reserveInput}
                            onChange={(e) => setReserveInput(e.target.value)}
                            placeholder="Enter amount"
                            className="w-56 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                          <button
                            onClick={() => {
                              const amt = Number(reserveInput);
                              if (!reserveInput.trim() || !Number.isFinite(amt) || amt < 0) {
                                toast({
                                  title: "Invalid Amount",
                                  description: "Please enter a valid reserve amount.",
                                  variant: "destructive",
                                });
                                return;
                              }
                              saveReserveAmount(amt, `Reserve amount ${formatCurrency(amt)} saved.`);
                            }}
                            disabled={reserveSaving}
                            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 px-5 py-2.5 text-sm font-bold text-white shadow-md transition-colors disabled:opacity-60"
                          >
                            {reserveSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                            {reserveSaving ? "Saving..." : "Save Reserve Amount"}
                          </button>
                          <button
                            onClick={runReserveAnalysis}
                            disabled={reserveBusy}
                            title="Recompute the recommendation against the reserve amount you just saved, so the variance reflects it."
                            className="inline-flex items-center gap-2 rounded-lg border border-blue-300 bg-white hover:bg-blue-50 px-5 py-2.5 text-sm font-bold text-blue-700 transition-colors disabled:opacity-60"
                          >
                            {reserveBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                            {reserveBusy ? "Running..." : "Rerun Analysis"}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Settlement Recommendation */}
              <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 flex items-center justify-between gap-3 border-b border-slate-100 bg-emerald-50/60">
                  <h2 className="flex items-center gap-3 font-extrabold text-slate-900">
                    <Scale className="h-5 w-5 text-emerald-600" /> Settlement Recommendation
                  </h2>
                  {!settlementRun && (
                    <button
                      onClick={runSettlementAnalysis}
                      disabled={settlementBusy}
                      className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 px-4 py-2 text-xs font-bold text-white shadow-sm transition-colors disabled:opacity-60"
                    >
                      {settlementBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                      {settlementBusy ? "Running..." : "Run AI Analysis"}
                    </button>
                  )}
                </div>
                {settlementRun && (
                  <div className="p-6">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
                      <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Settlement Amount</div>
                        <div className="text-xl font-extrabold text-emerald-600">
                          {formatCurrency(data?.settlement?.recommendedSettlement ?? settlementAnalysis?.settlementAmount)}
                        </div>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Final Settlement (Adjuster)</div>
                        <div className="text-xl font-extrabold text-slate-900">
                          {data?.settlement?.finalSettlement != null
                            ? formatCurrency(Number(data.settlement.finalSettlement))
                            : "—"}
                        </div>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Deductible Applied</div>
                        <div className="text-xl font-extrabold text-slate-900">
                          {formatCurrency(data?.settlement?.deductible ?? settlementAnalysis?.deductible)}
                        </div>
                      </div>
                    </div>

                    {settlementAnalysis && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
                        <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3.5">
                          <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Remaining Coverage Limit</div>
                          <div className="mt-1 text-sm font-extrabold text-slate-900">
                            {formatCurrency(data?.settlement?.remainingCoverageLimit ?? settlementAnalysis.remainingCoverageLimit)}
                          </div>
                        </div>
                        <div className="rounded-xl border border-blue-200 bg-blue-50/40 px-4 py-3.5">
                          <div className="text-[10px] font-bold uppercase tracking-wide text-blue-700">STP Score</div>
                          <div className="mt-1 text-sm font-extrabold text-blue-800">
                            {settlementAnalysis.stpScore ?? "—"}
                          </div>
                        </div>
                      </div>
                    )}

                    {settlementAnalysis?.recommendedAction && (
                      <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 px-4 py-3.5 mb-3">
                        <div className="text-[10px] font-bold uppercase tracking-wide text-emerald-700 mb-1">Recommended Action</div>
                        <p className="text-sm text-slate-700">{settlementAnalysis.recommendedAction}</p>
                      </div>
                    )}
                    {settlementAnalysis?.notes && (
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3.5 mb-5">
                        <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500 mb-1">Notes</div>
                        <p className="text-sm text-slate-700">{settlementAnalysis.notes}</p>
                      </div>
                    )}

                    {settlementAnalysis?.settlementAmount == null && data?.settlement?.recommendedSettlement == null && (
                      <p className="text-xs text-amber-700/90 bg-amber-50/60 border border-amber-200 rounded-lg px-4 py-3 mb-5">
                        No settlement recommendation is available for this claim in the database yet.
                      </p>
                    )}

                    <div className="flex flex-wrap gap-3">
                      <button
                        onClick={() =>
                          saveSettlementAmount(
                            Number(settlementAnalysis?.settlementAmount ?? data?.settlement?.recommendedSettlement ?? 0),
                            "System recommended settlement approved and saved."
                          )
                        }
                        disabled={
                          settlementSaving ||
                          (settlementAnalysis?.settlementAmount == null && data?.settlement?.recommendedSettlement == null)
                        }
                        className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 px-6 py-2.5 text-sm font-bold text-white shadow-sm transition-colors disabled:opacity-60"
                      >
                        {settlementSaving && !settlementRejected ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <CheckCircle2 className="h-4 w-4" />
                        )}
                        Approve
                      </button>
                      <button
                        onClick={() => setSettlementRejected(true)}
                        disabled={settlementSaving}
                        className="inline-flex items-center gap-2 rounded-full border border-red-300 bg-white hover:bg-red-50 px-6 py-2.5 text-sm font-bold text-red-600 transition-colors disabled:opacity-60"
                      >
                        <XCircle className="h-4 w-4" /> Reject
                      </button>
                    </div>
                    {settlementRejected && (
                      <div className="mt-5 border-t border-slate-100 pt-5">
                        <label className="block text-[11px] font-bold text-slate-600 mb-1.5">
                          Enter Settlement Amount ($)
                        </label>
                        <div className="flex flex-wrap items-center gap-3">
                          <input
                            type="number"
                            min="0"
                            value={settlementInput}
                            onChange={(e) => setSettlementInput(e.target.value)}
                            placeholder="Enter amount"
                            className="w-56 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                          />
                          <button
                            onClick={() => {
                              const amt = Number(settlementInput);
                              if (!settlementInput.trim() || !Number.isFinite(amt) || amt < 0) {
                                toast({
                                  title: "Invalid Amount",
                                  description: "Please enter a valid settlement amount.",
                                  variant: "destructive",
                                });
                                return;
                              }
                              saveSettlementAmount(amt, `Settlement amount ${formatCurrency(amt)} saved.`);
                            }}
                            disabled={settlementSaving}
                            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 px-5 py-2.5 text-sm font-bold text-white shadow-md transition-colors disabled:opacity-60"
                          >
                            {settlementSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                            {settlementSaving ? "Saving..." : "Save Settlement Amount"}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Financial Leakage */}
              <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 flex items-center justify-between gap-3 border-b border-slate-100 bg-rose-50/60">
                  <h2 className="flex items-center gap-3 font-extrabold text-slate-900">
                    <AlertTriangle className="h-5 w-5 text-rose-600" /> Financial Leakage
                  </h2>
                  {!leakageRun && (
                    <button
                      onClick={runLeakageAnalysis}
                      disabled={leakageBusy}
                      className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 px-4 py-2 text-xs font-bold text-white shadow-sm transition-colors disabled:opacity-60"
                    >
                      {leakageBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                      {leakageBusy ? "Running..." : "Run AI Analysis"}
                    </button>
                  )}
                </div>
                {leakageRun && (
                  <div className="p-6">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Leakage Risk</div>
                        <div className="text-xl font-extrabold">
                          {(leakageAnalysis?.leakageRisk || data?.leakage?.leakageRisk) ? (
                            <span
                              className={`inline-flex rounded-full px-3.5 py-1 text-[11px] font-bold text-white ${
                                (leakageAnalysis?.leakageRisk || data?.leakage?.leakageRisk) === "Critical"
                                  ? "bg-red-700"
                                  : (leakageAnalysis?.leakageRisk || data?.leakage?.leakageRisk) === "High"
                                    ? "bg-red-600"
                                    : (leakageAnalysis?.leakageRisk || data?.leakage?.leakageRisk) === "Medium"
                                      ? "bg-amber-500"
                                      : "bg-emerald-500"
                              }`}
                            >
                              {leakageAnalysis?.leakageRisk || data?.leakage?.leakageRisk}
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </div>
                      </div>
                      <div className="rounded-xl border border-rose-200 bg-rose-50/40 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Leakage Score</div>
                        <div className="text-xl font-extrabold text-rose-600">
                          {(leakageAnalysis?.leakageScore ?? data?.leakage?.leakageScore) ?? "—"}/100
                        </div>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Overall Variance</div>
                        <div className="text-xl font-extrabold text-slate-900">
                          {(leakageAnalysis?.overallVariancePercent ?? data?.leakage?.overallVariancePercent) != null
                            ? `${leakageAnalysis?.overallVariancePercent ?? data?.leakage?.overallVariancePercent}%`
                            : "—"}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3.5">
                        <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Total Estimated Cost</div>
                        <div className="mt-1 text-sm font-extrabold text-slate-900">
                          {formatCurrency(leakageAnalysis?.totalEstimatedCost ?? data?.leakage?.totalEstimatedCost)}
                        </div>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3.5">
                        <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Total Actual Cost</div>
                        <div className="mt-1 text-sm font-extrabold text-slate-900">
                          {formatCurrency(leakageAnalysis?.totalActualCost ?? data?.leakage?.totalActualCost)}
                        </div>
                      </div>
                    </div>

                    {(leakageAnalysis?.riskFlags ?? data?.leakage?.riskFlags ?? []).length > 0 && (
                      <div className="rounded-xl border border-rose-100 bg-rose-50/40 px-4 py-3.5 mb-3">
                        <div className="text-[10px] font-bold uppercase tracking-wide text-rose-700 mb-2">Risk Flags</div>
                        <ul className="space-y-1.5">
                          {(leakageAnalysis?.riskFlags ?? data?.leakage?.riskFlags ?? []).map((f: RiskFlag, i: number) => (
                            <li key={i} className="text-sm text-slate-700">
                              <span className="font-bold">{f.item_type || f.vendor_id || "Item"}:</span> {f.issue}
                              {f.severity && <span className="ml-1.5 text-xs text-rose-600 font-bold">({f.severity})</span>}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {(leakageAnalysis?.recommendation || data?.leakage?.recommendation) && (
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3.5 mb-5">
                        <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500 mb-1">Recommendation</div>
                        <p className="text-sm text-slate-700">
                          {leakageAnalysis?.recommendation || data?.leakage?.recommendation}
                        </p>
                      </div>
                    )}

                    {leakageAnalysis == null && data?.leakage == null && (
                      <p className="text-xs text-amber-700/90 bg-amber-50/60 border border-amber-200 rounded-lg px-4 py-3 mb-5">
                        No financial leakage data is available for this claim in the database yet.
                      </p>
                    )}

                    <div className="border-t border-slate-100 pt-5">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-3">
                        <div>
                          <label className="block text-[11px] font-bold text-slate-600 mb-1.5">Risk Level Override</label>
                          <Select value={leakageRiskOverride} onValueChange={setLeakageRiskOverride}>
                            <SelectTrigger className="w-full rounded-lg border-slate-200 text-sm font-semibold h-9">
                              <SelectValue placeholder="Select risk level" />
                            </SelectTrigger>
                            <SelectContent>
                              {LEAKAGE_RISK_LEVELS.map((level) => (
                                <SelectItem key={level} value={level}>{level}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <label className="block text-[11px] font-bold text-slate-600 mb-1.5">Adjuster Notes</label>
                      <textarea
                        value={leakageNotes}
                        onChange={(e) => setLeakageNotes(e.target.value)}
                        rows={3}
                        placeholder="Add notes about this leakage review..."
                        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500 mb-4"
                      />
                      <button
                        onClick={saveLeakageDecision}
                        disabled={leakageSaving}
                        className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 px-5 py-2.5 text-sm font-bold text-white shadow-md transition-colors disabled:opacity-60"
                      >
                        {leakageSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                        {leakageSaving ? "Saving..." : "Save Leakage Decision"}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Payment Eligibility — populated by the same Financial Leakage
                  "Run AI Analysis" click above (see runLeakageAnalysis). Read-only:
                  eligibility is one input to the adjuster's final payment decision
                  below, not something to save on its own. */}
              {leakageRun && eligibilityAnalysis && (
                <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
                  <div className="px-6 py-4 flex items-center gap-3 border-b border-slate-100 bg-indigo-50/60">
                    <ShieldCheck className="h-5 w-5 text-indigo-600" />
                    <h2 className="font-extrabold text-slate-900">Payment Eligibility</h2>
                  </div>
                  <div className="p-6">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Eligible for Auto-Adjudication</div>
                        <span
                          className={`inline-flex rounded-full px-3.5 py-1 text-[11px] font-bold text-white ${
                            eligibilityAnalysis.eligibleForAutoAdjudication ? "bg-emerald-500" : "bg-amber-500"
                          }`}
                        >
                          {eligibilityAnalysis.eligibleForAutoAdjudication ? "Eligible" : "Not Eligible"}
                        </span>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Decision</div>
                        <div className="text-sm font-extrabold text-slate-900">{eligibilityAnalysis.decision || "—"}</div>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">STP Category</div>
                        <div className="text-sm font-extrabold text-slate-900">{eligibilityAnalysis.stpCategory || "—"}</div>
                      </div>
                    </div>
                    {eligibilityAnalysis.gates && (
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3.5 mb-5">
                        <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500 mb-2">Gates Evaluated</div>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(eligibilityAnalysis.gates).map(([name, gate]) => (
                            <span
                              key={name}
                              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-bold border ${
                                gate.pass
                                  ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                                  : "bg-red-50 border-red-200 text-red-600"
                              }`}
                            >
                              {gate.pass ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                              {name.replace(/_/g, " ")}
                              {gate.skip ? " (skipped)" : ""}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {eligibilityAnalysis.recommendation && (
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3.5">
                        <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500 mb-1">Recommendation</div>
                        <p className="text-sm text-slate-700">{eligibilityAnalysis.recommendation}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Payment Readiness & Final Decision — the ONLY place in this
                  page that can actually disburse money. Approve/Reject calls
                  the orchestrator's deterministic /payment-decision endpoint
                  (no LLM in the loop) via decidePayment(). */}
              {leakageRun && paymentPreview && (
                <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
                  <div className="px-6 py-4 flex items-center gap-3 border-b border-slate-100 bg-emerald-50/60">
                    <DollarSign className="h-5 w-5 text-emerald-600" />
                    <h2 className="font-extrabold text-slate-900">Payment Readiness &amp; Final Decision</h2>
                  </div>
                  <div className="p-6">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Approved for Payment</div>
                        <span
                          className={`inline-flex rounded-full px-3.5 py-1 text-[11px] font-bold text-white ${
                            paymentPreview.approved ? "bg-emerald-500" : "bg-red-500"
                          }`}
                        >
                          {paymentPreview.approved ? "Approved" : "Not Approved"}
                        </span>
                      </div>
                      <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 px-4 py-4">
                        <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Available Amount</div>
                        <div className="text-xl font-extrabold text-emerald-600">
                          {formatCurrency(paymentPreview.availableAmount)}
                        </div>
                        {paymentPreview.amountSource && (
                          <div className="text-[10px] text-slate-400 mt-0.5">{paymentPreview.amountSource}</div>
                        )}
                      </div>
                    </div>
                    {!paymentPreview.approved && paymentPreview.reason && (
                      <p className="text-xs text-amber-700/90 bg-amber-50/60 border border-amber-200 rounded-lg px-4 py-3 mb-5">
                        {paymentPreview.reason}
                      </p>
                    )}

                    {paymentDecisionResult === "" ? (
                      <div className="flex flex-wrap gap-3">
                        <button
                          onClick={() => decidePayment("Approved")}
                          disabled={paymentDeciding}
                          className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 px-6 py-2.5 text-sm font-bold text-white shadow-sm transition-colors disabled:opacity-60"
                        >
                          {paymentDeciding ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                          {paymentDeciding ? "Processing..." : "Approve Payment & Disburse"}
                        </button>
                        <button
                          onClick={() => decidePayment("Rejected")}
                          disabled={paymentDeciding}
                          className="inline-flex items-center gap-2 rounded-full border border-red-300 bg-white hover:bg-red-50 px-6 py-2.5 text-sm font-bold text-red-600 transition-colors disabled:opacity-60"
                        >
                          <XCircle className="h-4 w-4" /> Reject Payment
                        </button>
                      </div>
                    ) : (
                      <div
                        className={`inline-flex items-center gap-2 rounded-full px-5 py-2 text-sm font-bold ${
                          paymentDecisionResult === "approved"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : "bg-red-50 text-red-600 border border-red-200"
                        }`}
                      >
                        {paymentDecisionResult === "approved" ? (
                          <>
                            <CheckCircle2 className="h-4 w-4" /> Payment Decision Recorded — Approved
                          </>
                        ) : (
                          <>
                            <XCircle className="h-4 w-4" /> Payment Decision Recorded — Rejected
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Claim Decision */}
              <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
                <div className="bg-indigo-50/80 px-6 py-4 flex items-center gap-3 border-b border-indigo-100">
                  <Wand2 className="h-4.5 w-4.5 text-indigo-600" />
                  <h2 className="font-extrabold text-slate-900">Claim Decision</h2>
                  {isSiu && (
                    <span className="rounded-full bg-red-500 px-3 py-1 text-[10px] font-bold text-white">SIU Escalated</span>
                  )}
                </div>
                <div className="p-6">
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 px-4 py-4">
                      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 mb-2.5">
                        <Shield className="h-3.5 w-3.5 text-emerald-600" /> Coverage Status
                      </div>
                      <span className="inline-flex rounded-full bg-emerald-500 px-3.5 py-1 text-[11px] font-bold text-white">
                        {data?.decision?.coverageStatus || "Confirmed"}
                      </span>
                    </div>
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 px-4 py-4">
                      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 mb-2.5">
                        <Shield className="h-3.5 w-3.5 text-emerald-600" /> Fraud Indicator
                      </div>
                      <span className="inline-flex rounded-full bg-emerald-600 px-3.5 py-1 text-[11px] font-bold text-white">
                        {data?.decision?.fraudIndicator || "Low"}
                      </span>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-white px-4 py-4">
                      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 mb-2.5">
                        <Scale className="h-3.5 w-3.5 text-slate-600" /> STP Classification
                      </div>
                      <span className="inline-flex rounded-full bg-slate-800 px-3.5 py-1 text-[11px] font-bold text-white">
                        {data?.decision?.stpClassification || "Manual"}
                      </span>
                    </div>
                    <div className="rounded-xl border border-indigo-200 bg-indigo-50/40 px-4 py-4">
                      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 mb-2">
                        <DollarSign className="h-3.5 w-3.5 text-indigo-600" /> Est. Settlement
                      </div>
                      <span className="text-xl font-extrabold text-blue-600">
                        {formatCurrency(data?.decision?.estSettlement)}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-3 mb-6">
                    <button
                      onClick={() =>
                        runOrchestrator("Approve Claim", async () => {
                          const r = await decideClaimGate(selectedClaimId, "Approved", {
                            gateType: "damage_assessment_review",
                          });
                          return r.decided > 0
                            ? `Approved ${r.gates.join(", ")} for ${selectedClaimId}.`
                            : "No pending approval gate for this claim.";
                        })
                      }
                      disabled={busyAction !== null}
                      className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 px-6 py-2.5 text-sm font-bold text-white shadow-sm transition-colors disabled:opacity-60"
                    >
                      <CheckCircle2 className="h-4 w-4" /> Approve Claim
                    </button>
                    <button
                      onClick={() =>
                        runOrchestrator("Reject Claim", async () => {
                          const r = await decideClaimGate(selectedClaimId, "Rejected", {
                            gateType: "damage_assessment_review",
                          });
                          return r.decided > 0
                            ? `Rejected ${r.gates.join(", ")} for ${selectedClaimId}.`
                            : "No pending approval gate for this claim.";
                        })
                      }
                      disabled={busyAction !== null}
                      className="inline-flex items-center gap-2 rounded-full border border-red-300 bg-white hover:bg-red-50 px-6 py-2.5 text-sm font-bold text-red-600 transition-colors disabled:opacity-60"
                    >
                      <XCircle className="h-4 w-4" /> Reject Claim
                    </button>
                    <button
                      onClick={() =>
                        runOrchestrator("Forward to SIU", async () => {
                          const r = await decideClaimGate(selectedClaimId, "Rejected", {
                            gateType: "damage_assessment_review",
                            notes: "Escalated to SIU by adjuster",
                          });
                          return r.decided > 0
                            ? `Escalated ${r.gates.join(", ")} to SIU for ${selectedClaimId}.`
                            : "No pending approval gate to escalate for this claim.";
                        })
                      }
                      disabled={busyAction !== null}
                      className="inline-flex items-center gap-2 rounded-full border border-yellow-400 bg-white hover:bg-yellow-50 px-6 py-2.5 text-sm font-bold text-red-500 transition-colors disabled:opacity-60"
                    >
                      <Send className="h-4 w-4 text-yellow-500" /> Forward to SIU
                    </button>
                  </div>

                  <div className="border-t border-slate-100 pt-4">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-700 mb-3">
                      <FileText className="h-3.5 w-3.5" /> Decision Audit Trail
                    </div>
                    {data?.decision?.recommendedAction ? (
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <span className="inline-flex rounded-full border border-slate-300 px-3 py-1 text-[10px] font-bold text-slate-700">
                            {data.decision.recommendedAction}
                          </span>
                          <span className="text-xs text-slate-500">{data?.claim?.status}</span>
                        </div>
                        <span className="text-xs text-slate-400">{data?.claim?.customerName}</span>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400">No decisions recorded yet</p>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Claim Summary sidebar */}
        {showSummary && (
          <div className="space-y-4">
            <div className="rounded-xl bg-white border border-slate-200 shadow-sm p-5">
              <h3 className="flex items-center gap-2 font-extrabold text-slate-900 mb-4">
                <Shield className="h-4.5 w-4.5 text-indigo-500" /> Claim Summary
              </h3>
              <div className="space-y-3">
                <div className="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3">
                  <div className="text-[11px] font-semibold text-slate-500 mb-1">Claim Number</div>
                  <div className="font-extrabold text-slate-900 break-words">{data?.claim?.claimNumber || "—"}</div>
                </div>
                <div className="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3">
                  <div className="text-[11px] font-semibold text-slate-500 mb-1">Loss Date</div>
                  <div className="font-extrabold text-slate-900 flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5 text-slate-400" /> {data?.claim?.lossDate || "—"}
                  </div>
                </div>
                <div className="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3">
                  <div className="text-[11px] font-semibold text-slate-500 mb-1">Coverage Limit</div>
                  <div className="font-extrabold text-emerald-600">{formatCurrency(data?.claim?.coverageLimit)}</div>
                </div>
                <div className="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3">
                  <div className="text-[11px] font-semibold text-slate-500 mb-1">Deductible</div>
                  <div className="font-extrabold text-slate-900">{formatCurrency(data?.claim?.deductible)}</div>
                </div>
                <div className="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3">
                  <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Status</div>
                  <span className="inline-flex rounded-full bg-violet-500 px-3 py-1 text-[10px] font-bold text-white">
                    {data?.claim?.status || "—"}
                  </span>
                </div>
              </div>
              <div className="mt-5 pt-4 border-t border-slate-100">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-700 mb-2">
                  <MessageSquare className="h-3.5 w-3.5" /> Recent Interactions
                </div>
                <p className="text-xs text-slate-400">No recent interactions</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
