import { useState } from "react";
import {
  Shield,
  Search,
  Filter,
  ChevronRight,
  ChevronDown,
  ArrowLeft,
  User,
  AlertTriangle,
  Clock,
  ListChecks,
  Scale,
  Sparkles,
  CheckCircle2,
  MessageSquare,
  Phone,
  Globe,
  FileUp,
  Info,
} from "lucide-react";

interface SiuCase {
  siuId: string;
  claimId: string;
  fraud: number;
  policyholder: string;
  investigator: string;
  status: string;
  lossType: string;
  referral: string;
}

const cases: SiuCase[] = [
  { siuId: "SIU-1780909527098", claimId: "CLM-2024-5632", fraud: 25, policyholder: "Hexa Tester", investigator: "SIU Investigator", status: "Completed", lossType: "water damage", referral: "Adjuster" },
  { siuId: "SIU-1778599574366", claimId: "CLM-MOT-MP2RLHR0", fraud: 10, policyholder: "John Davis", investigator: "SIU Investigator", status: "Completed", lossType: "water damage", referral: "Adjuster" },
  { siuId: "SIU-1775745035645", claimId: "CLM-2026-MNRKN7EBYGAY", fraud: 25, policyholder: "John Davis", investigator: "SIU Investigator", status: "Completed", lossType: "wind/hail", referral: "Adjuster" },
  { siuId: "SIU-1775739211915", claimId: "CLM-2026-MNRH04Y65WBR", fraud: 10, policyholder: "John Davis", investigator: "SIU Investigator", status: "Completed", lossType: "water damage", referral: "Adjuster" },
  { siuId: "SIU-1774948898299", claimId: "CLM-2026-MNEE6L1ZBDLJ", fraud: 10, policyholder: "John Davis", investigator: "SIU Investigator", status: "Completed", lossType: "water damage", referral: "Adjuster" },
  { siuId: "SIU-1774936555296", claimId: "CLM-2026-MN22JMXEUK6L", fraud: 10, policyholder: "John Davis", investigator: "SIU Investigator", status: "Completed", lossType: "water damage", referral: "Adjuster" },
  { siuId: "SIU-1774862101733", claimId: "CLM-2026-MND1PZKX4RTQ", fraud: 25, policyholder: "John Davis", investigator: "SIU Investigator", status: "Completed", lossType: "wind/hail", referral: "Adjuster" },
  { siuId: "SIU-1774858713442", claimId: "CLM-2026-MND0ZLQW83HJ", fraud: 10, policyholder: "Hexa Tester", investigator: "SIU Investigator", status: "Completed", lossType: "Theft", referral: "Adjuster" },
];

const timelineStructure = ["Case Created", "SIU Review Started", "Evidence Review", "Interviews", "External Verification", "Decision"];

const timelineEvents = [
  {
    title: "Case Forwarded to SIU",
    datetime: "Jun 8, 2026, 11:00 AM",
    detail: { eventType: "Case Created", date: "2026-06-08", status: "Completed", notes: "Completed successfully" },
  },
  { title: "SIU Review Initiated", datetime: null, detail: null },
  {
    title: "Evidence Review Completed",
    datetime: "Jun 8, 2026, 11:00 AM",
    detail: { eventType: "Evidence Review", date: "2026-06-08", status: "Completed", notes: "All documents validated" },
  },
  { title: "Interview Scheduled", datetime: null, detail: null },
  { title: "External Verification Pending", datetime: null, detail: null },
  {
    title: "Final Decision Pending",
    datetime: "Jun 8, 2026, 11:00 AM",
    detail: { eventType: "Decision", date: "2026-06-08", status: "Completed", notes: "Case cleared — no fraud detected" },
  },
];

const activities = [
  { title: "Case Initiation", items: ["Forwarded by Adjuster / AI", "SIU Case ID generated"] },
  { title: "SIU Review Started", items: ["Investigator assigned", "Initial fraud signals reviewed"] },
  { title: "Evidence Review", items: ["Documents analyzed", "Image / damage validation", "Vendor inputs reviewed"] },
  { title: "Interview Stage", items: ["Interview scheduled (customer/vendor/witness)", "Interview completed", "Notes captured"] },
  { title: "External Verification", items: ["Police report check", "Third-party validation", "External database checks"] },
];

