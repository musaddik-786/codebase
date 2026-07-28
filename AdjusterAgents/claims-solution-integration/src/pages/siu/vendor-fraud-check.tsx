import { useState } from "react";
import {
  Shield,
  Search,
  AlertCircle,
  TrendingUp,
  Flag,
  Network,
  BarChart3,
  AlertTriangle,
  FileText,
  Building2,
  ChevronRight,
  Sparkles,
  Eye,
  CheckCircle2,
  Clock,
} from "lucide-react";

interface Vendor {
  name: string;
  specialty: string;
  score: number;
  claims: number;
  lastAssessed: string;
  drivers: string[];
  aiAnalysis: string;
}

const vendors: Vendor[] = [
  {
    name: "Elite Fire Restoration",
    specialty: "Fire/Water Restoration",
    score: 88,
    claims: 22,
    lastAssessed: "4/2/2026",
    drivers: ["Board-up charges 3x market rate", "Content manipulation claims 45%", "Adjuster #7 exclusive relationship"],
    aiAnalysis:
      '"Critical risk: Exclusive adjuster relationship and inflated emergency services pricing. Immediate review recommended."',
  },
  {
    name: "QuickFix Auto Body",
    specialty: "Auto Repair",
    score: 82,
    claims: 31,
    lastAssessed: "4/2/2026",
    drivers: ["OEM vs aftermarket part switching", "Supplement rate 62% above peers", "Rental duration anomalies"],
    aiAnalysis: '"High risk: Systematic parts substitution pattern with inflated supplements. Detailed invoice audit advised."',
  },
  {
    name: "Bob's Towing Service",
    specialty: "Towing",
    score: 78,
    claims: 18,
    lastAssessed: "4/2/2026",
    drivers: ["Mileage inflation on tow invoices", "After-hours surcharge abuse", "Storage fee stacking"],
    aiAnalysis: '"Elevated risk: Recurrent mileage and storage overbilling. Cross-check GPS logs against invoices."',
  },
  {
    name: "ClearView Adjusting Services",
    specialty: "Public Adjuster",
    score: 75,
    claims: 27,
    lastAssessed: "4/2/2026",
    drivers: ["Consistent attorney referral pattern", "Claim value uplift 38% post-engagement", "Late-stage representation entries"],
    aiAnalysis: '"Elevated risk: Referral network alignment with legal partners inflating settlements. Monitor closely."',
  },
  {
    name: "Premier Collision Center",
    specialty: "Collision Repair",
    score: 72,
    claims: 24,
    lastAssessed: "4/2/2026",
    drivers: ["Labor hours 2.1x industry average", "Repeated supplemental estimates", "Threshold-clustered invoices"],
    aiAnalysis: '"Elevated risk: Labor inflation and just-below-threshold billing clusters detected."',
  },
];

const redFlags = [
  {
    id: 1,
    title: "OEM vs Aftermarket Switch",
    desc: "OEM parts billed but aftermarket installed based on part number verification",
    date: "4/2/2026",
    alertType: "billing anomaly",
    related: 3,
    logic: "Parts authenticity validation",
    severity: "Medium",
  },
  {
    id: 2,
    title: "Midnight Claim Submissions",
    desc: "78% of claims submitted between 12-4 AM - atypical user behavior",
    date: "4/2/2026",
    alertType: "timing irregularity",
    related: 5,
    logic: "Submission timestamp analysis",
    severity: "High",
  },
  {
    id: 3,
    title: "Rental Duration Anomaly",
    desc: "Rental car charges extend 12 days beyond repair completion",
    date: "4/2/2026",
    alertType: "pattern repetition",
    related: 4,
    logic: "Repair-to-rental timeline matching",
    severity: "Medium",
  },
  {
    id: 4,
    title: "Duplicate Damage Photos",
    desc: "Same damage photos submitted across 3 separate claims",
    date: "4/2/2026",
    alertType: "image reuse",
    related: 3,
    logic: "Image hash comparison",
    severity: "High",
  },
  {
    id: 5,
    title: "Supplement Rate Spike",
    desc: "Supplement requests on 84% of claims vs 22% peer average",
    date: "4/2/2026",
    alertType: "billing anomaly",
    related: 6,
    logic: "Peer benchmark deviation",
    severity: "Medium",
  },
];

