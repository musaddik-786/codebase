import { useState } from "react";
import type { ClaimJourney, ClaimInsights } from "@/lib/journey-data";
import {
  ArrowLeft,
  Check,
  Sparkles,
  Bell,
  TrendingUp,
  Upload,
  Mail,
  AlertTriangle,
  Download,
  Phone,
  Smile,
  Meh,
  Clock,
  Flag,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileWarning,
  Zap,
} from "lucide-react";

const MCP_BASE = (import.meta.env as Record<string, string | undefined>).VITE_MCP_URL ?? "http://localhost:7720";

interface ClaimJourneyWorkspaceProps {
  claim: ClaimJourney;
  insights: ClaimInsights | null;
  onBack: () => void;
}

// ── Missing-field label map ────────────────────────────────────────────────
const FIELD_LABELS: Record<string, string> = {
  description: "Claim Description",
  police_report: "Police Report",
  loss_date: "Date of Loss",
  loss_location: "Loss Location",
  incident_date: "Incident Date",
  contact_number: "Contact Number",
  address: "Address",
  loss_type: "Loss Type",
  estimated_cost: "Estimated Cost",
  property_damage: "Property Damage",
  cause_of_loss: "Cause of Loss",
  claimant_name: "Claimant Name",
  phone_number: "Phone Number",
  email: "Email",
  policy_number: "Policy Number",
};

const fieldLabel = (f: string) =>
  FIELD_LABELS[f] ?? f.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

// ── STP badge helpers ────────────────────────────────────────────────────────

function stpColor(category: string | null): string {
  switch (category) {
    case "Full STP":    return "bg-emerald-100 text-emerald-800 border-emerald-300";
    case "Fast Track":  return "bg-blue-100 text-blue-800 border-blue-300";
    case "Vendor STP":  return "bg-violet-100 text-violet-800 border-violet-300";
    case "Manual Review": return "bg-amber-100 text-amber-800 border-amber-300";
    default:            return "bg-gray-100 text-gray-600 border-gray-300";
  }
}

function coverageColor(verdict: string | null): { bg: string; icon: React.ReactNode } {
  switch (verdict) {
    case "Covered":
      return { bg: "bg-emerald-50 border-emerald-200", icon: <ShieldCheck className="h-5 w-5 text-emerald-600" /> };
    case "Partially Covered":
      return { bg: "bg-amber-50 border-amber-200", icon: <ShieldAlert className="h-5 w-5 text-amber-600" /> };
    case "Not Covered":
      return { bg: "bg-red-50 border-red-200", icon: <ShieldX className="h-5 w-5 text-red-600" /> };
    default:
      return { bg: "bg-gray-50 border-gray-200", icon: <ShieldCheck className="h-5 w-5 text-gray-400" /> };
  }
}

function readinessColor(score: number | null): string {
  if (score === null) return "bg-gray-200";
  if (score >= 80) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-red-500";
}

// ── Main component ────────────────────────────────────────────────────────────

