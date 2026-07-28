import { useState } from "react";
import {
  FileText,
  DollarSign,
  Activity,
  BarChart3,
  Target,
  TrendingUp,
  TrendingDown,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

const costComparison = [
  { vendor: "SummitView Construction", estimate: 23000, actual: 28290, variance: 23.0 },
  { vendor: "AquaPure Water Services", estimate: 21000, actual: 25410, variance: 21.0 },
  { vendor: "BrightSpark Electric", estimate: 19000, actual: 22610, variance: 19.0 },
  { vendor: "SteelFrame Structural", estimate: 17000, actual: 19890, variance: 17.0 },
  { vendor: "QuickFix Handyman", estimate: 15000, actual: 17250, variance: 15.0 },
  { vendor: "TrueNorth Roofing", estimate: 13000, actual: 14690, variance: 13.0 },
  { vendor: "AllStar Maintenance", estimate: 11000, actual: 12210, variance: 11.0 },
  { vendor: "FireGuard Systems", estimate: 9000, actual: 9810, variance: 9.0 },
  { vendor: "FloodStop Remediation", estimate: 7000, actual: 7490, variance: 7.0 },
  { vendor: "PrimeCraft Builders", estimate: 5000, actual: 5250, variance: 5.0 },
  { vendor: "SafeHaven Security", estimate: 23000, actual: 23690, variance: 3.0 },
  { vendor: "GreenTree Landscaping", estimate: 21000, actual: 21210, variance: 1.0 },
  { vendor: "ElectriFix Solutions", estimate: 19000, actual: 18810, variance: -1.0 },
  { vendor: "RoofMasters Inc", estimate: 17000, actual: 16490, variance: -3.0 },
  { vendor: "AquaShield Plumbing", estimate: 15000, actual: 14250, variance: -5.0 },
  { vendor: "ClearView Glass", estimate: 13000, actual: 12090, variance: -7.0 },
];

const benchmarkGroups = [
  {
    specialty: "Fire",
    avg: 7030,
    vendors: [
      { name: "Apex Repairs", cost: 4250 },
      { name: "FireGuard Systems", cost: 9810 },
    ],
  },
  {
    specialty: "Water",
    avg: 13310,
    vendors: [
      { name: "BlueLine Restoration", cost: 6090 },
      { name: "AquaShield Plumbing", cost: 14250 },
      { name: "FloodStop Remediation", cost: 7490 },
      { name: "AquaPure Water Services", cost: 25410 },
    ],
  },
  {
    specialty: "Wind",
    avg: 8010,
    vendors: [{ name: "StormGuard Services", cost: 8010 }],
  },
  {
    specialty: "Structural",
    avg: 11717,
    vendors: [
      { name: "ProBuild Contractors", cost: 10010 },
      { name: "PrimeCraft Builders", cost: 5250 },
      { name: "SteelFrame Structural", cost: 19890 },
    ],
  },
  {
    specialty: "Glass/Windows",
    avg: 12090,
    vendors: [{ name: "ClearView Glass", cost: 12090 }],
  },
  {
    specialty: "Roofing",
    avg: 19823,
    vendors: [
      { name: "RoofMasters Inc", cost: 16490 },
      { name: "TrueNorth Roofing", cost: 14690 },
      { name: "SummitView Construction", cost: 28290 },
    ],
  },
];

const costRecords: { vendor: string; claimId: string; estimated: number; actual: number | null }[] = [
  { vendor: "Apex Repairs", claimId: "CLM-2025-001", estimated: 3000, actual: 3151 },
  { vendor: "Apex Repairs", claimId: "CLM-2025-002", estimated: 4500, actual: null },
  { vendor: "BlueLine Restoration", claimId: "CLM-2025-004", estimated: 6000, actual: null },
  { vendor: "BlueLine Restoration", claimId: "CLM-2025-005", estimated: 7500, actual: null },
  { vendor: "BlueLine Restoration", claimId: "CLM-2025-006", estimated: 9000, actual: null },
  { vendor: "StormGuard Services", claimId: "CLM-2025-007", estimated: 10500, actual: null },
  { vendor: "StormGuard Services", claimId: "CLM-2025-008", estimated: 12000, actual: null },
  { vendor: "StormGuard Services", claimId: "CLM-2025-009", estimated: 13500, actual: 12666 },
  { vendor: "StormGuard Services", claimId: "CLM-2025-010", estimated: 15000, actual: null },
  { vendor: "ProBuild Contractors", claimId: "CLM-2025-010", estimated: 16500, actual: null },
  { vendor: "ProBuild Contractors", claimId: "CLM-2025-011", estimated: 18000, actual: 17574 },
  { vendor: "ClearView Glass", claimId: "CLM-2025-013", estimated: 19500, actual: 19497 },
  { vendor: "ClearView Glass", claimId: "CLM-2025-014", estimated: 21000, actual: null },
  { vendor: "ClearView Glass", claimId: "CLM-2025-015", estimated: 22500, actual: null },
  { vendor: "AquaShield Plumbing", claimId: "CLM-2025-016", estimated: 24000, actual: null },
  { vendor: "AquaShield Plumbing", claimId: "CLM-2025-017", estimated: 25500, actual: null },
  { vendor: "AquaShield Plumbing", claimId: "CLM-2025-018", estimated: 27000, actual: null },
];

const fmt = (n: number) => `$${n.toLocaleString()}`;

export default function VendorCostAnalytics() {
  const [recordsOpen, setRecordsOpen] = useState(false);

  const maxVariance = 23;
  const benchmarkMax = 30000;

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-8 py-7 shadow-md">
        <h1 className="text-3xl font-extrabold tracking-tight text-white">Cost &amp; Estimate Analytics</h1>
        <p className="mt-1 text-sm text-indigo-200/80 font-medium">Analyze vendor cost variances, benchmarks, and estimation accuracy</p>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-slate-900 to-slate-800">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Total Estimates Processed</span>
            <FileText className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">59</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-blue-800 to-indigo-900">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Avg Estimate Amount</span>
            <FileText className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">$14,297</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-emerald-600 to-green-700">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Avg Actual Cost</span>
            <DollarSign className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">$14,947</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-red-600 to-orange-600">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Overall Variance %</span>
            <Activity className="h-4 w-4 opacity-80" />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-extrabold">4.0%</span>
            <span className="rounded-full bg-white/20 px-2 py-0.5 text-[10px] font-bold">Overrun</span>
          </div>
        </div>
      </div>

      {/* Cost Comparison by Vendor */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-violet-600 to-blue-600">
          <BarChart3 className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Cost Comparison by Vendor</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-900 text-white text-left text-[11px] uppercase tracking-wide">
              <th className="px-5 py-2.5 font-bold">Vendor</th>
              <th className="px-5 py-2.5 font-bold">Avg Estimate ($)</th>
              <th className="px-5 py-2.5 font-bold">Avg Actual Cost ($)</th>
              <th className="px-5 py-2.5 font-bold">Variance (%)</th>
              <th className="px-5 py-2.5 font-bold">Trend</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {costComparison.map((r) => (
              <tr key={r.vendor} className="odd:bg-amber-50/40 hover:bg-slate-50">
                <td className="px-5 py-3 font-bold text-slate-900">{r.vendor}</td>
                <td className="px-5 py-3 text-slate-700">{fmt(r.estimate)}</td>
                <td className="px-5 py-3 text-slate-700">{fmt(r.actual)}</td>
                <td className="px-5 py-3">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-extrabold text-white ${
                      r.variance > 0 ? "bg-amber-500" : "bg-emerald-500"
                    }`}
                  >
                    {r.variance > 0 ? "+" : ""}
                    {r.variance.toFixed(1)}%
                  </span>
                </td>
                <td className="px-5 py-3">
                  {r.variance > 0 ? (
                    <TrendingUp className="h-4 w-4 text-amber-500" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-emerald-500" />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Over/Under Estimation Trends */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-emerald-600 to-cyan-600">
          <Activity className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Over/Under Estimation Trends</h2>
        </div>
        <div className="p-6 space-y-3">
          {costComparison.map((r) => (
            <div key={r.vendor} className="grid grid-cols-[160px_1fr_60px] items-center gap-3">
              <span className="text-xs font-semibold text-slate-700 text-right truncate">{r.vendor}</span>
              <div className="relative h-5">
                <div className="absolute inset-y-0 left-1/2 w-px bg-slate-200" />
                {r.variance >= 0 ? (
                  <div
                    className="absolute inset-y-0 left-1/2 rounded-r-full bg-red-400"
                    style={{ width: `${(r.variance / maxVariance) * 48}%` }}
                  />
                ) : (
                  <div
                    className="absolute inset-y-0 rounded-l-full bg-emerald-400"
                    style={{ right: "50%", width: `${(Math.abs(r.variance) / maxVariance) * 48}%` }}
                  />
                )}
              </div>
              <span className={`text-xs font-extrabold ${r.variance >= 0 ? "text-red-600" : "text-emerald-600"}`}>
                {r.variance > 0 ? "+" : ""}
                {r.variance.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Cost Benchmarking by Specialty */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-orange-500 to-red-600">
          <Target className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Cost Benchmarking by Specialty</h2>
        </div>
        <div className="p-6 space-y-7">
          {benchmarkGroups.map((g) => (
            <div key={g.specialty}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-extrabold text-slate-900">{g.specialty}</span>
                <span className="text-[11px] font-semibold text-slate-400">Avg: {fmt(g.avg)}</span>
              </div>
              <div className="space-y-2.5">
                {g.vendors.map((v) => {
                  const above = v.cost > g.avg;
                  return (
                    <div key={v.name} className="grid grid-cols-[150px_1fr_auto] items-center gap-3">
                      <span className="text-xs font-semibold text-slate-600 text-right truncate">{v.name}</span>
                      <div className="relative h-4 rounded-full bg-slate-100 overflow-visible">
                        <div
                          className={`h-full rounded-full ${above ? "bg-red-400" : "bg-emerald-400"}`}
                          style={{ width: `${Math.min((v.cost / benchmarkMax) * 100, 100)}%` }}
                        />
                        <div
                          className="absolute top-[-3px] bottom-[-3px] w-[2px] bg-slate-800"
                          style={{ left: `${Math.min((g.avg / benchmarkMax) * 100, 100)}%` }}
                        />
                      </div>
                      <span className="flex items-center gap-2">
                        <span className="text-xs font-extrabold text-slate-800 w-16 text-right">{fmt(v.cost)}</span>
                        {above && (
                          <span className="rounded-full bg-red-600 px-2 py-0.5 text-[9px] font-bold text-white whitespace-nowrap">
                            Above Benchmark
                          </span>
                        )}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detailed Cost Records */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <button
          onClick={() => setRecordsOpen((o) => !o)}
          className="w-full px-5 py-3.5 flex items-center justify-between bg-gradient-to-r from-slate-900 to-slate-800 text-left"
        >
          <span className="flex items-center gap-2.5">
            <FileText className="h-4 w-4 text-white" />
            <span className="text-white font-extrabold text-sm">Detailed Cost Records</span>
          </span>
          <span className="flex items-center gap-1.5 text-[11px] font-bold text-slate-300">
            {recordsOpen ? "Collapse" : "Expand"}
            {recordsOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </span>
        </button>
        {recordsOpen && (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-indigo-950 text-white text-left text-[11px] uppercase tracking-wide">
                <th className="px-5 py-2.5 font-bold">Vendor</th>
                <th className="px-5 py-2.5 font-bold">Claim ID</th>
                <th className="px-5 py-2.5 font-bold">Estimated Cost</th>
                <th className="px-5 py-2.5 font-bold">Actual Cost</th>
                <th className="px-5 py-2.5 font-bold">Difference</th>
                <th className="px-5 py-2.5 font-bold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {costRecords.map((r, i) => {
                const diff = r.actual !== null ? r.actual - r.estimated : null;
                return (
                  <tr key={`${r.claimId}-${i}`} className="hover:bg-slate-50">
                    <td className="px-5 py-3 font-bold text-slate-900">{r.vendor}</td>
                    <td className="px-5 py-3 text-slate-500 text-xs">{r.claimId}</td>
                    <td className="px-5 py-3 text-slate-700">{fmt(r.estimated)}</td>
                    <td className="px-5 py-3">
                      {r.actual !== null ? (
                        <span className="text-slate-700">{fmt(r.actual)}</span>
                      ) : (
                        <span className="italic text-slate-400">Pending</span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      {diff !== null ? (
                        <span className={`font-bold ${diff > 0 ? "text-red-600" : "text-emerald-600"}`}>
                          {diff > 0 ? `+$${diff.toLocaleString()}` : `$-${Math.abs(diff).toLocaleString()}`}
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      {r.actual !== null ? (
                        <span className="inline-flex rounded-full bg-emerald-600 px-2.5 py-0.5 text-[10px] font-bold text-white">Completed</span>
                      ) : (
                        <span className="inline-flex rounded-full bg-amber-500 px-2.5 py-0.5 text-[10px] font-bold text-white">Pending</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
