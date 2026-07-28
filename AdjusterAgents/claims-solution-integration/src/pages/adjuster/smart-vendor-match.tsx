import { useEffect, useState, useMemo } from "react";
import { useToast } from "@/hooks/use-toast";
import {
  Building2,
  CheckCircle2,
  Clock,
  DollarSign,
  FileText,
  Filter,
  Loader2,
  MapPin,
  Phone,
  Play,
  Search,
  Shield,
  Sparkles,
  Star,
  ThumbsUp,
  TrendingUp,
  UserCheck,
  Users,
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const fmt = (val: number | null | undefined) => {
  if (val == null) return "—";
  return new Intl.NumberFormat("en-US").format(val);
};

function rankCircle(rank: number): string {
  if (rank === 1) return "bg-amber-400 text-white";
  if (rank === 2) return "bg-slate-400 text-white";
  if (rank === 3) return "bg-orange-400 text-white";
  return "bg-slate-200 text-slate-600";
}

function subroPill(level: string): string {
  if (level === "High") return "bg-red-500";
  if (level === "Medium") return "bg-amber-500";
  return "bg-emerald-500";
}

export default function SmartVendorMatch() {
  const { toast } = useToast();
  const [claims, setClaims] = useState<any[]>([]);
  const [selectedClaimNumber, setSelectedClaimNumber] = useState<string>("");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [specialtyFilter, setSpecialtyFilter] = useState("all");
  const [sortBy, setSortBy] = useState("vis");

  useEffect(() => {
    fetch("/api/claims")
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load claims (${res.status})`);
        return res.json();
      })
      .then((d) => {
        const list = d.claims || [];
        setClaims(list);
        if (list.length > 0) setSelectedClaimNumber(list[0].id);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load claims");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const qs = selectedClaimNumber ? `?claimNumber=${encodeURIComponent(selectedClaimNumber)}` : "";
    fetch(`/api/adjuster/vendor-match${qs}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load vendor match data");
        return res.json();
      })
      .then((json) => setData(json))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedClaimNumber]);

  const specialties = useMemo(
    () => Array.from(new Set((data?.vendors || []).map((v: any) => String(v.specialty)))) as string[],
    [data]
  );

  const rankedVendors = useMemo(() => {
    let list = [...(data?.vendors || [])];
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (v: any) =>
          v.name.toLowerCase().includes(q) ||
          v.specialty.toLowerCase().includes(q) ||
          `${v.city}, ${v.state}`.toLowerCase().includes(q)
      );
    }
    if (specialtyFilter !== "all") list = list.filter((v: any) => v.specialty === specialtyFilter);
    if (sortBy === "vis") list.sort((a: any, b: any) => b.visScore - a.visScore);
    else if (sortBy === "rating") list.sort((a: any, b: any) => b.rating - a.rating);
    else if (sortBy === "cost") list.sort((a: any, b: any) => a.avgCost - b.avgCost);
    return list;
  }, [data, search, specialtyFilter, sortBy]);

  const rec = data?.recommended;
  const stats = data?.stats;
  const subro = data?.claim?.subrogationPotential || "Low";

  const handleAction = (action: string) => {
    toast({ title: "Action Recorded", description: `Successfully executed: ${action}` });
  };

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-7 py-5 shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
            <Users className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-white">Vendor Matching Intelligence</h1>
            <p className="mt-0.5 text-sm text-indigo-200/80 font-medium">AI-ranked vendors using 9-factor Vendor Intelligence Score (VIS)</p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs font-bold text-white whitespace-nowrap">
            VIS Records: {stats ? stats.totalVendors : "—"}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs font-bold text-white whitespace-nowrap">
            <Users className="h-3.5 w-3.5" /> {stats ? stats.totalVendors : "—"} Vendors
          </span>
        </div>
      </div>

      {/* Search + filters */}
      <div className="flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search vendors by name, specialty, or location..."
            className="w-full rounded-full bg-white border border-slate-200 pl-11 pr-4 py-2.5 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
          />
        </div>
        <Select value={specialtyFilter} onValueChange={setSpecialtyFilter}>
          <SelectTrigger className="w-full md:w-48 rounded-full bg-white border-slate-200 font-semibold text-sm h-10 shadow-sm">
            <span className="flex items-center gap-2"><Filter className="h-3.5 w-3.5 text-slate-400" /><SelectValue placeholder="All Specialties" /></span>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Specialties</SelectItem>
            {specialties.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={sortBy} onValueChange={setSortBy}>
          <SelectTrigger className="w-full md:w-44 rounded-full bg-white border-slate-200 font-semibold text-sm h-10 shadow-sm">
            <span className="flex items-center gap-2"><TrendingUp className="h-3.5 w-3.5 text-slate-400" /><SelectValue placeholder="VIS Score" /></span>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="vis">VIS Score</SelectItem>
            <SelectItem value="rating">Rating</SelectItem>
            <SelectItem value="cost">Avg Cost</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* AI-Powered Vendor Recommendation */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="bg-gradient-to-r from-slate-950 via-indigo-950 to-purple-800 px-6 py-4 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/10">
            <FileText className="h-4 w-4 text-violet-300" />
          </div>
          <div>
            <h2 className="text-white font-extrabold">AI-Powered Vendor Recommendation</h2>
            <p className="text-xs text-slate-400 mt-0.5">Select a claim to compute the 9-factor Vendor Intelligence Score (VIS)</p>
          </div>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-5">
            <div>
              <label className="block text-[11px] font-bold text-slate-500 mb-1.5">Select Claim</label>
              <Select value={selectedClaimNumber} onValueChange={setSelectedClaimNumber}>
                <SelectTrigger className="w-full rounded-lg border-slate-200 font-semibold text-sm h-10">
                  <SelectValue placeholder="Select claim" />
                </SelectTrigger>
                <SelectContent>
                  {claims.map((c: any) => (
                    <SelectItem key={c.id} value={c.id}>{c.id}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <div className="text-[11px] font-bold text-slate-500 mb-2">Loss Type</div>
              <span className="inline-flex rounded-full bg-blue-500 px-3.5 py-1.5 text-[11px] font-bold text-white">
                {data?.claim?.lossType || "—"}
              </span>
            </div>
            <div>
              <div className="text-[11px] font-bold text-slate-500 mb-2">Required Specialty</div>
              <span className="inline-flex rounded-full bg-violet-500 px-3.5 py-1.5 text-[11px] font-bold text-white">
                {data?.claim?.requiredSpecialty || "—"}
              </span>
            </div>
            <div>
              <div className="text-[11px] font-bold text-slate-500 mb-2">Subrogation Potential</div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`inline-flex rounded-full px-3.5 py-1.5 text-[11px] font-bold text-white ${subroPill(subro)}`}>
                  {subro}
                </span>
                {subro === "High" && (
                  <span className="text-[11px] font-semibold text-red-500">Forensic-compliant vendors prioritized</span>
                )}
              </div>
            </div>
          </div>

          {loading ? (
            <div className="flex justify-center py-12"><Loader2 className="w-7 h-7 animate-spin text-violet-600" /></div>
          ) : error ? (
            <div className="bg-red-50 text-red-600 p-4 rounded-xl border border-red-200 font-medium">{error}</div>
          ) : rec ? (
            <div className="rounded-xl border-2 border-emerald-300 bg-emerald-50/70 p-5">
              <div className="flex items-start gap-3 mb-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500 shadow">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <h3 className="font-extrabold text-slate-900">AI Recommended Vendor</h3>
                    <span className="rounded-full bg-emerald-500 px-3 py-0.5 text-[10px] font-bold text-white">Top Match</span>
                    <span className="rounded-full bg-violet-600 px-3 py-0.5 text-[10px] font-bold text-white">VIS: {rec.visScore}%</span>
                  </div>
                  <p className="text-xs font-semibold text-emerald-700 mt-1">
                    Best vendor for {data?.claim?.claimNumber || "this claim"} — scored across specialty, SLA, cost, risk, subrogation, and concentration factors
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                <div className="rounded-lg bg-white border border-emerald-100 px-4 py-3">
                  <div className="text-[10px] font-bold text-slate-500 mb-1">Vendor Name</div>
                  <div className="font-extrabold text-slate-900 text-sm truncate">{rec.name}</div>
                </div>
                <div className="rounded-lg bg-white border border-emerald-100 px-4 py-3">
                  <div className="text-[10px] font-bold text-slate-500 mb-1">Rating</div>
                  <div className="font-extrabold text-slate-900 text-sm flex items-center gap-1">
                    <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" /> {rec.rating}
                  </div>
                </div>
                <div className="rounded-lg bg-white border border-emerald-100 px-4 py-3">
                  <div className="text-[10px] font-bold text-slate-500 mb-1">Avg Cost</div>
                  <div className="font-extrabold text-emerald-600 text-sm">${fmt(rec.avgCost)}</div>
                </div>
                <div className="rounded-lg bg-white border border-emerald-100 px-4 py-3">
                  <div className="text-[10px] font-bold text-slate-500 mb-1">ETA</div>
                  <div className="font-extrabold text-blue-600 text-sm">{rec.avgTurnaroundDays} days</div>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 mb-4">
                <span className="rounded-full bg-emerald-100 text-emerald-700 px-3 py-1 text-[10px] font-bold">SLA: On Track</span>
                <span className="rounded-full bg-amber-100 text-amber-700 px-3 py-1 text-[10px] font-bold">Cost: +6% vs Peer</span>
                <span className="rounded-full bg-emerald-100 text-emerald-700 px-3 py-1 text-[10px] font-bold">
                  Risk: {rec.fraudScore >= 0.4 ? "High" : rec.fraudScore >= 0.2 ? "Medium" : "Low"}
                </span>
                <span className="rounded-full bg-emerald-100 text-emerald-700 px-3 py-1 text-[10px] font-bold">Subro: Compliant</span>
              </div>

              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-700 mb-4">
                <Play className="h-3 w-3 fill-emerald-700" /> View VIS Score Breakdown (9 Factors)
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => handleAction(`Accept Recommendation — ${rec.name}`)}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 px-5 py-2.5 text-sm font-bold text-white shadow-sm transition-colors"
                >
                  <ThumbsUp className="h-4 w-4" /> Accept Recommendation
                </button>
                <button
                  onClick={() => handleAction("View Alternatives")}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-5 py-2.5 text-sm font-bold text-slate-700 transition-colors"
                >
                  View Alternatives
                </button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500 py-6 text-center">No vendor recommendation available</p>
          )}
        </div>
      </div>

      {/* Stat cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <div className="rounded-xl border border-emerald-100 bg-emerald-50/70 px-5 py-4">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="h-4 w-4 text-emerald-500" />
              <span className="text-[11px] font-bold text-slate-500">License Verified</span>
            </div>
            <div className="text-2xl font-extrabold text-emerald-600">{stats.licenseVerified}</div>
          </div>
          <div className="rounded-xl border border-blue-100 bg-blue-50/70 px-5 py-4">
            <div className="flex items-center gap-2 mb-2">
              <Star className="h-4 w-4 text-blue-500" />
              <span className="text-[11px] font-bold text-slate-500">Avg Rating</span>
            </div>
            <div className="text-2xl font-extrabold text-blue-600">{stats.avgRating}</div>
          </div>
          <div className="rounded-xl border border-amber-100 bg-amber-50/70 px-5 py-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="h-4 w-4 text-amber-500" />
              <span className="text-[11px] font-bold text-slate-500">Avg Turnaround</span>
            </div>
            <div className="text-2xl font-extrabold text-amber-600">{stats.avgTurnaroundDays} days</div>
          </div>
          <div className="rounded-xl border border-violet-100 bg-violet-50/70 px-5 py-4">
            <div className="flex items-center gap-2 mb-2">
              <Building2 className="h-4 w-4 text-violet-500" />
              <span className="text-[11px] font-bold text-slate-500">Total Jobs</span>
            </div>
            <div className="text-2xl font-extrabold text-violet-600">{fmt(stats.totalJobs)}</div>
          </div>
          <div className="rounded-xl border border-teal-100 bg-teal-50/70 px-5 py-4">
            <div className="flex items-center gap-2 mb-2">
              <UserCheck className="h-4 w-4 text-teal-500" />
              <span className="text-[11px] font-bold text-slate-500">STP Ready</span>
            </div>
            <div className="text-2xl font-extrabold text-teal-600">{stats.stpReady}</div>
          </div>
        </div>
      )}

      {/* Ranked Vendor List */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-purple-700 px-6 py-4">
          <h2 className="flex items-center gap-2 text-white font-extrabold">
            <TrendingUp className="h-4 w-4" /> Ranked Vendor List
          </h2>
          <p className="text-xs text-blue-100/90 mt-0.5">
            Vendors ranked by 9-factor VIS: Specialty, License, SLA, Cost, Capacity, Rework, Subro, Risk, Concentration
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-200 text-[11px] font-extrabold tracking-wide text-slate-500">
                <th className="px-4 py-3">RANK</th>
                <th className="px-4 py-3">VENDOR NAME</th>
                <th className="px-4 py-3">SPECIALTY</th>
                <th className="px-4 py-3">LICENSE</th>
                <th className="px-4 py-3">RATING</th>
                <th className="px-4 py-3">AVG COST</th>
                <th className="px-4 py-3">ETA</th>
                <th className="px-4 py-3">JOBS</th>
                <th className="px-4 py-3">LOCATION</th>
                <th className="px-4 py-3">VIS SCORE</th>
                <th className="px-4 py-3">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rankedVendors.length === 0 ? (
                <tr>
                  <td colSpan={11} className="px-4 py-12 text-center text-slate-500 text-sm">No vendors found</td>
                </tr>
              ) : (
                rankedVendors.map((v: any, i: number) => (
                  <tr key={v.name} className={i % 2 === 0 ? "bg-amber-50/40" : "bg-white"}>
                    <td className="px-4 py-4">
                      <span className={`inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-extrabold shadow-sm ${rankCircle(i + 1)}`}>
                        {i + 1}
                      </span>
                    </td>
                    <td className="px-4 py-4 min-w-[190px]">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-extrabold text-slate-900 text-sm">{v.name}</span>
                        {v.verified && (
                          <span className="rounded-full bg-violet-100 text-violet-700 px-2 py-0.5 text-[9px] font-bold">STP</span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-500 mt-1">
                        <Phone className="h-3 w-3" /> {v.phone}
                      </div>
                      <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                        <span className="rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 px-2 py-0.5 text-[9px] font-bold">SLA: On Track</span>
                        <span className="rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 px-2 py-0.5 text-[9px] font-bold">
                          Risk: {v.fraudScore >= 0.4 ? "High" : v.fraudScore >= 0.2 ? "Medium" : "Low"}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className="inline-flex rounded-full bg-amber-100/80 text-teal-700 px-3 py-1 text-[10px] font-bold whitespace-nowrap">
                        {v.specialty}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-1.5">
                        {v.licenseValid ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                        ) : (
                          <Clock className="h-4 w-4 text-amber-500" />
                        )}
                        <span className="text-[11px] text-slate-500 font-medium whitespace-nowrap">{v.licenseNumber}</span>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-1">
                        {[1, 2, 3, 4, 5].map((s) => (
                          <Star
                            key={s}
                            className={`h-3 w-3 ${s <= Math.round(v.rating) ? "fill-amber-400 text-amber-400" : "text-slate-200"}`}
                          />
                        ))}
                        <span className="text-xs font-bold text-slate-700 ml-1">{v.rating}</span>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className="inline-flex items-center gap-1 text-sm font-bold text-emerald-600 whitespace-nowrap">
                        <DollarSign className="h-3.5 w-3.5" />{fmt(v.avgCost)}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600 whitespace-nowrap">
                        <Clock className="h-3.5 w-3.5 text-slate-400" /> {v.avgTurnaroundDays}d
                      </span>
                    </td>
                    <td className="px-4 py-4 text-sm font-semibold text-slate-700">{fmt(v.completedJobs)}</td>
                    <td className="px-4 py-4">
                      <span className="inline-flex items-center gap-1 text-xs text-slate-600 whitespace-nowrap">
                        <MapPin className="h-3.5 w-3.5 text-slate-400" /> {v.city}, {v.state}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <span className="inline-flex rounded-full bg-emerald-500 px-3 py-1 text-[11px] font-bold text-white">
                        {v.visScore}%
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <button
                        onClick={() => handleAction(`Assign ${v.name}`)}
                        className="inline-flex rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 px-4 py-2 text-xs font-bold text-white shadow-sm transition-colors"
                      >
                        Assign
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
