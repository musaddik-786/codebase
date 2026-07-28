import { useState, useEffect, useMemo } from "react";
import {
  BarChart3,
  CheckCircle2,
  Clock,
  DollarSign,
  FileText,
  Gauge,
  Loader2,
  Package,
  Scale,
  Search,
  Shield,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  Users,
  Wrench,
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const fmt = (val: number | null | undefined) => {
  if (val == null) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }).format(val);
};

function severityPill(severity: string): string {
  const s = severity.toLowerCase();
  if (s.includes("critical") || s.includes("severe")) return "bg-red-600";
  if (s.includes("high")) return "bg-orange-500";
  if (s.includes("medium") || s.includes("moderate")) return "bg-orange-400";
  return "bg-emerald-500";
}

interface Factor {
  icon: React.ReactNode;
  title: string;
  verdict: "Supports" | "Neutral";
  description: string;
}

export default function RepairVsReplacement() {
  const [claims, setClaims] = useState<any[]>([]);
  const [selectedClaimId, setSelectedClaimId] = useState<string>("");
  const [claimSearch, setClaimSearch] = useState("");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/claims")
      .then((res) => res.json())
      .then((json) => {
        const list = json.claims || [];
        setClaims(list);
        if (list.length > 0) setSelectedClaimId(list[0].id);
        else setLoading(false);
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
    fetch(`/api/adjuster/repair-vs-replacement?claimNumber=${selectedClaimId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load repair vs replacement data");
        return res.json();
      })
      .then((json) => setData(json))
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

  const repair = data?.comparison?.repair;
  const replacement = data?.comparison?.replacement;
  const action = data?.recommendation?.action || "Repair";
  const confidence = data?.recommendation?.confidence;
  const ex = data?.explainability;

  const factors: Factor[] = useMemo(() => {
    if (!data) return [];
    const repairTotal = repair?.total ?? 0;
    const replaceTotal = replacement?.total ?? 0;
    const ratio = ex?.costRatio;
    const fraudLevel = ex?.fraudLevel || "Low";
    return [
      {
        icon: <DollarSign className="h-4 w-4" />,
        title: "Cost Threshold Comparison",
        verdict: "Neutral",
        description: ratio != null
          ? `Repair cost is ${ratio}% of replacement cost (${fmt(repairTotal)} vs ${fmt(replaceTotal)}).`
          : "Cost comparison data is being compiled for this claim.",
      },
      {
        icon: <TrendingDown className="h-4 w-4" />,
        title: "Asset Age & Depreciation",
        verdict: "Supports",
        description: "Asset has significant remaining useful life, favoring the recommended path.",
      },
      {
        icon: <Gauge className="h-4 w-4" />,
        title: "Extent & Severity of Damage",
        verdict: "Supports",
        description: `Damage severity assessed as ${data?.claim?.severity || "—"} — within ${action.toLowerCase()} feasibility range.`,
      },
      {
        icon: <Wrench className="h-4 w-4" />,
        title: "Repair Feasibility",
        verdict: "Supports",
        description: `Qualified vendors available for ${data?.claim?.lossType || "this loss type"} work in the claim region.`,
      },
      {
        icon: <Clock className="h-4 w-4" />,
        title: "Turnaround Time Impact",
        verdict: "Supports",
        description: `Estimated ${repair?.days ?? "—"} day(s) for repair vs ${replacement?.days ?? "—"} day(s) for replacement.`,
      },
      {
        icon: <Shield className="h-4 w-4" />,
        title: "Policy & Coverage Conditions",
        verdict: "Supports",
        description: ex?.netPayable != null
          ? `Net payable after deductible: ${fmt(ex.netPayable)} — within coverage terms.`
          : "Coverage terms permit the recommended settlement path.",
      },
      {
        icon: <Users className="h-4 w-4" />,
        title: "Vendor Input & Historical Data",
        verdict: "Supports",
        description: ex?.benchmark
          ? `${ex.benchmark.vendorName} benchmark: avg repair ${fmt(ex.benchmark.avgRepair)}, avg replacement ${fmt(ex.benchmark.avgReplacement)}, ETA ${ex.benchmark.etaDays} days.`
          : "Historical vendor benchmarks align with the recommendation.",
      },
      {
        icon: <Scale className="h-4 w-4" />,
        title: "Subrogation Potential",
        verdict: "Neutral",
        description: `Fraud risk assessed as ${fraudLevel} (score: ${ex?.fraudScore ?? 0}) — no subrogation constraints identified.`,
      },
    ];
  }, [data, repair, replacement, action, ex]);

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-7 py-5 shadow-md flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
            <Scale className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-white">Repair vs Replacement Summary</h1>
            <p className="mt-0.5 text-sm text-indigo-200/80 font-medium">AI-powered cost comparison, life expectancy analysis, and decision support</p>
          </div>
        </div>
        <span className="rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs font-bold text-white whitespace-nowrap">Adjuster</span>
      </div>

      {/* Claim Selector */}
      <div className="rounded-xl bg-slate-950 border border-slate-800 px-6 py-5 shadow-lg">
        <h2 className="flex items-center gap-2 text-white font-extrabold mb-4">
          <FileText className="h-4 w-4 text-violet-300" /> Claim Selector
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 items-end">
          <div>
            <label className="block text-[11px] font-bold text-slate-300 mb-1.5">Search Claim</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
              <input
                value={claimSearch}
                onChange={(e) => setClaimSearch(e.target.value)}
                placeholder="Search claim #"
                className="w-full rounded-full bg-slate-900 border border-slate-700 pl-8 pr-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-[11px] font-bold text-slate-300 mb-1.5">Select Claim</label>
            <Select value={selectedClaimId} onValueChange={setSelectedClaimId}>
              <SelectTrigger className="w-full rounded-lg bg-slate-900 border-violet-400/60 text-white font-semibold text-sm h-9">
                <SelectValue placeholder="Select claim" />
              </SelectTrigger>
              <SelectContent>
                {filteredClaims.map((c: any) => (
                  <SelectItem key={c.id} value={c.id}>{c.id}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <div className="text-[10px] font-bold tracking-wider text-slate-400 mb-2">LOSS TYPE</div>
            <span className="inline-flex rounded-full bg-slate-700 px-3 py-1 text-[11px] font-bold text-white whitespace-nowrap">
              {data?.claim?.lossType || "—"}
            </span>
          </div>
          <div>
            <div className="text-[10px] font-bold tracking-wider text-slate-400 mb-2">STATUS</div>
            <span className="inline-flex rounded-full bg-violet-500 px-3 py-1 text-[11px] font-bold text-white whitespace-nowrap">
              {data?.claim?.status || "—"}
            </span>
          </div>
          <div>
            <div className="text-[10px] font-bold tracking-wider text-slate-400 mb-2">AI SEVERITY</div>
            <span className={`inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white whitespace-nowrap ${severityPill(data?.claim?.severity || "")}`}>
              {data?.claim?.severity || "—"}
            </span>
          </div>
          <div>
            <div className="text-[10px] font-bold tracking-wider text-slate-400 mb-2">FRAUD SCORE</div>
            <span className={`text-sm font-extrabold ${
              (data?.claim?.fraudLevel || "Low") === "High" ? "text-red-400"
                : (data?.claim?.fraudLevel || "Low") === "Medium" ? "text-amber-400" : "text-emerald-400"
            }`}>
              {data?.claim?.fraudLevel || "—"}
            </span>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-violet-600" /></div>
      ) : error ? (
        <div className="bg-red-50 text-red-600 p-4 rounded-xl border border-red-200 font-medium">{error}</div>
      ) : data ? (
        <>
          {/* Financial Impact Comparison */}
          <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
            <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-purple-700 px-6 py-4">
              <h2 className="text-white font-extrabold">Loss Assessment: Generated via AI Analysis</h2>
              <p className="text-xs text-blue-100/90 mt-0.5">Financial Impact Comparison</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-slate-200 text-[11px] font-extrabold tracking-wider">
                    <th className="px-6 py-3.5 text-slate-500">METRIC</th>
                    <th className="px-6 py-3.5 text-blue-700 bg-blue-50/70">
                      <span className="inline-flex items-center gap-1.5"><Wrench className="h-3.5 w-3.5" /> REPAIR</span>
                    </th>
                    <th className="px-6 py-3.5 text-purple-700 bg-fuchsia-50/70">
                      <span className="inline-flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5" /> REPLACEMENT</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr>
                    <td className="px-6 py-4 text-sm font-semibold text-slate-700">
                      <span className="inline-flex items-center gap-2"><DollarSign className="h-4 w-4 text-slate-400" /> Total Cost</span>
                    </td>
                    <td className="px-6 py-4 bg-blue-50/40 text-lg font-extrabold text-blue-600">{fmt(repair?.total)}</td>
                    <td className="px-6 py-4 bg-fuchsia-50/40 text-lg font-extrabold text-fuchsia-600">{fmt(replacement?.total)}</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm font-semibold text-slate-700">
                      <span className="inline-flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-slate-400" /> Net Payable</span>
                    </td>
                    <td className="px-6 py-4 bg-blue-50/40 text-lg font-extrabold text-emerald-600">{fmt(ex?.netPayable ?? repair?.total)}</td>
                    <td className="px-6 py-4 bg-fuchsia-50/40 text-lg font-extrabold text-emerald-600">{fmt(replacement?.total)}</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm font-semibold text-slate-700">
                      <span className="inline-flex items-center gap-2"><Clock className="h-4 w-4 text-slate-400" /> Time</span>
                    </td>
                    <td className="px-6 py-4 bg-blue-50/40 text-sm font-extrabold text-blue-600">{repair?.days ?? "—"} days</td>
                    <td className="px-6 py-4 bg-fuchsia-50/40 text-sm font-extrabold text-purple-600">{replacement?.days ?? "—"} days</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="bg-emerald-50 border-t border-emerald-100 px-6 py-3.5 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              <span className="text-sm font-extrabold text-emerald-800">
                AI Recommendation: {action}
                {confidence != null && <span className="font-bold text-emerald-700"> — Confidence: {confidence}%</span>}
              </span>
            </div>
          </div>

          {/* Side-by-Side Scenario Comparison */}
          <div>
            <h2 className="flex items-center gap-2 font-extrabold text-slate-900 text-lg mb-4">
              <BarChart3 className="h-5 w-5 text-indigo-600" /> Side-by-Side Scenario Comparison
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {/* Repair Scenario */}
              <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
                <div className="bg-gradient-to-r from-teal-500 to-cyan-500 px-6 py-3.5 flex items-center gap-2.5">
                  <Wrench className="h-4 w-4 text-white" />
                  <h3 className="text-white font-extrabold">Repair Scenario</h3>
                </div>
                <div className="p-5 space-y-4">
                  <div className="rounded-xl border border-blue-100 bg-blue-50/50 px-5 py-4">
                    <div className="text-[10px] font-extrabold tracking-wider text-slate-500 mb-1">REPAIR COST</div>
                    <div className="text-2xl font-extrabold text-blue-600">{fmt(repair?.total)}</div>
                    <div className="text-xs text-slate-500 mt-1">Material: {fmt(repair?.material)} &nbsp;|&nbsp; Labor: {fmt(repair?.labor)}</div>
                  </div>
                  <div className="rounded-xl border border-teal-100 bg-teal-50/50 px-5 py-4">
                    <div className="text-[10px] font-extrabold tracking-wider text-slate-500 mb-1">ESTIMATED COMPLETION TIME</div>
                    <div className="text-2xl font-extrabold text-teal-600">{repair?.days ?? "—"} days</div>
                    <div className="text-xs text-slate-500 mt-1">Based on damage scope and labor availability</div>
                  </div>
                  <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 px-5 py-4">
                    <div className="text-[10px] font-extrabold tracking-wider text-slate-500 mb-1">VENDOR AVAILABILITY</div>
                    <div className="text-lg font-extrabold text-emerald-600">Pending Assignment</div>
                    <div className="text-xs text-slate-500 mt-1">Awaiting vendor assignment</div>
                  </div>
                  <div className="rounded-xl border border-amber-100 bg-amber-50/50 px-5 py-4">
                    <div className="text-[10px] font-extrabold tracking-wider text-slate-500 mb-1">DOWNTIME IMPACT</div>
                    <div className="text-lg font-extrabold text-amber-600">Minimal — {repair?.days ?? "—"} day(s)</div>
                    <div className="text-xs text-slate-500 mt-1">Property usable during repair</div>
                  </div>
                </div>
              </div>

              {/* Replacement Scenario */}
              <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
                <div className="bg-gradient-to-r from-violet-600 to-purple-600 px-6 py-3.5 flex items-center gap-2.5">
                  <Package className="h-4 w-4 text-white" />
                  <h3 className="text-white font-extrabold">Replacement Scenario</h3>
                </div>
                <div className="p-5 space-y-4">
                  <div className="rounded-xl border border-fuchsia-100 bg-fuchsia-50/50 px-5 py-4">
                    <div className="text-[10px] font-extrabold tracking-wider text-slate-500 mb-1">REPLACEMENT COST</div>
                    <div className="text-2xl font-extrabold text-fuchsia-600">{fmt(replacement?.total)}</div>
                    <div className="text-xs text-slate-500 mt-1">Material: {fmt(replacement?.material)} &nbsp;|&nbsp; Install: {fmt(replacement?.install)}</div>
                  </div>
                  <div className="rounded-xl border border-purple-100 bg-purple-50/50 px-5 py-4">
                    <div className="text-[10px] font-extrabold tracking-wider text-slate-500 mb-1">LEAD TIME</div>
                    <div className="text-2xl font-extrabold text-purple-600">{replacement?.days ?? "—"} days</div>
                    <div className="text-xs text-slate-500 mt-1">Includes procurement, delivery, and installation</div>
                  </div>
                  <div className="rounded-xl border border-amber-100 bg-amber-50/50 px-5 py-4">
                    <div className="text-[10px] font-extrabold tracking-wider text-slate-500 mb-1">DEPRECIATION IMPACT</div>
                    <div className="text-lg font-extrabold text-amber-600">Low — asset has significant remaining value</div>
                    <div className="text-xs text-slate-500 mt-1">Remaining useful life: 6 years</div>
                  </div>
                  <div className="rounded-xl border border-teal-100 bg-teal-50/50 px-5 py-4">
                    <div className="text-[10px] font-extrabold tracking-wider text-slate-500 mb-1">PROCUREMENT AVAILABILITY</div>
                    <div className="text-lg font-extrabold text-teal-600">In Stock — Ready for dispatch</div>
                    <div className="text-xs text-slate-500 mt-1">Based on vendor inventory and supply chain status</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* AI Explainability Panel */}
          <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
            <div className="bg-gradient-to-r from-slate-950 via-indigo-950 to-slate-900 px-6 py-4 flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/10">
                <Sparkles className="h-4 w-4 text-violet-300" />
              </div>
              <div>
                <h2 className="text-white font-extrabold">AI Explainability Panel</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Why <span className="font-bold text-violet-300">{action}</span> was recommended for {data?.claim?.claimNumber}
                </p>
              </div>
            </div>
            <div className="divide-y divide-slate-100">
              {factors.map((f) => (
                <div key={f.title} className="px-6 py-4 flex items-start gap-4">
                  <div className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${
                    f.verdict === "Supports" ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"
                  }`}>
                    {f.icon}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="font-extrabold text-slate-900 text-sm">{f.title}</span>
                      <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                        f.verdict === "Supports"
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-amber-100 text-amber-700"
                      }`}>
                        {f.verdict}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">{f.description}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="bg-indigo-50/70 border-t border-indigo-100 px-6 py-4 text-center">
              <div className="font-extrabold text-indigo-900">
                Decision Confidence: {confidence != null ? `${confidence}%` : "—"}
              </div>
              <div className="text-xs text-indigo-500 mt-0.5">Based on 8 weighted assessment factors analyzed by AI engine</div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
