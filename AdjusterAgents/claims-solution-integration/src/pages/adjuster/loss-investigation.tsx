import { useEffect, useState, useMemo } from "react";
import {
  AlertTriangle,
  Briefcase,
  ChevronRight,
  Clock,
  Filter,
  Loader2,
  Search,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import CaseInvestigation from "@/pages/adjuster/case-investigation";

interface QueueData {
  stats: {
    activeCases: number;
    pendingDocs: number;
    siuReviews: number;
  };
  claims: Array<{
    claimNumber: string;
    policyholder: string;
    lossType: string;
    severity: string;
    complexity: string;
    status: string;
    approvalMode: string;
    routing: string;
    filed: string;
    description: string;
    location: string;
  }>;
}

function severityPill(severity: string): string {
  const s = severity.toLowerCase();
  if (s.includes("high") || s.includes("critical") || s.includes("severe")) return "bg-rose-500";
  if (s.includes("medium") || s.includes("moderate")) return "bg-amber-500";
  return "bg-emerald-500";
}

function statusPill(status: string): string {
  const s = status.toLowerCase();
  if (s.includes("approved") || s.includes("payment") || s.includes("closed") || s.includes("settled"))
    return "bg-emerald-500";
  if (s.includes("reject") || s.includes("denied")) return "bg-rose-500";
  return "bg-sky-500";
}

export default function LossInvestigation() {
  const [openCase, setOpenCase] = useState<string | null>(null);
  const [data, setData] = useState<QueueData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [lossTypeFilter, setLossTypeFilter] = useState("all");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/adjuster/investigation-queue");
        const json = await res.json().catch(() => null);
        if (!res.ok) throw new Error(json?.error || "Could not load investigation queue.");
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load investigation queue.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const filteredClaims = useMemo(() => {
    if (!data) return [];
    return data.claims.filter(c => {
      const matchSearch = c.claimNumber.toLowerCase().includes(search.toLowerCase()) ||
                          c.policyholder.toLowerCase().includes(search.toLowerCase());
      const matchStatus = statusFilter === "all" || c.status === statusFilter;
      const matchSeverity = severityFilter === "all" || c.severity === severityFilter;
      const matchLossType = lossTypeFilter === "all" || c.lossType === lossTypeFilter;
      return matchSearch && matchStatus && matchSeverity && matchLossType;
    });
  }, [data, search, statusFilter, severityFilter, lossTypeFilter]);

  const uniqueStatuses = useMemo(() => Array.from(new Set(data?.claims.map(c => c.status) || [])), [data]);
  const uniqueSeverities = useMemo(() => Array.from(new Set(data?.claims.map(c => c.severity) || [])), [data]);
  const uniqueLossTypes = useMemo(() => Array.from(new Set(data?.claims.map(c => c.lossType) || [])), [data]);

  if (openCase) {
    return <CaseInvestigation claimNumber={openCase} onBack={() => setOpenCase(null)} />;
  }

  return (
    <div className="animate-in fade-in duration-500 pb-12">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-7 py-6 shadow-md mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">Loss Adjustment Investigation</h1>
          <p className="mt-1 text-sm text-indigo-200/80 font-medium">Review and investigate insurance claims with AI-powered tools</p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs font-bold text-white">
            <Briefcase className="h-3.5 w-3.5" /> Active Cases ({data?.stats.activeCases ?? "—"})
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs font-bold text-amber-300">
            <Clock className="h-3.5 w-3.5" /> Pending Docs ({data?.stats.pendingDocs ?? "—"})
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs font-bold text-violet-200">
            <AlertTriangle className="h-3.5 w-3.5" /> SIU Reviews ({data?.stats.siuReviews ?? "—"})
          </span>
        </div>
      </div>

      {/* Investigation Queue card */}
      <div className="rounded-xl overflow-hidden shadow-md border border-slate-200 bg-white">
        <div className="bg-gradient-to-r from-slate-950 via-violet-950 to-violet-800 px-6 py-4">
          <h2 className="flex items-center gap-2 text-white font-extrabold text-lg">
            <Search className="h-4.5 w-4.5" /> Investigation Queue
          </h2>
          <p className="mt-0.5 text-xs text-violet-200/80">Select a case to open the detailed investigation panel</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-24 text-slate-500 gap-3">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="font-medium">Loading queue...</span>
          </div>
        ) : error || !data ? (
          <div className="m-6 rounded-xl border border-red-200 bg-red-50 p-8 text-center text-red-700 font-medium">
            {error || "Failed to load data"}
          </div>
        ) : (
          <div className="p-6">
            <div className="flex items-center gap-2 text-slate-700 font-bold text-sm mb-4">
              <Filter className="h-4 w-4" /> Filter &amp; Prioritize Claims
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Search claim # or policyholder..."
                  className="pl-9 h-10 rounded-full bg-white border-slate-200 font-medium text-sm"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="h-10 rounded-full bg-white border-slate-200 font-semibold text-sm">
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  {uniqueStatuses.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={severityFilter} onValueChange={setSeverityFilter}>
                <SelectTrigger className="h-10 rounded-full bg-white border-slate-200 font-semibold text-sm">
                  <SelectValue placeholder="All Severities" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Severities</SelectItem>
                  {uniqueSeverities.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={lossTypeFilter} onValueChange={setLossTypeFilter}>
                <SelectTrigger className="h-10 rounded-full bg-white border-slate-200 font-semibold text-sm">
                  <SelectValue placeholder="All Loss Types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Loss Types</SelectItem>
                  {uniqueLossTypes.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <p className="text-sm text-slate-500 mb-4">
              Showing <span className="font-bold text-slate-800">{filteredClaims.length}</span> of{" "}
              <span className="font-bold text-slate-800">{data.claims.length}</span> claims
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="px-4 py-3 text-sm font-bold text-slate-600">Claim #</th>
                    <th className="px-4 py-3 text-sm font-bold text-slate-600">Policyholder</th>
                    <th className="px-4 py-3 text-sm font-bold text-slate-600">Loss Type</th>
                    <th className="px-4 py-3 text-sm font-bold text-slate-600">Severity</th>
                    <th className="px-4 py-3 text-sm font-bold text-slate-600">Complexity</th>
                    <th className="px-4 py-3 text-sm font-bold text-slate-600">Status</th>
                    <th className="px-4 py-3 text-sm font-bold text-slate-600">Approval Mode</th>
                    <th className="px-4 py-3 text-sm font-bold text-slate-600">Filed</th>
                    <th className="px-4 py-3 text-sm font-bold text-slate-600">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredClaims.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-4 py-12 text-center text-slate-500 font-medium">
                        No claims found
                      </td>
                    </tr>
                  ) : (
                    filteredClaims.map((claim, i) => (
                      <tr
                        key={i}
                        onClick={() => setOpenCase(claim.claimNumber)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            setOpenCase(claim.claimNumber);
                          }
                        }}
                        tabIndex={0}
                        role="button"
                        aria-label={`Open case ${claim.claimNumber}`}
                        className="hover:bg-slate-50 transition-colors cursor-pointer focus:outline-none focus-visible:bg-slate-50"
                      >
                        <td className="px-4 py-4 font-bold text-slate-900 text-sm max-w-[160px] break-words">{claim.claimNumber}</td>
                        <td className="px-4 py-4 text-sm text-slate-800">{claim.policyholder}</td>
                        <td className="px-4 py-4 text-sm text-slate-800">{claim.lossType}</td>
                        <td className="px-4 py-4">
                          <span className={`inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white ${severityPill(claim.severity)}`}>
                            {claim.severity}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <span className="inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white bg-teal-500">
                            {claim.complexity}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <span className={`inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white whitespace-nowrap ${statusPill(claim.status)}`}>
                            {claim.status}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <span className="inline-flex rounded-full border border-slate-300 px-3 py-1 text-[11px] font-bold text-slate-500 whitespace-nowrap">
                            {claim.approvalMode}
                          </span>
                        </td>
                        <td className="px-4 py-4 text-sm text-slate-700 whitespace-nowrap">{claim.filed}</td>
                        <td className="px-4 py-4">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setOpenCase(claim.claimNumber);
                            }}
                            className="inline-flex items-center gap-1 rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 px-4 py-2 text-xs font-bold text-white shadow-sm transition-colors whitespace-nowrap"
                          >
                            Open Case <ChevronRight className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
