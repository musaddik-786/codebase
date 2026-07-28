import { useState } from "react";
import { Clock, Star, DollarSign, ShieldCheck, Trophy, BarChart3, AlertTriangle, Lightbulb, TrendingDown, TrendingUp } from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { topVendors, visWeights, bottomPerformers } from "@/lib/vendor-data";

function rankCircle(rank: number): string {
  if (rank === 1) return "bg-amber-400 text-white";
  if (rank === 2) return "bg-slate-400 text-white";
  if (rank === 3) return "bg-orange-500 text-white";
  return "bg-slate-200 text-slate-600";
}

export default function VendorPerformance() {
  const [visVendor, setVisVendor] = useState<(typeof topVendors)[0] | null>(null);

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-8 py-7 shadow-md">
        <h1 className="text-3xl font-extrabold tracking-tight text-white">Vendor Performance</h1>
        <p className="mt-1 text-sm text-indigo-200/80 font-medium">Monitor vendor intelligence scores, SLA compliance, and performance metrics</p>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-slate-900 to-slate-800">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Avg Completion Time</span>
            <Clock className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">5 days</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-blue-800 to-indigo-900">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Avg Customer Rating</span>
            <Star className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">3.4 / 5</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-red-600 to-orange-600">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Cost Accuracy %</span>
            <DollarSign className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">73%</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-emerald-600 to-green-700">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Avg SLA Compliance</span>
            <ShieldCheck className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">77%</div>
        </div>
      </div>

      {/* Top 5 leaderboard */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-emerald-600 to-cyan-600">
          <Trophy className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Top 5 Vendors — VIS Leaderboard</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {topVendors.map((v) => (
            <button
              key={v.name}
              onClick={() => setVisVendor(v)}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50/70 transition-colors text-left"
            >
              <div className="flex items-center gap-4">
                <span className={`inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-extrabold shadow-sm ${rankCircle(v.rank)}`}>
                  {v.rank}
                </span>
                <div>
                  <div className="font-extrabold text-slate-900 text-sm">{v.name}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">{v.specialty} · {v.location}</div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-lg font-extrabold text-emerald-600">
                  {v.vis} <span className="text-[10px] font-bold text-slate-400">VIS</span>
                </span>
                <div className="w-24 h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div className="h-full rounded-full bg-emerald-500" style={{ width: `${v.vis}%` }} />
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Vendor Performance Distribution */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-violet-600 to-blue-600">
          <BarChart3 className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Vendor Performance Distribution</h2>
        </div>
        <div className="p-5 space-y-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="flex items-center gap-2 text-sm font-bold text-slate-800">
                <TrendingUp className="h-3.5 w-3.5 text-slate-500" /> High Performers
                <span className="text-[10px] font-semibold text-slate-400">(VIS ≥ 80)</span>
              </span>
              <span className="text-sm font-extrabold text-slate-900">6 <span className="text-[11px] font-semibold text-slate-400">(15%)</span></span>
            </div>
            <div className="w-full h-4 rounded-full bg-slate-100 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-emerald-700 to-emerald-500" style={{ width: "15%" }} />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="flex items-center gap-2 text-sm font-bold text-slate-800">
                <BarChart3 className="h-3.5 w-3.5 text-slate-500" /> Medium Performers
                <span className="text-[10px] font-semibold text-slate-400">(VIS 60-79)</span>
              </span>
              <span className="text-sm font-extrabold text-slate-900">14 <span className="text-[11px] font-semibold text-slate-400">(35%)</span></span>
            </div>
            <div className="w-full h-4 rounded-full bg-slate-100 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-orange-500 to-amber-700" style={{ width: "35%" }} />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="flex items-center gap-2 text-sm font-bold text-slate-800">
                <TrendingDown className="h-3.5 w-3.5 text-slate-500" /> Low Performers
                <span className="text-[10px] font-semibold text-slate-400">(VIS &lt; 60)</span>
              </span>
              <span className="text-sm font-extrabold text-slate-900">20 <span className="text-[11px] font-semibold text-slate-400">(50%)</span></span>
            </div>
            <div className="w-full h-4 rounded-full bg-slate-100 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-red-800 to-red-600" style={{ width: "50%" }} />
            </div>
          </div>
        </div>
      </div>

      {/* Bottom 5 performers */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-red-600 to-pink-600">
          <AlertTriangle className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Bottom 5 Performers</h2>
        </div>
        <table className="w-full text-left">
          <thead>
            <tr className="bg-gradient-to-r from-indigo-950 to-violet-950 text-white text-xs font-bold">
              <th className="px-5 py-2.5">Vendor</th>
              <th className="px-5 py-2.5">VIS</th>
              <th className="px-5 py-2.5">Issues</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {bottomPerformers.map((v) => (
              <tr key={v.name}>
                <td className="px-5 py-3.5 min-w-[160px]">
                  <div className="font-extrabold text-slate-900 text-sm">{v.name}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">{v.specialty} · {v.location}</div>
                </td>
                <td className="px-5 py-3.5 text-lg font-extrabold text-amber-500">{v.vis}</td>
                <td className="px-5 py-3.5">
                  <div className="flex flex-wrap gap-1.5">
                    {v.issues.map((issue) => (
                      <span key={issue} className="rounded-full border border-red-200 bg-red-50 text-red-500 px-2.5 py-0.5 text-[10px] font-bold whitespace-nowrap">
                        {issue}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Key Insights */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-teal-600 to-emerald-600">
          <Lightbulb className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Key Insights</h2>
        </div>
        <div className="p-5 space-y-3">
          <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50/60 px-4 py-3 text-sm font-medium text-slate-700">
            <TrendingDown className="h-4 w-4 text-red-500 flex-shrink-0" />
            50% of vendors (20) are below acceptable performance threshold (VIS &lt; 60)
          </div>
          <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50/60 px-4 py-3 text-sm font-medium text-slate-700">
            <ShieldCheck className="h-4 w-4 text-amber-500 flex-shrink-0" />
            65% of vendors (13) have SLA compliance below 90%, requiring attention
          </div>
          <div className="flex items-center gap-3 rounded-lg border border-orange-200 bg-orange-50/60 px-4 py-3 text-sm font-medium text-slate-700">
            <DollarSign className="h-4 w-4 text-orange-500 flex-shrink-0" />
            7 vendors show consistent cost overruns: AllStar Maintenance, TrueNorth Roofing, QuickFix Handyman +4 more
          </div>
          <div className="flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50/60 px-4 py-3 text-sm font-medium text-slate-700">
            <TrendingUp className="h-4 w-4 text-emerald-500 flex-shrink-0" />
            15% of vendors (6) are high performers (VIS ≥ 80), network average VIS is 37
          </div>
        </div>
      </div>

      {/* VIS Breakdown popup */}
      <Dialog open={!!visVendor} onOpenChange={(o) => !o && setVisVendor(null)}>
        <DialogContent className="max-w-md p-6">
          {visVendor && (
            <>
              <DialogTitle className="text-base font-extrabold text-slate-900 mb-1">
                VIS Breakdown — {visVendor.name}
              </DialogTitle>
              <p className="text-xs text-slate-500 mb-4">{visVendor.specialty} · {visVendor.location}</p>
              <div className="space-y-2.5">
                {visWeights.map((w) => {
                  const score = visVendor.breakdown[w.key];
                  return (
                    <div key={w.key} className="flex items-center gap-3">
                      <span className="w-44 text-xs font-semibold text-slate-700 flex-shrink-0">
                        {w.label} <span className="text-slate-400">({Math.round(w.weight * 100)}%)</span>
                      </span>
                      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                        <div className="h-full rounded-full bg-violet-500" style={{ width: `${score}%` }} />
                      </div>
                      <span className="w-8 text-right text-xs font-extrabold text-slate-900">{score}</span>
                    </div>
                  );
                })}
              </div>
              <div className="mt-4 rounded-lg bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-3 flex items-center justify-between">
                <span className="text-sm font-bold text-white">Weighted Total (VIS)</span>
                <span className="text-xl font-extrabold text-white">{visVendor.vis}</span>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