function CaseDetail({ c, onBack }: { c: SiuCase; onBack: () => void }) {
  const [openEvent, setOpenEvent] = useState<number | null>(0);
  const [notes, setNotes] = useState("");

  return (
    <div className="animate-in fade-in duration-300 pb-16 space-y-5">
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-4 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Cases
        </button>
        <span className="inline-flex rounded-full bg-emerald-600 px-3 py-1 text-[11px] font-bold text-white">
          Case Status: {c.status}
        </span>
      </div>

      {/* Case Header */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 flex items-center justify-between bg-gradient-to-r from-slate-950 via-red-950 to-red-800">
          <span className="flex items-center gap-2.5">
            <Shield className="h-4 w-4 text-white" />
            <h2 className="text-white font-extrabold text-sm">Case Header</h2>
          </span>
          <ChevronDown className="h-4 w-4 text-white/70" />
        </div>
        <div className="p-5 grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Claim ID", value: c.claimId },
            { label: "SIU Case ID", value: c.siuId },
            { label: "Policyholder", value: c.policyholder },
            { label: "Loss Type", value: c.lossType },
            { label: "Claim Amount", value: "—" },
            { label: "Fraud Risk Score", value: String(c.fraud), green: true },
            { label: "Referral Source", value: c.referral },
            { label: "Assigned Investigator", value: c.investigator },
          ].map((f) => (
            <div key={f.label} className="rounded-lg border border-slate-200 bg-slate-50/50 px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{f.label}</div>
              <div className={`mt-1 text-sm font-extrabold ${f.green ? "text-emerald-600" : "text-slate-900"}`}>{f.value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-5 items-start">
        <div className="space-y-5">
          {/* Fraud Risk Summary */}
          <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 flex items-center justify-between bg-gradient-to-r from-red-600 to-rose-600">
              <span className="flex items-center gap-2.5">
                <AlertTriangle className="h-4 w-4 text-white" />
                <h2 className="text-white font-extrabold text-sm">Fraud Risk Summary</h2>
              </span>
              <span className="flex items-center gap-2">
                <span className="rounded-full bg-emerald-500 px-2.5 py-0.5 text-[10px] font-bold text-white">Low Risk</span>
                <ChevronDown className="h-4 w-4 text-white/70" />
              </span>
            </div>
            <div className="p-6 flex flex-col md:flex-row items-center gap-8">
              <div className="flex flex-col items-center">
                <div className="relative h-28 w-44">
                  <svg viewBox="0 0 100 55" className="w-full h-full">
                    <path d="M 8 50 A 42 42 0 0 1 92 50" fill="none" stroke="#e2e8f0" strokeWidth="8" strokeLinecap="round" />
                    <path d="M 8 50 A 42 42 0 0 1 30 13" fill="none" stroke="#10b981" strokeWidth="8" strokeLinecap="round" />
                    <line
                      x1="50" y1="50" x2="24" y2="22"
                      stroke="#334155" strokeWidth="2.5" strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-x-0 bottom-0 text-center">
                    <span className="text-2xl font-extrabold text-emerald-600">{c.fraud}</span>
                    <span className="text-xs font-bold text-slate-400"> / 100</span>
                  </div>
                </div>
                <span className="mt-2 rounded-full bg-emerald-500 px-3 py-0.5 text-[10px] font-bold text-white">Low Risk</span>
              </div>
              <div className="flex-1 w-full">
                <div className="flex items-center gap-2 text-xs font-extrabold text-slate-800">
                  <Sparkles className="h-3.5 w-3.5 text-rose-500" /> Key Fraud Indicators
                </div>
                <div className="mt-3 rounded-lg border border-rose-100 bg-rose-50/60 px-4 py-3 flex items-center gap-3">
                  <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-rose-500">
                    <AlertTriangle className="h-3 w-3 text-white" />
                  </span>
                  <div>
                    <div className="text-xs font-extrabold text-slate-900">Staged Loss</div>
                    <div className="text-[11px] text-slate-500 font-medium">Low</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* SIU Investigation Timeline */}
          <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 flex items-center justify-between bg-gradient-to-r from-violet-600 to-indigo-600">
              <span className="flex items-center gap-2.5">
                <Clock className="h-4 w-4 text-white" />
                <h2 className="text-white font-extrabold text-sm">SIU Investigation Timeline</h2>
              </span>
              <span className="flex items-center gap-2">
                <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-[10px] font-bold text-white">3 events</span>
                <ChevronDown className="h-4 w-4 text-white/70" />
              </span>
            </div>
            <div className="p-5 space-y-5">
              <div className="rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2 text-white text-xs font-extrabold flex items-center gap-2">
                <Sparkles className="h-3.5 w-3.5" /> Timeline Structure
              </div>
              <div className="flex items-start justify-between px-2">
                {timelineStructure.map((s, i) => (
                  <div key={s} className="flex-1 flex flex-col items-center relative">
                    {i < timelineStructure.length - 1 && (
                      <div className="absolute top-3.5 left-1/2 w-full h-[2px] bg-violet-300" />
                    )}
                    <span className="relative z-10 inline-flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500 ring-4 ring-emerald-100">
                      <CheckCircle2 className="h-4 w-4 text-white" />
                    </span>
                    <span className="mt-2 text-[9px] font-bold text-slate-600 text-center leading-tight">{s}</span>
                  </div>
                ))}
              </div>

              <div className="rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2 text-white text-xs font-extrabold flex items-center gap-2">
                <ListChecks className="h-3.5 w-3.5" /> Timeline View
              </div>
              <div className="space-y-1">
                {timelineEvents.map((e, i) => (
                  <div key={e.title}>
                    <button
                      onClick={() => e.detail && setOpenEvent(openEvent === i ? null : i)}
                      className={`w-full flex items-center justify-between px-2 py-2 rounded-lg text-left ${
                        e.detail ? "hover:bg-violet-50/60 cursor-pointer" : "cursor-default"
                      }`}
                    >
                      <span className="flex items-center gap-3">
                        <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                        <span className="text-xs font-extrabold text-slate-800">{e.title}</span>
                      </span>
                      {e.datetime && (
                        <span className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-400">
                          {e.datetime} <Info className="h-3 w-3" />
                        </span>
                      )}
                    </button>
                    {e.detail && openEvent === i && (
                      <div className="ml-6 mt-1 mb-2 rounded-lg border border-slate-200 bg-slate-50/70 p-4 grid grid-cols-2 gap-x-8 gap-y-3">
                        <div>
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Event Type</div>
                          <div className="text-xs font-bold text-slate-800 mt-0.5">{e.detail.eventType}</div>
                        </div>
                        <div>
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Date</div>
                          <div className="text-xs font-bold text-slate-800 mt-0.5">{e.detail.date}</div>
                        </div>
                        <div>
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Status</div>
                          <div className="text-xs font-bold text-slate-800 mt-0.5">{e.detail.status}</div>
                        </div>
                        <div>
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Notes</div>
                          <div className="text-xs font-bold text-slate-800 mt-0.5">{e.detail.notes}</div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Activities */}
          <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 flex items-center justify-between bg-gradient-to-r from-emerald-600 to-green-600">
              <span className="flex items-center gap-2.5">
                <ListChecks className="h-4 w-4 text-white" />
                <h2 className="text-white font-extrabold text-sm">Activities</h2>
              </span>
              <span className="flex items-center gap-2">
                <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-[10px] font-bold text-white">1 logged</span>
                <ChevronDown className="h-4 w-4 text-white/70" />
              </span>
            </div>
            <div className="p-5 space-y-4">
              {activities.map((a) => (
                <div key={a.title} className="rounded-xl border border-emerald-200 bg-emerald-50/40 px-5 py-4">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2.5">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      <span className="text-xs font-extrabold text-slate-900">{a.title}</span>
                    </span>
                    <span className="rounded-full bg-emerald-500 px-2.5 py-0.5 text-[10px] font-bold text-white">Done</span>
                  </div>
                  <div className="mt-2.5 space-y-1.5 pl-6">
                    {a.items.map((it) => (
                      <div key={it} className="flex items-center gap-2 text-[11px] font-semibold text-slate-500">
                        <span className="h-1.5 w-1.5 rounded-full border border-emerald-400" /> {it}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-5">
          {/* Estimated Completion */}
          <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 flex items-center justify-between bg-gradient-to-r from-orange-500 to-rose-500">
              <span className="flex items-center gap-2.5">
                <Clock className="h-4 w-4 text-white" />
                <h2 className="text-white font-extrabold text-sm">Estimated Completion</h2>
              </span>
              <ChevronDown className="h-4 w-4 text-white/70" />
            </div>
            <div className="p-4 space-y-3">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 px-4 py-4 text-center">
                <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-600">Investigation Completed</div>
                <div className="mt-1 text-xl font-extrabold text-emerald-700">Completed in 1 day</div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/60 px-4 py-3">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Days Passed</div>
                <div className="mt-1 text-xs font-extrabold text-emerald-700">1 day — Completed</div>
                <div className="mt-2 h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div className="h-full w-full rounded-full bg-gradient-to-r from-emerald-500 to-green-400" />
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/60 px-4 py-3">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Current Stage</div>
                <div className="mt-1.5 flex items-center gap-2">
                  <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-violet-600">
                    <Sparkles className="h-3 w-3 text-white" />
                  </span>
                  <span className="text-xs font-extrabold text-slate-900">{c.status} — Cleared</span>
                </div>
                <div className="mt-2 flex items-center justify-between text-[10px] font-bold text-slate-400">
                  <span>Stage Progress</span>
                  <span className="text-slate-700">100%</span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div className="h-full w-full rounded-full bg-gradient-to-r from-emerald-500 to-green-400" />
                </div>
              </div>
            </div>
          </div>

          {/* Investigation Actions */}
          <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 flex items-center justify-between bg-gradient-to-r from-emerald-600 to-teal-600">
              <span className="flex items-center gap-2.5">
                <Shield className="h-4 w-4 text-white" />
                <h2 className="text-white font-extrabold text-sm">Investigation Actions</h2>
              </span>
              <ChevronDown className="h-4 w-4 text-white/70" />
            </div>
            <div className="p-4 space-y-3">
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 text-center text-[11px] font-bold text-slate-500">
                This case has been completed. Actions are disabled.
              </div>
              <button disabled className="w-full flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-orange-300 to-amber-300 px-4 py-2.5 text-xs font-bold text-white opacity-80 cursor-not-allowed">
                <FileUp className="h-3.5 w-3.5" /> Request Additional Proof
              </button>
              <button disabled className="w-full flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-300 to-purple-300 px-4 py-2.5 text-xs font-bold text-white opacity-80 cursor-not-allowed">
                <Phone className="h-3.5 w-3.5" /> Schedule Interview
              </button>
              <button disabled className="w-full flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-sky-300 to-blue-300 px-4 py-2.5 text-xs font-bold text-white opacity-80 cursor-not-allowed">
                <Globe className="h-3.5 w-3.5" /> Trigger External Verification
              </button>
              <div className="rounded-md bg-emerald-600 px-3 py-1.5 flex items-center gap-2">
                <MessageSquare className="h-3.5 w-3.5 text-white" />
                <span className="text-[10px] font-bold uppercase tracking-wider text-white">Investigation Notes</span>
              </div>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add investigation notes..."
                className="w-full rounded-lg border border-slate-200 bg-slate-50/60 p-3 text-xs font-medium text-slate-700 h-20 resize-none focus:outline-none focus:ring-2 focus:ring-emerald-300"
              />
              <button disabled className="w-full rounded-full bg-slate-400 px-4 py-2 text-xs font-bold text-white cursor-not-allowed">
                Save Notes
              </button>
            </div>
          </div>

          {/* Fraud Decision */}
          <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 flex items-center justify-between bg-gradient-to-r from-slate-700 to-slate-600">
              <span className="flex items-center gap-2.5">
                <Scale className="h-4 w-4 text-white" />
                <h2 className="text-white font-extrabold text-sm">Fraud Decision</h2>
              </span>
              <ChevronDown className="h-4 w-4 text-white/70" />
            </div>
            <div className="p-4">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 px-4 py-5 text-center">
                <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-600">Decision Recorded</div>
                <div className="mt-1 text-2xl font-extrabold text-emerald-700">Cleared</div>
                <span className="mt-2 inline-flex rounded-full bg-emerald-500 px-3 py-0.5 text-[10px] font-bold text-white">
                  Confidence: 75%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SiuWorkbench() {
  const [selected, setSelected] = useState<SiuCase | null>(null);
  const [search, setSearch] = useState("");

  if (selected) {
    return <CaseDetail c={selected} onBack={() => setSelected(null)} />;
  }

  const filtered = cases.filter(
    (c) =>
      c.siuId.toLowerCase().includes(search.toLowerCase()) ||
      c.claimId.toLowerCase().includes(search.toLowerCase()) ||
      c.investigator.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-8 py-6 shadow-md flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">SIU Investigation Workbench</h1>
          <p className="mt-1 text-sm text-indigo-200/80 font-medium">Investigate flagged claims with AI-powered fraud detection tools</p>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-3.5 py-1.5 text-[11px] font-bold text-white">
            <Shield className="h-3.5 w-3.5" /> Open Cases (21)
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-3.5 py-1.5 text-[11px] font-bold text-white">
            <AlertTriangle className="h-3.5 w-3.5" /> Escalated (1)
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-3.5 py-1.5 text-[11px] font-bold text-white">
            <ListChecks className="h-3.5 w-3.5" /> Total Cases (22)
          </span>
        </div>
      </div>

      {/* Investigation Queue */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-5 bg-gradient-to-r from-slate-950 via-red-950 to-red-800">
          <div className="flex items-center gap-2.5">
            <Search className="h-4 w-4 text-white" />
            <h2 className="text-white font-extrabold text-base">Investigation Queue</h2>
          </div>
          <p className="mt-0.5 text-xs text-red-100/70 font-medium">Select a case to open the detailed investigation panel</p>
        </div>
        <div className="px-5 py-4 flex items-center gap-4 border-b border-slate-100">
          <span className="flex items-center gap-1.5 text-xs font-extrabold text-slate-700 shrink-0">
            <Filter className="h-3.5 w-3.5" /> Search &amp; Filter
          </span>
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search claim #, SIU case ID, or investigator..."
              className="w-full rounded-full border border-slate-200 bg-slate-50/60 pl-9 pr-4 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>
          <span className="text-[11px] font-semibold text-slate-500 shrink-0">
            Showing <span className="font-extrabold text-slate-800">{filtered.length}</span> of <span className="font-extrabold text-slate-800">21</span> open cases
          </span>
        </div>
        <div className="p-4 space-y-3">
          {filtered.map((c) => (
            <button
              key={c.siuId}
              onClick={() => setSelected(c)}
              className="w-full flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3.5 hover:border-blue-300 hover:shadow-md transition-all text-left"
            >
              <div className="flex items-center gap-3.5">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-rose-500 to-pink-600 shadow-sm">
                  <Shield className="h-5 w-5 text-white" />
                </span>
                <div>
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="text-sm font-extrabold text-slate-900">{c.siuId}</span>
                    <span className="text-slate-300">|</span>
                    <span className="text-xs font-bold text-slate-500">{c.claimId}</span>
                    <span className="inline-flex rounded-full bg-emerald-500 px-2 py-0.5 text-[9px] font-bold text-white">
                      Fraud: {c.fraud}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[11px] font-semibold text-slate-400">
                    <User className="h-3 w-3" /> {c.policyholder}
                    <span className="text-slate-300">|</span> —
                    <span className="text-slate-300">|</span> Investigator: <span className="text-slate-600 font-bold">{c.investigator}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2.5">
                <span className="inline-flex rounded-full bg-emerald-700 px-3 py-1 text-[10px] font-bold text-white">{c.status}</span>
                <ChevronRight className="h-4 w-4 text-slate-300" />
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
