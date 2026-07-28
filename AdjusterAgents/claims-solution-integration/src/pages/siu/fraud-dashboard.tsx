import { Clock, AlertTriangle, ClipboardList, UserCheck, FileText, CheckCircle2 } from "lucide-react";

const flaggedClaims = [
  {
    id: "CLM-2026-839274",
    desc: "Storm on June 1st, 2026 caused hail and wind damage to roof and gutters. ...",
    type: "wind/hail",
    address: "116 May St Altamont, UT 84001",
    severity: "High",
  },
  {
    id: "CLM-2026-492881",
    desc: "Pipe burst in kitchen caused sudden water damage to kitchen and nearby a...",
    type: "water damage",
    address: "116 May St Altamont, UT 84001",
    severity: "High",
  },
  {
    id: "CLM-2026-4832",
    desc: "Pipe burst in kitchen on 08-06-2026 at 15:45. Sudden water damage, high ...",
    type: "water damage",
    address: "116 May St Altamont, UT 84001",
    severity: "High",
  },
  {
    id: "FNOL-2026-7358",
    desc: "Theft/vandalism resulting in removal of roof shingles and gutters; not weat...",
    type: "Theft",
    address: "2850 S. Delaware St. San Mateo, CA 94403",
    severity: "High",
  },
];

const recentActivity = [
  { name: "John Davis", desc: "there was a pipe burst in kitchen area", status: "Loss Investigation" },
  { name: "FNTest_132 LNTest_132", desc: "Pipe under kitchen sink burst at 8am, flooding kitchen floor and two b...", status: "Loss Investigation" },
  { name: "FNTest_132 LNTest_132", desc: "Storm on June 1st, 2026 caused hail and wind damage to roof and gutters. 60...", status: "Approved" },
  { name: "FNTest_132 LNTest_132", desc: "Pipe burst in kitchen caused sudden water damage to kitchen and nea...", status: "Loss Investigation" },
  { name: "FNTest_132 LNTest_132", desc: "Pipe under kitchen sink burst, flooding kitchen floor and lower cabinets. Dam...", status: "Approved" },
];

export default function FraudDashboard() {
  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-8 py-7 shadow-md">
        <h1 className="text-3xl font-extrabold tracking-tight text-white">Fraud Investigation Center</h1>
        <p className="mt-1 text-sm text-indigo-200/80 font-medium">Investigate suspicious claims and anomalies</p>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-slate-900 to-slate-800">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Suspected Claims</span>
            <Clock className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">29</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-blue-800 to-indigo-900">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Anomalies Flagged</span>
            <AlertTriangle className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">16</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-orange-600 to-red-600">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Investigation Queue</span>
            <ClipboardList className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">18</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-emerald-600 to-green-700">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Resolved This Week</span>
            <UserCheck className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">4</div>
        </div>
      </div>

      {/* Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Flagged Claims */}
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 flex items-center justify-between bg-gradient-to-r from-violet-600 to-blue-600">
            <h2 className="text-white font-extrabold text-sm">Flagged Claims</h2>
            <button className="text-[11px] font-bold text-white/80 hover:text-white">View All →</button>
          </div>
          <div className="divide-y divide-slate-100">
            {flaggedClaims.map((c) => (
              <div key={c.id} className="relative px-5 py-4 bg-violet-50/30 hover:bg-violet-50/60 transition-colors">
                <span className="absolute inset-y-0 left-0 w-1 bg-violet-500" />
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-[11px] font-bold text-violet-600">{c.id}</div>
                    <div className="mt-0.5 text-sm font-bold text-slate-900">{c.desc}</div>
                    <div className="mt-1 text-[11px] text-slate-400 font-medium">
                      {c.type} <span className="mx-1">•</span> {c.address}
                    </div>
                  </div>
                  <span className="inline-flex rounded-full bg-emerald-600 px-2.5 py-0.5 text-[10px] font-bold text-white shrink-0">
                    {c.severity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 flex items-center justify-between bg-gradient-to-r from-teal-600 to-emerald-600">
            <h2 className="text-white font-extrabold text-sm">Recent Activity</h2>
            <button className="text-[11px] font-bold text-white/80 hover:text-white">View All →</button>
          </div>
          <div className="divide-y divide-slate-100">
            {recentActivity.map((a, i) => (
              <div key={i} className="px-5 py-4 flex items-center justify-between gap-3 hover:bg-slate-50 transition-colors">
                <div className="flex items-start gap-3">
                  <span
                    className={`mt-0.5 inline-flex h-7 w-7 items-center justify-center rounded-lg ${
                      a.status === "Approved" ? "bg-emerald-100" : "bg-blue-100"
                    }`}
                  >
                    {a.status === "Approved" ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <FileText className="h-4 w-4 text-blue-600" />
                    )}
                  </span>
                  <div>
                    <div className="text-sm font-bold text-slate-900">{a.name}</div>
                    <div className="text-[11px] text-slate-400 font-medium">{a.desc}</div>
                  </div>
                </div>
                <span
                  className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-bold text-white shrink-0 ${
                    a.status === "Approved" ? "bg-emerald-500" : "bg-blue-500"
                  }`}
                >
                  {a.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