export function ClaimJourneyWorkspace({ claim, insights, onBack }: ClaimJourneyWorkspaceProps) {
  const [feedbackKey, setFeedbackKey] = useState<string | null>(null);
  const [feedbackSaving, setFeedbackSaving] = useState(false);
  const [feedbackSaved, setFeedbackSaved] = useState(false);

  const [openStage, setOpenStage] = useState<number | null>(null);
  const journeyStages = claim.stages;
  const total = journeyStages.length;

  const [concernType, setConcernType] = useState("");
  const [concernSaving, setConcernSaving] = useState(false);
  const [concernSaved, setConcernSaved] = useState(false);

  const [contactStatus, setContactStatus] = useState<Record<string, "idle" | "saving" | "done">>({
    email: "idle", escalate: "idle",
  });

  const stageStatusLabel = (idx: number) => {
    if (idx < claim.stageIndex) return "Completed";
    if (idx === claim.stageIndex) return "In Progress";
    return "Upcoming";
  };

  // ── Feedback submit ────────────────────────────────────────────────────────

  const handleFeedback = async (key: string) => {
    setFeedbackKey(key);
    setFeedbackSaving(true);
    try {
      await fetch(`${MCP_BASE}/api/v1/feedback/api/feedback/write`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_number: claim.id,
          comment: key,
          stage_number: claim.stageIndex + 1,
          stage_name: journeyStages[claim.stageIndex],
        }),
      });
    } catch {
      // best-effort
    } finally {
      setFeedbackSaving(false);
      setFeedbackSaved(true);
    }
  };

  // ── Raise concern ──────────────────────────────────────────────────────────

  const handleConcern = async () => {
    if (!concernType || concernType === "Select concern type...") return;
    setConcernSaving(true);
    try {
      await fetch(
        `${MCP_BASE}/api/v1/communication/api/communication/log_inbound/${encodeURIComponent(claim.id)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message_text: `Policyholder concern: ${concernType}` }),
        }
      );
    } catch {
      // best-effort
    } finally {
      setConcernSaving(false);
      setConcernSaved(true);
    }
  };

  // ── Contact team actions ───────────────────────────────────────────────────

  const handleContact = async (action: "email" | "escalate") => {
    setContactStatus((prev) => ({ ...prev, [action]: "saving" }));
    const message =
      action === "email"
        ? "Policyholder requested contact with adjuster via email."
        : "Policyholder requested escalation of claim.";
    try {
      await fetch(
        `${MCP_BASE}/api/v1/communication/api/communication/log_inbound/${encodeURIComponent(claim.id)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message_text: message }),
        }
      );
    } catch {
      // best-effort
    } finally {
      setContactStatus((prev) => ({ ...prev, [action]: "done" }));
    }
  };

  // ── Download summary ───────────────────────────────────────────────────────

  const handleDownload = () => {
    const lines = [
      `CLAIM SUMMARY`,
      `=============`,
      `Claim Number    : ${claim.id}`,
      `Policy Number   : ${claim.policyNumber}`,
      `Policyholder    : ${claim.policyholder}`,
      `Loss Type       : ${claim.type}`,
      `Date of Loss    : ${claim.dateOfLoss}`,
      `Status          : ${claim.status}`,
      `Current Stage   : ${journeyStages[claim.stageIndex]} (Stage ${claim.stageIndex + 1} of ${total})`,
      `Progress        : ${claim.progress}%`,
      `Est. Completion : ${claim.estCompletion}`,
      ``,
      `WHAT'S HAPPENING`,
      `----------------`,
      claim.whatsHappeningNow,
      ``,
      `WHAT HAPPENS NEXT`,
      `-----------------`,
      claim.whatHappensNext,
    ];
    if (insights) {
      if (insights.stpCategory) {
        lines.push(``, `PROCESSING TRACK`, `----------------`, insights.stpCategory);
      }
      if (insights.coverageVerdict) {
        lines.push(``, `COVERAGE STATUS`, `---------------`, insights.coverageVerdict);
        if (insights.netPayable != null) {
          const payableLabel = insights.netPayable === 0 && insights.coverageVerdict === "Covered"
            ? "Below deductible"
            : insights.netPayable === 0 && insights.coverageVerdict?.startsWith("Covered - Pending")
            ? "Pending assessment"
            : `$${insights.netPayable.toLocaleString()}`;
          lines.push(`Net Payable: ${payableLabel}`);
        }
      }
      if (insights.completenessScore != null) {
        lines.push(``, `CLAIM READINESS`, `---------------`, `Completeness: ${insights.completenessScore}%`);
        if (insights.overallResult) lines.push(`Overall: ${insights.overallResult}`);
      }
    }
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${claim.id}-summary.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* ── Claim header bar ───────────────────────────────────────────────── */}
      <div className="rounded-2xl bg-gradient-to-r from-[#0f172a] to-[#1e1b4b] p-5 text-white shadow-lg">
        <div className="flex flex-wrap items-center gap-x-8 gap-y-4">
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-sm text-white/80 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Claims
          </button>

          <HeaderField label="CLAIM ID" value={claim.id} />
          <HeaderField label="POLICY NUMBER" value={claim.policyNumber} />
          <HeaderField label="POLICYHOLDER" value={claim.policyholder} />
          <HeaderField label="LOSS TYPE" value={claim.type} />
          <HeaderField label="DATE OF LOSS" value={claim.dateOfLoss} />
          {insights?.severity && (
            <HeaderField label="SEVERITY" value={insights.severity} />
          )}

          <div className="ml-auto flex flex-col items-end gap-2">
            <span className="rounded-full bg-gradient-to-r from-emerald-400 to-teal-400 px-3 py-1 text-xs font-bold text-emerald-950">
              Stage {claim.stageIndex + 1}: {journeyStages[claim.stageIndex]}
            </span>
            <span className="rounded-full bg-blue-500 px-3 py-1 text-xs font-semibold text-white">
              Status: {claim.status}
            </span>
            {insights?.stpCategory && (
              <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${stpColor(insights.stpCategory)}`}>
                <Zap className="inline h-3 w-3 mr-1" />
                {insights.stpCategory}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── Claim Intelligence row (Readiness + STP + Coverage) ─────────────── */}
      {insights && (insights.completenessScore !== null || insights.stpCategory || insights.coverageVerdict) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Readiness card */}
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-4">
            <div className="flex items-center gap-2 mb-3">
              <FileWarning className="h-4 w-4 text-indigo-500" />
              <span className="text-sm font-semibold text-gray-900">Claim Readiness</span>
              {insights.overallResult && (
                <span className={`ml-auto rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                  insights.overallResult === "Ready"
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : insights.overallResult === "Flagged for Review"
                    ? "bg-red-50 text-red-700 border-red-200"
                    : "bg-amber-50 text-amber-700 border-amber-200"
                }`}>
                  {insights.overallResult}
                </span>
              )}
            </div>
            {insights.completenessScore !== null ? (
              <>
                <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                  <span>Completeness</span>
                  <span className="font-bold text-gray-900">{insights.completenessScore}%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${readinessColor(insights.completenessScore)}`}
                    style={{ width: `${insights.completenessScore}%` }}
                  />
                </div>
                {insights.missingFields && insights.missingFields.length > 0 && (
                  <div className="mt-2 rounded-lg bg-amber-50 border border-amber-100 px-3 py-2">
                    <p className="text-[11px] font-semibold text-amber-700 mb-1">Missing fields:</p>
                    <p className="text-[11px] text-amber-600">{insights.missingFields.map(fieldLabel).join(", ")}</p>
                  </div>
                )}
                {insights.docsStatus === "Incomplete" && (
                  <div className="mt-2 rounded-lg bg-rose-50 border border-rose-100 px-3 py-2">
                    <p className="text-[11px] text-rose-600 font-medium">No documents uploaded yet</p>
                  </div>
                )}
              </>
            ) : (
              <p className="text-xs text-gray-400">Readiness not scored yet</p>
            )}
          </div>

          {/* Processing Track card */}
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-4">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="h-4 w-4 text-violet-500" />
              <span className="text-sm font-semibold text-gray-900">Processing Track</span>
            </div>
            {insights.stpCategory ? (
              <>
                <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-semibold ${stpColor(insights.stpCategory)}`}>
                  {insights.stpCategory}
                </span>
                <p className="mt-2 text-xs text-gray-500">
                  {insights.stpCategory === "Full STP" && "Fastest path — minimal manual review needed."}
                  {insights.stpCategory === "Fast Track" && "Expedited — light review before moving forward."}
                  {insights.stpCategory === "Vendor STP" && "A specialist will be engaged to assess your claim."}
                  {insights.stpCategory === "Manual Review" && "An adjuster will review your claim manually."}
                </p>
                {insights.complexity && (
                  <p className="mt-1 text-[11px] text-gray-400">Complexity: {insights.complexity}</p>
                )}
              </>
            ) : (
              <p className="text-xs text-gray-400">Segmentation not run yet</p>
            )}
          </div>

          {/* Coverage Status card */}
          {(() => {
            const { bg, icon } = coverageColor(insights.coverageVerdict);
            return (
              <div className={`rounded-xl border shadow-sm p-4 ${bg}`}>
                <div className="flex items-center gap-2 mb-3">
                  {icon}
                  <span className="text-sm font-semibold text-gray-900">Coverage Status</span>
                </div>
                {insights.coverageVerdict ? (
                  <>
                    <p className="text-sm font-bold text-gray-900">{insights.coverageVerdict}</p>
                    {insights.netPayable != null && (
                      <p className="mt-1 text-xs text-gray-600">
                        Est. payable:{" "}
                        <span className="font-semibold">
                          {insights.netPayable === 0 && insights.coverageVerdict === "Covered"
                            ? "Below deductible"
                            : insights.netPayable === 0 && insights.coverageVerdict?.startsWith("Covered - Pending")
                            ? "Pending assessment"
                            : `$${insights.netPayable.toLocaleString()}`}
                        </span>
                      </p>
                    )}
                    {insights.exclusionTriggered && insights.exclusionDetails && (
                      <div className="mt-2 rounded-lg bg-white/70 border border-red-100 px-2 py-1.5">
                        <p className="text-[11px] text-red-600">{insights.exclusionDetails}</p>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-xs text-gray-400">Coverage not verified yet</p>
                )}
              </div>
            );
          })()}
        </div>
      )}

      {/* ── Interactive journey stepper ─────────────────────────────────────── */}
      <div className="rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 border border-indigo-100 p-6">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-2 text-indigo-900 font-semibold">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            Interactive Claim Journey
          </div>
          <span className="flex items-center gap-1.5 rounded-full bg-[#1e1b4b] px-3 py-1.5 text-xs font-medium text-white">
            <Sparkles className="h-3 w-3" />
            Click any stage for details
          </span>
        </div>

        <div className="flex items-start justify-between gap-1">
          {journeyStages.map((stage, idx) => {
            const completed = idx < claim.stageIndex;
            const current = idx === claim.stageIndex;
            return (
              <button
                key={stage}
                onClick={() => setOpenStage(openStage === idx ? null : idx)}
                className="flex flex-1 flex-col items-center relative group"
              >
                {idx < total - 1 && (
                  <div
                    className={`absolute top-5 left-1/2 h-0.5 w-full ${
                      idx < claim.stageIndex ? "bg-green-500" : "bg-gray-300"
                    }`}
                  />
                )}
                <div
                  className={`relative z-10 flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all group-hover:scale-110 ${
                    openStage === idx ? "ring-4 ring-indigo-300" : ""
                  } ${
                    completed
                      ? "bg-green-500 border-green-500 text-white"
                      : current
                      ? "bg-white border-indigo-600 text-indigo-600 ring-4 ring-indigo-200"
                      : "bg-white border-gray-300 text-gray-300"
                  }`}
                >
                  {completed ? (
                    <Check className="h-5 w-5" />
                  ) : (
                    <span className="h-2.5 w-2.5 rounded-full bg-current" />
                  )}
                </div>
                <span
                  className={`mt-3 text-center text-[11px] leading-tight max-w-[80px] ${
                    current
                      ? "font-bold text-indigo-700"
                      : completed
                      ? "font-medium text-gray-700"
                      : "text-gray-400"
                  }`}
                >
                  {stage}
                </span>
              </button>
            );
          })}
        </div>

        {openStage !== null && (
          <div className="mt-6 rounded-xl bg-white border border-indigo-100 p-4 shadow-sm animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-indigo-950">
                Stage {openStage + 1}: {journeyStages[openStage]}
              </h4>
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  openStage < claim.stageIndex
                    ? "bg-green-100 text-green-700"
                    : openStage === claim.stageIndex
                    ? "bg-indigo-100 text-indigo-700"
                    : "bg-gray-100 text-gray-500"
                }`}
              >
                {stageStatusLabel(openStage)}
              </span>
            </div>
            <p className="text-sm text-gray-600">
              {openStage < claim.stageIndex
                ? "This step has been completed and verified by your claims team."
                : openStage === claim.stageIndex
                ? claim.whatsHappeningNow
                : "This step is part of the upcoming journey and has not started yet."}
            </p>
            {/* Show segmentation result inline when Segmentation & Triage stage is opened */}
            {journeyStages[openStage] === "Segmentation & Triage" && insights?.stpCategory && (
              <div className="mt-3 flex items-center gap-2 rounded-lg bg-violet-50 border border-violet-100 px-3 py-2">
                <Zap className="h-4 w-4 text-violet-600 flex-shrink-0" />
                <span className="text-xs text-violet-800 font-medium">
                  Routed to: <strong>{insights.stpCategory}</strong>
                  {insights.complexity ? ` · Complexity: ${insights.complexity}` : ""}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── What's happening / next ──────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl bg-indigo-50/60 border border-indigo-100 p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-white">
              <Sparkles className="h-4 w-4" />
            </div>
            <h3 className="font-semibold text-indigo-950">What's Happening Now?</h3>
          </div>
          <div className="rounded-xl bg-white p-4 text-sm text-gray-700 shadow-sm">
            {claim.whatsHappeningNow}
          </div>
          <p className="mt-3 flex items-center gap-1.5 text-xs text-gray-400">
            <Sparkles className="h-3 w-3" />
            AI-generated update • Last refreshed just now
          </p>
        </div>

        <div className="rounded-2xl bg-cyan-50/60 border border-cyan-100 p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-cyan-600 text-white">
              <TrendingUp className="h-4 w-4" />
            </div>
            <h3 className="font-semibold text-cyan-950">What Happens Next?</h3>
          </div>
          <div className="rounded-xl bg-white p-4 shadow-sm">
            <p className="text-sm font-semibold text-gray-900">
              {journeyStages[Math.min(claim.stageIndex + 1, total - 1)]}
            </p>
            <p className="mt-1 text-sm text-gray-600">{claim.whatHappensNext}</p>
            <span className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700 border border-amber-200">
              <Clock className="h-3 w-3" />
              {claim.nextStatusLabel}
            </span>
          </div>
        </div>
      </div>

      {/* ── Feedback + Concern ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Feedback — wired to FeedbackAgent (port 7706) */}
        <div className="rounded-2xl bg-white border-l-4 border-l-amber-400 border border-gray-200 p-6 shadow-sm">
          <h3 className="flex items-center gap-2 font-semibold text-gray-900 mb-4">
            <Flag className="h-4 w-4 text-amber-500" />
            How Was This Stage?
          </h3>
          <div className="flex flex-wrap gap-3">
            {[
              { key: "Clear", icon: Smile },
              { key: "Confusing", icon: Meh },
              { key: "Took Too Long", icon: Clock },
            ].map(({ key, icon: Icon }) => (
              <button
                key={key}
                onClick={() => !feedbackSaved && handleFeedback(key)}
                disabled={feedbackSaving || feedbackSaved}
                className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${
                  feedbackKey === key
                    ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {feedbackSaving && feedbackKey === key
                  ? <Loader2 className="h-4 w-4 animate-spin" />
                  : <Icon className="h-4 w-4" />}
                {key}
              </button>
            ))}
          </div>
          {feedbackSaved && (
            <p className="mt-3 flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Feedback saved — thank you!
            </p>
          )}
        </div>

        {/* Raise a Concern — wired to CommunicationAgent (port 7709) */}
        <div className="rounded-2xl bg-white border-l-4 border-l-rose-400 border border-gray-200 p-6 shadow-sm">
          <h3 className="flex items-center gap-2 font-semibold text-gray-900 mb-4">
            <Flag className="h-4 w-4 text-rose-500" />
            Raise a Concern
          </h3>
          {concernSaved ? (
            <div className="flex items-center gap-2 rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-3 text-sm text-emerald-700">
              <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
              Your concern has been logged. The claims team will follow up with you.
            </div>
          ) : (
            <>
              <p className="text-sm text-gray-500 mb-2">Select the type of concern:</p>
              <select
                value={concernType}
                onChange={(e) => setConcernType(e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none focus:border-rose-400 mb-3"
              >
                <option value="">Select concern type...</option>
                <option>Delay in processing</option>
                <option>Incorrect information</option>
                <option>Need to add documents</option>
                <option>Other</option>
              </select>
              <button
                onClick={handleConcern}
                disabled={!concernType || concernSaving}
                className="flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {concernSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <AlertCircle className="h-4 w-4" />}
                Submit Concern
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── Latest updates ───────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <div className="flex items-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-500 px-6 py-4 text-white">
          <Bell className="h-5 w-5" />
          <div>
            <h3 className="font-semibold">Latest Updates</h3>
            <p className="text-xs text-white/80">Recent actions on your claim</p>
          </div>
        </div>
        <div className="p-6">
          {claim.latestUpdate ? (
            <div className="flex items-start gap-4">
              <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold">
                1
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900">
                    {claim.latestUpdate.title}
                  </span>
                  <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[11px] font-medium text-violet-700">
                    {claim.latestUpdate.actor}
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-600">{claim.latestUpdate.detail}</p>
                <p className="mt-1 text-xs text-teal-600">{claim.latestUpdate.timestamp}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-500">No updates recorded on this claim yet.</p>
          )}
        </div>
      </div>

      {/* ── Timeline + Document share ─────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl bg-gradient-to-br from-[#1e1b4b] to-[#312e81] p-6 text-white shadow-lg">
          <div className="flex items-center gap-2 mb-5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10">
              <TrendingUp className="h-4 w-4" />
            </div>
            <h3 className="font-semibold">Estimated Timeline</h3>
          </div>
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-white/70">Progress</span>
            <span className="font-bold">{claim.progress}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-violet-400 to-fuchsia-400"
              style={{ width: `${claim.progress}%` }}
            />
          </div>
          <div className="mt-3 flex items-center justify-between text-xs">
            <span className="text-white/60">
              Stage {claim.stageIndex + 1} of {total}
            </span>
            <span className="flex items-center gap-1 text-amber-300">
              <Sparkles className="h-3 w-3" />
              Est. completion: {claim.estCompletion}
            </span>
          </div>
        </div>

        {/* Document Share — links to Document Hub (DocumentSubmissionAgent port 7705) */}
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-cyan-500 px-6 py-4 text-white">
            <Upload className="h-5 w-5" />
            <div>
              <h3 className="font-semibold">Document Share</h3>
              <p className="text-xs text-white/80">Upload and share supporting documents</p>
            </div>
          </div>
          <div className="divide-y divide-gray-100">
            {["Additional Damage Images/Videos", "Repair Estimates", "Proof of Ownership"].map(
              (doc) => (
                <div key={doc} className="flex items-center justify-between px-6 py-4">
                  <span className="text-sm text-gray-700">{doc}</span>
                  <a
                    href="/document-hub"
                    className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <Upload className="h-3.5 w-3.5" />
                    Upload
                  </a>
                </div>
              )
            )}
          </div>
          <div className="px-6 py-3 bg-blue-50/50 border-t border-blue-100">
            <p className="text-xs text-blue-700">
              Documents are classified by AI and linked to claim <strong>{claim.id}</strong>.
            </p>
          </div>
        </div>
      </div>

      {/* ── Contact team ──────────────────────────────────────────────────────── */}
      <div className="rounded-2xl bg-gradient-to-r from-teal-50 to-emerald-50 border border-teal-100 p-6">
        <h3 className="flex items-center gap-2 font-semibold text-teal-900 mb-4">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-teal-500 text-white">
            <Phone className="h-4 w-4" />
          </span>
          Need Help? Contact Your Team
        </h3>
        <div className="flex flex-wrap gap-3">
          {/* Email Adjuster — logs inbound via CommunicationAgent */}
          <button
            onClick={() => contactStatus.email === "idle" && handleContact("email")}
            disabled={contactStatus.email !== "idle"}
            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-70"
          >
            {contactStatus.email === "saving" ? (
              <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
            ) : contactStatus.email === "done" ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            ) : (
              <Mail className="h-4 w-4 text-blue-500" />
            )}
            {contactStatus.email === "done" ? "Request Sent" : "Email Adjuster"}
          </button>

          {/* Escalate — logs inbound via CommunicationAgent */}
          <button
            onClick={() => contactStatus.escalate === "idle" && handleContact("escalate")}
            disabled={contactStatus.escalate !== "idle"}
            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-70"
          >
            {contactStatus.escalate === "saving" ? (
              <Loader2 className="h-4 w-4 animate-spin text-amber-500" />
            ) : contactStatus.escalate === "done" ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-amber-500" />
            )}
            {contactStatus.escalate === "done" ? "Escalated" : "Escalate"}
          </button>

          {/* Download Claim Summary — generates from existing claim data */}
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <Download className="h-4 w-4 text-teal-500" />
            Download Claim Summary
          </button>
        </div>
      </div>
    </div>
  );
}

function HeaderField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] font-medium tracking-wider text-white/50">{label}</div>
      <div className="text-sm font-semibold text-white">{value}</div>
    </div>
  );
}