const networkSignals = [
  {
    title: "Weather Event Surge",
    severity: "Medium",
    entity: "Hail Storm 2024-03-15",
    entityType: "event",
    occurrences: 45,
    note: "Claim surge 2-3 weeks post weather event",
  },
  {
    title: "Adjuster Association",
    severity: "High",
    entity: "Adjuster Mike Thompson",
    entityType: "adjuster",
    occurrences: 34,
    note: "89% of claims from this vendor are handled by the same adjuster",
  },
  {
    title: "Loss Type Repeat",
    severity: "Medium",
    entity: "Rear-end collision",
    entityType: "loss_type",
    occurrences: 28,
    note: "78% of claims are rear-end collisions at low speed",
  },
  {
    title: "Referral Network",
    severity: "High",
    entity: "Law Firm: Johnson & Associates",
    entityType: "legal",
    occurrences: 22,
    note: "Consistent attorney referral pattern detected",
  },
];

const invoiceRows = [
  { claim: "CLM-22984", holder: "Robert Williams", loss: "property", amt: "$9,304.12", ratio: "3.63:1", ratioHot: true, flags: ["Supp", "2 flags"] },
  { claim: "CLM-11567", holder: "David Thompson", loss: "water", amt: "$3,984.94", ratio: "2.87:1", ratioHot: false, flags: [] },
  { claim: "CLM-33421", holder: "Michelle Davis", loss: "property", amt: "$6,462.08", ratio: "3.60:1", ratioHot: true, flags: [] },
  { claim: "CLM-44532", holder: "Christopher Lee", loss: "property", amt: "$7,271.41", ratio: "2.27:1", ratioHot: false, flags: ["2 flags"] },
  { claim: "CLM-55643", holder: "Amanda Wilson", loss: "fire", amt: "$5,529.38", ratio: "1.89:1", ratioHot: false, flags: ["Supp", "Threshold"] },
  { claim: "CLM-66754", holder: "Brian Johnson", loss: "property", amt: "$7,246.6", ratio: "3.24:1", ratioHot: true, flags: [] },
  { claim: "CLM-77865", holder: "Stephanie Brown", loss: "water", amt: "$9,211.52", ratio: "3.20:1", ratioHot: true, flags: ["2 flags"] },
  { claim: "CLM-88976", holder: "Kevin Garcia", loss: "property", amt: "$5,431.25", ratio: "3.34:1", ratioHot: true, flags: [] },
];

type Tab = "risk" | "flags" | "network" | "invoice";

