import { useMemo, useState } from "react";
import { ShieldAlert, AlertTriangle, ShieldCheck, Eye, Shield, Activity, DollarSign, TrendingUp, Link2, FileCheck2 } from "lucide-react";
import { riskFlags, costAnomalies, repeatedHighCost, relationshipPatterns, licenseValidation, billingPatterns } from "@/lib/vendor-data";

const riskBadge: Record<string, string> = {
  High: "bg-red-700 text-white",
  Medium: "bg-yellow-300 text-yellow-900",
  Low: "bg-emerald-100 text-emerald-700 border border-emerald-200",
};

const statusBadge: Record<string, string> = {
  Active: "bg-emerald-700 text-white",
  Inactive: "border border-slate-300 text-slate-400 bg-white",
  "Under Review": "bg-amber-500 text-white",
};

const fmtMoney = (n: number) => `$${new Intl.NumberFormat("en-US").format(n)}`;

export default function VendorRiskCompliance() {
  const [filter, setFilter] = useState<"All" | "High" | "Medium" | "Low">("All");

  const filtered = useMemo(
    () => (filter === "All" ? riskFlags : riskFlags.filter((r) => r.risk === filter)),
    [filter]
  );

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-8 py-7 shadow-md">
        <h1 className="text-3xl font-extrabold tracking-tight text-white">Vendor Risk &amp; Compliance</h1>
        <p className="mt-1 text-sm text-indigo-200/80 font-medium">Monitor vendor risk levels, compliance status, and suspicious billing patterns</p>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-red-700 to-rose-600">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">High Risk Vendors</span>
            <ShieldAlert className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">6</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-amber-500 to-orange-600">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Medium Risk</span>
            <AlertTriangle className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">7</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-emerald-600 to-green-700">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Low Risk</span>
            <ShieldCheck className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">7</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-blue-800 to-indigo-900">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Under Review</span>
            <Eye className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">1</div>
        </div>
      </div>

      {/* Risk flags table */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-violet-600 to-blue-600">
          <Shield className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Risk Flags Table</h2>
        </div>
        <div className="px-5 pt-4">
          <div className="inline-flex rounded-lg bg-slate-100 p-1 gap-1">
            {(["All", "High", "Medium", "Low"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded-md px-4 py-1.5 text-xs font-bold transition-colors ${
                  filter === f ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto mt-2">
          <table className="w-full text-left">
            <thead>
              <tr className="text-xs font-semibold text-slate-500 border-b border-slate-200">
                <th className="px-5 py-3">Vendor ID</th>
                <th className="px-5 py-3">Vendor Name</th>
                <th className="px-5 py-3">Specialty</th>
                <th className="px-5 py-3">Risk Flag</th>
                <th className="px-5 py-3">Reason</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((r) => (
                <tr key={r.vendorId} className="hover:bg-slate-50/60">
                  <td className="px-5 py-3.5 text-xs font-semibold text-slate-500 whitespace-nowrap">{r.vendorId}</td>
                  <td className="px-5 py-3.5 text-sm font-bold text-slate-900 whitespace-nowrap">{r.name}</td>
                  <td className="px-5 py-3.5 text-sm text-slate-600">{r.specialty}</td>
                  <td className="px-5 py-3.5">
                    <span className={`rounded-full px-3 py-1 text-[10px] font-bold ${riskBadge[r.risk]}`}>{r.risk}</span>
                  </td>
                  <td className="px-5 py-3.5 text-sm text-slate-600 max-w-[240px] truncate">{r.reason}</td>
                  <td className="px-5 py-3.5">
                    <span className={`rounded-full px-3 py-1 text-[10px] font-bold ${statusBadge[r.status]}`}>{r.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">
        {/* AI Signals / Compliance Insights */}
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-emerald-600 to-cyan-600">
            <Activity className="h-4 w-4 text-white" />
            <h2 className="text-white font-extrabold text-sm">AI Signals / Compliance Insights</h2>
          </div>
          <div className="p-5 space-y-6">
            <div>
              <div className="flex items-center gap-2 text-sm font-extrabold text-red-600 mb-3">
                <DollarSign className="h-4 w-4" /> Cost Anomaly Detection
              </div>
              <div className="space-y-2">
                {costAnomalies.map((c) => (
                  <div key={c.vendor} className="rounded-lg border border-red-100 bg-red-50/40 px-4 py-2.5 text-sm">
                    <span className="font-bold text-slate-800">{c.vendor}</span>{" "}
                    <span className="text-red-500 font-semibold">Cost exceeds estimate by {c.pct.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 text-sm font-extrabold text-amber-600 mb-3">
                <TrendingUp className="h-4 w-4" /> Repeated High-Cost Estimates
              </div>
              <div className="space-y-2">
                {repeatedHighCost.map((c, i) => (
                  <div key={`${c.vendor}-${i}`} className="rounded-lg border border-amber-100 bg-amber-50/40 px-4 py-2.5 text-sm">
                    <span className="font-bold text-slate-800">{c.vendor}</span>{" "}
                    <span className="text-amber-600 font-semibold">Avg estimate: {fmtMoney(c.estimate)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 text-sm font-extrabold text-blue-600 mb-3">
                <Link2 className="h-4 w-4" /> Vendor-Claim Relationship Patterns
              </div>
              <div className="space-y-2">
                {relationshipPatterns.map((c) => (
                  <div key={c.vendor} className="rounded-lg border border-blue-100 bg-blue-50/40 px-4 py-2.5 text-sm">
                    <span className="font-bold text-slate-800">{c.vendor}</span>{" "}
                    <span className="text-blue-600 font-semibold">VIS: {c.vis} — Requires monitoring</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 text-sm font-extrabold text-violet-600 mb-3">
                <FileCheck2 className="h-4 w-4" /> License Validation
              </div>
              <div className="space-y-2">
                {licenseValidation.map((c) => (
                  <div key={c.vendor} className="rounded-lg border border-violet-100 bg-violet-50/40 px-4 py-2.5 text-sm">
                    <span className="font-bold text-slate-800">{c.vendor}</span>{" "}
                    <span className="text-violet-600 font-semibold">Status: {c.status} — Needs license review</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Suspicious Billing Patterns */}
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-orange-500 to-red-600">
            <AlertTriangle className="h-4 w-4 text-white" />
            <h2 className="text-white font-extrabold text-sm">Suspicious Billing Patterns</h2>
          </div>
          <div className="p-5 space-y-3.5">
            {billingPatterns.map((b) => (
              <div
                key={b.vendor}
                className={`rounded-xl border px-4 py-3.5 ${b.suspicious ? "border-red-200 bg-red-50/50" : "border-slate-200 bg-white"}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold text-slate-900">{b.vendor}</span>
                  <span className={`text-xs font-extrabold ${b.variance >= 15 ? "text-red-600" : b.variance > 0 ? "text-amber-600" : "text-emerald-600"}`}>
                    {b.variance.toFixed(1)}% variance
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden mb-2">
                  <div
                    className={`h-full rounded-full ${b.variance >= 15 ? "bg-red-500" : b.variance > 0 ? "bg-amber-400" : "bg-emerald-500"}`}
                    style={{ width: `${Math.min(Math.abs(b.variance) * 4, 100)}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium">
                  <span>Avg Est: {fmtMoney(b.avgEst)}</span>
                  <span>Avg Actual: {fmtMoney(b.avgActual)}</span>
                </div>
                {b.suspicious && (
                  <span className="inline-flex items-center gap-1.5 mt-2.5 rounded-full border border-red-300 bg-red-100/70 text-red-600 px-3 py-1 text-[10px] font-bold">
                    <AlertTriangle className="h-3 w-3" /> Suspicious overcharging detected
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