function severityBadge(sev: string) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-bold text-white ${
        sev === "High" ? "bg-red-600" : "bg-amber-500"
      }`}
    >
      {sev}
    </span>
  );
}

export default function VendorFraudCheck() {
  const [tab, setTab] = useState<Tab>("risk");
  const [selectedVendor, setSelectedVendor] = useState<Vendor | null>(null);
  const [reviewed, setReviewed] = useState<number[]>([]);
  const [escalated, setEscalated] = useState<number[]>([]);

  const escalatedCases = 8 + escalated.length;

  const tabBtn = (t: Tab, icon: React.ReactNode, label: string, badge?: number) => (
    <button
      onClick={() => setTab(t)}
      className={`inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-[11px] font-bold transition-colors ${
        tab === t
          ? t === "flags"
            ? "bg-gradient-to-r from-rose-600 to-fuchsia-600 text-white"
            : "bg-gradient-to-r from-fuchsia-600 to-violet-600 text-white"
          : "border border-white/15 bg-white/5 text-slate-400 hover:text-slate-200"
      }`}
    >
      {icon} {label}
      {badge !== undefined && (
        <span className="inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[9px] font-extrabold text-white">
          {badge}
        </span>
      )}
    </button>
  );

  return (
    <div className="animate-in fade-in duration-500 pb-16 -m-6 min-h-screen bg-gradient-to-br from-[#170b2b] via-[#1d0f38] to-[#12081f] p-6">
      {/* Banner */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="mt-1 inline-flex h-10 w-10 items-center justify-center rounded-xl border border-violet-500/40 bg-violet-500/10">
            <Shield className="h-5 w-5 text-violet-400" />
          </span>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">Vendor Fraud Intelligence Workspace</h1>
            <p className="mt-1 text-sm text-violet-200/70 font-medium">SIU Analytics Dashboard - Detect, Analyze, Investigate</p>
          </div>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
          <input
            placeholder="Search vendors, alerts..."
            className="rounded-full border border-white/10 bg-white/5 pl-9 pr-4 py-2 text-xs font-medium text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500/40 w-64"
          />
        </div>
      </div>

      {/* KPI tiles */}
      <div className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-red-500/30 bg-gradient-to-br from-red-950/80 to-red-900/40 px-5 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[11px] font-bold text-red-300">Critical Alerts</div>
              <div className="mt-1 text-3xl font-extrabold text-white">4</div>
            </div>
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-red-500/40">
              <AlertCircle className="h-4.5 w-4.5 text-red-400" />
            </span>
          </div>
        </div>
        <div className="rounded-xl border border-orange-500/30 bg-gradient-to-br from-orange-950/80 to-amber-900/30 px-5 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[11px] font-bold text-orange-300">High-Risk Vendors</div>
              <div className="mt-1 text-3xl font-extrabold text-white">5</div>
            </div>
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-orange-500/40">
              <TrendingUp className="h-4.5 w-4.5 text-orange-400" />
            </span>
          </div>
        </div>
        <div className="rounded-xl border border-fuchsia-500/30 bg-gradient-to-br from-fuchsia-950/70 to-purple-900/40 px-5 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[11px] font-bold text-fuchsia-300">Escalated Cases</div>
              <div className="mt-1 text-3xl font-extrabold text-white">{escalatedCases}</div>
            </div>
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-fuchsia-500/40">
              <Flag className="h-4.5 w-4.5 text-fuchsia-400" />
            </span>
          </div>
        </div>
        <div className="rounded-xl border border-blue-500/30 bg-gradient-to-br from-blue-950/70 to-indigo-900/40 px-5 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[11px] font-bold text-blue-300">Network Signals</div>
              <div className="mt-1 text-3xl font-extrabold text-white">25</div>
            </div>
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-blue-500/40">
              <Network className="h-4.5 w-4.5 text-blue-400" />
            </span>
          </div>
        </div>
      </div>

      {/* Sub tabs */}
      <div className="mt-5 flex items-center gap-2.5 flex-wrap">
        {tabBtn("risk", <BarChart3 className="h-3.5 w-3.5" />, "Vendor Risk Scores")}
        {tabBtn("flags", <AlertTriangle className="h-3.5 w-3.5" />, "Red Flag Alerts", 10)}
        {tabBtn("network", <Network className="h-3.5 w-3.5" />, "Network Signals")}
        {tabBtn("invoice", <FileText className="h-3.5 w-3.5" />, "Invoice Patterns")}
      </div>

      {/* Vendor Risk Scores */}
      {tab === "risk" && (
        <div className="mt-5 grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
            <h2 className="text-white font-extrabold text-base">Vendor Risk Assessment</h2>
            <p className="text-xs text-slate-400 font-medium mt-0.5">Click a vendor to view detailed analysis</p>
            <div className="mt-4 space-y-3">
              {vendors.map((v) => (
                <button
                  key={v.name}
                  onClick={() => setSelectedVendor(v)}
                  className={`w-full rounded-xl border px-4 py-3.5 text-left transition-all ${
                    selectedVendor?.name === v.name
                      ? "border-violet-400 bg-violet-500/15 ring-1 ring-violet-400/50"
                      : "border-white/10 bg-white/[0.04] hover:border-violet-400/40"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2.5">
                      <Building2 className="h-4 w-4 text-slate-400" />
                      <span className="text-sm font-extrabold text-white">{v.name}</span>
                    </span>
                    <span className="inline-flex rounded-full bg-gradient-to-r from-rose-500 to-pink-500 px-2.5 py-0.5 text-[10px] font-bold text-white">
                      High
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-[11px] font-semibold">
                    <span className="text-slate-400">{v.specialty}</span>
                    <span className="text-slate-400">
                      Risk Score: <span className="text-red-400 font-extrabold">{v.score}</span>
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 rounded-full bg-white/10 overflow-hidden">
                    <div className="h-full rounded-full bg-blue-500" style={{ width: `${v.score}%` }} />
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
            {!selectedVendor ? (
              <>
                <h2 className="text-white font-extrabold text-base">Select a Vendor</h2>
                <div className="mt-20 flex flex-col items-center justify-center text-center">
                  <Building2 className="h-12 w-12 text-slate-600" />
                  <p className="mt-4 text-sm font-medium text-slate-500">Select a vendor to view risk details</p>
                </div>
              </>
            ) : (
              <div className="animate-in fade-in duration-300">
                <h2 className="text-white font-extrabold text-base">{selectedVendor.name}</h2>
                <p className="text-xs text-slate-400 font-medium mt-0.5">
                  {selectedVendor.specialty} • {selectedVendor.claims} associated claims
                </p>
                <div className="mt-5 flex items-center gap-6">
                  <div className="relative h-24 w-24">
                    <svg viewBox="0 0 36 36" className="h-24 w-24 -rotate-90">
                      <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="3" />
                      <circle
                        cx="18" cy="18" r="15.9" fill="none" stroke="#ef4444" strokeWidth="3" strokeLinecap="round"
                        strokeDasharray={`${selectedVendor.score} ${100 - selectedVendor.score}`}
                      />
                    </svg>
                    <span className="absolute inset-0 flex items-center justify-center text-2xl font-extrabold text-white">
                      {selectedVendor.score}
                    </span>
                  </div>
                  <div>
                    <span className="inline-flex rounded-lg bg-gradient-to-r from-red-600 to-rose-600 px-3.5 py-1.5 text-xs font-extrabold text-white">
                      High Risk
                    </span>
                    <div className="mt-2 text-[11px] font-semibold text-slate-400">Last assessed: {selectedVendor.lastAssessed}</div>
                  </div>
                </div>
                <div className="mt-6 border-t border-white/10 pt-4">
                  <div className="flex items-center gap-2 text-xs font-extrabold text-white">
                    <span className="h-2 w-2 rounded-full bg-fuchsia-400" /> Top Risk Drivers
                  </div>
                  <div className="mt-3 space-y-2">
                    {selectedVendor.drivers.map((d) => (
                      <div key={d} className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3.5 py-2.5">
                        <ChevronRight className="h-3.5 w-3.5 text-amber-400" />
                        <span className="text-xs font-semibold text-slate-200">{d}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mt-5 border-t border-white/10 pt-4">
                  <div className="flex items-center gap-2 text-xs font-extrabold text-white">
                    <Sparkles className="h-3.5 w-3.5 text-violet-400" /> AI Analysis
                  </div>
                  <div className="mt-3 rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3 text-xs italic font-medium text-slate-300 leading-relaxed">
                    {selectedVendor.aiAnalysis}
                  </div>
                </div>
                <div className="mt-5 grid grid-cols-2 gap-3">
                  <button className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/5 px-4 py-2.5 text-xs font-bold text-slate-200 hover:bg-white/10">
                    <Eye className="h-3.5 w-3.5" /> View Claims
                  </button>
                  <button className="inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 px-4 py-2.5 text-xs font-bold text-white hover:from-violet-500 hover:to-fuchsia-500">
                    <Flag className="h-3.5 w-3.5" /> Open Investigation
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Red Flag Alerts */}
      {tab === "flags" && (
        <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.03] p-5">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            <h2 className="text-white font-extrabold text-base">Active Red Flag Alerts</h2>
          </div>
          <p className="text-xs text-slate-400 font-medium mt-0.5">Fraud indicators requiring investigation</p>
          <div className="mt-4 space-y-4">
            {redFlags.map((f) => {
              const isReviewed = reviewed.includes(f.id);
              const isEscalated = escalated.includes(f.id);
              const acted = isReviewed || isEscalated;
              return (
                <div key={f.id} className="rounded-xl border border-white/10 bg-white/[0.04] p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="text-sm font-extrabold text-white">{f.title}</div>
                    <div className="flex items-center gap-2 shrink-0">
                      {severityBadge(f.severity)}
                      {isEscalated && (
                        <span className="inline-flex rounded-full bg-fuchsia-600 px-2.5 py-0.5 text-[10px] font-bold text-white">
                          Escalated
                        </span>
                      )}
                      {isReviewed && (
                        <span className="inline-flex rounded-full bg-slate-600 px-2.5 py-0.5 text-[10px] font-bold text-white">
                          Reviewed
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="mt-1.5 text-xs font-medium text-slate-300">{f.desc}</p>
                  <div className="mt-2 flex items-center gap-4 text-[11px] font-semibold text-slate-500">
                    <span className="inline-flex items-center gap-1.5">
                      <Clock className="h-3 w-3" /> {f.date}
                    </span>
                    <span>Alert Type: {f.alertType}</span>
                    <span>{f.related} related claims</span>
                  </div>
                  <div className="mt-3 rounded-lg bg-black/30 px-4 py-2.5 text-[11px] font-semibold">
                    <span className="text-slate-300">Detection Logic: </span>
                    <span className="text-slate-500">{f.logic}</span>
                  </div>
                  {acted ? (
                    isReviewed && (
                      <div className="mt-3 text-[11px] font-semibold text-slate-500">Reviewed by: SIU Analyst</div>
                    )
                  ) : (
                    <div className="mt-3.5 flex items-center gap-3">
                      <button
                        onClick={() => setReviewed((r) => [...r, f.id])}
                        className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-4 py-1.5 text-[11px] font-bold text-slate-200 hover:bg-white/10"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" /> Mark Reviewed
                      </button>
                      <button
                        onClick={() => setEscalated((e) => [...e, f.id])}
                        className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-600 px-4 py-1.5 text-[11px] font-bold text-white hover:from-violet-500 hover:to-fuchsia-500"
                      >
                        <Flag className="h-3.5 w-3.5" /> Escalate
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Network Signals */}
      {tab === "network" && (
        <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.03] p-5">
          <div className="flex items-center gap-2">
            <Network className="h-4 w-4 text-blue-400" />
            <h2 className="text-white font-extrabold text-base">Network Relationship Signals</h2>
          </div>
          <p className="text-xs text-slate-400 font-medium mt-0.5">Hidden connections and relationship patterns</p>
          <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
            {networkSignals.map((s) => (
              <div key={s.title} className="rounded-xl border border-white/10 bg-white/[0.04] p-5">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-extrabold text-white">{s.title}</div>
                  {severityBadge(s.severity)}
                </div>
                <div className="mt-3 space-y-2 text-[11px] font-semibold">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Related Entity:</span>
                    <span className="text-slate-200 font-bold">{s.entity}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Entity Type:</span>
                    <span className="text-slate-300">{s.entityType}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Occurrences:</span>
                    <span className="text-white font-extrabold text-sm">{s.occurrences}</span>
                  </div>
                </div>
                <div className="mt-3 rounded-lg border border-white/10 bg-black/30 px-4 py-2.5 text-[11px] font-semibold text-slate-300">
                  {s.note}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Invoice Patterns */}
      {tab === "invoice" && (
        <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.03] p-5">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-amber-400" />
            <h2 className="text-white font-extrabold text-base">Invoice &amp; Billing Patterns</h2>
          </div>
          <p className="text-xs text-slate-400 font-medium mt-0.5">Claim associations and billing behavior analysis</p>
          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] font-bold text-slate-400 border-b border-white/10">
                <th className="px-4 py-2.5">Claim #</th>
                <th className="px-4 py-2.5">Policyholder</th>
                <th className="px-4 py-2.5">Loss Type</th>
                <th className="px-4 py-2.5 text-right">Invoice Amt</th>
                <th className="px-4 py-2.5 text-right">Labor/Material</th>
                <th className="px-4 py-2.5 text-right">Flags</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {invoiceRows.map((r) => (
                <tr key={r.claim} className="hover:bg-white/[0.03]">
                  <td className="px-4 py-3 text-xs font-extrabold text-white">{r.claim}</td>
                  <td className="px-4 py-3 text-xs font-semibold text-slate-300">{r.holder}</td>
                  <td className="px-4 py-3 text-xs font-medium text-slate-400">{r.loss}</td>
                  <td className="px-4 py-3 text-xs font-extrabold text-white text-right">{r.amt}</td>
                  <td className={`px-4 py-3 text-xs font-extrabold text-right ${r.ratioHot ? "text-red-400" : "text-slate-300"}`}>
                    {r.ratio}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="inline-flex items-center gap-1.5 justify-end">
                      {r.flags.map((fl) => (
                        <span
                          key={fl}
                          className={`inline-flex rounded-full px-2 py-0.5 text-[9px] font-bold text-white ${
                            fl === "Supp" ? "bg-amber-500" : fl === "Threshold" ? "bg-red-600" : "bg-fuchsia-600"
                          }`}
                        >
                          {fl}
                        </span>
                      ))}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
