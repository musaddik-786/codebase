import { useEffect, useState, useMemo } from "react";
import { useToast } from "@/hooks/use-toast";
import {
  AlertTriangle,
  Ban,
  Car,
  CheckSquare,
  Clock,
  FileText,
  Loader2,
  MapPin,
  Monitor,
  Radar,
  Search,
  Shield,
  UserPlus,
  Users,
} from "lucide-react";

const FILTERS = [
  { key: "All Claims", icon: CheckSquare },
  { key: "High Priority", icon: AlertTriangle },
  { key: "SLA Breached", icon: Clock },
  { key: "Drone Required", icon: Radar },
  { key: "SIU Flagged", icon: Shield },
  { key: "Motor / Auto", icon: Car },
];

export default function ExpertDispatch() {
  const { toast } = useToast();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("All Claims");
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch("/api/adjuster/expert-dispatch")
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load dispatch data (${res.status})`);
        return res.json();
      })
      .then((d) => setData(d))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load dispatch data"))
      .finally(() => setLoading(false));
  }, []);

  const filteredQueue = useMemo(() => {
    let list = [...(data?.queue || [])];
    if (filter === "High Priority")
      list = list.filter((q: any) => ["high", "critical"].includes(String(q.severity).toLowerCase()));
    else if (filter === "SLA Breached") list = list.filter((q: any) => q.slaBreached);
    else if (filter === "Drone Required") list = list.filter((q: any) => q.droneAvailable);
    else if (filter === "SIU Flagged")
      list = list.filter((q: any) => String(q.status).toLowerCase().includes("siu"));
    else if (filter === "Motor / Auto")
      list = list.filter((q: any) => /auto|motor|collision|vehicle/i.test(String(q.lossType)));
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (c: any) =>
          c.claimNumber.toLowerCase().includes(q) ||
          c.policyholder.toLowerCase().includes(q) ||
          c.location.toLowerCase().includes(q)
      );
    }
    return list;
  }, [data, filter, search]);

  const handleAction = (action: string, claimNumber: string) => {
    toast({ title: "Action Recorded", description: `${action} — ${claimNumber}` });
  };

  const severityPill = (severity: string) => {
    const s = severity.toLowerCase();
    if (s.includes("high") || s.includes("critical")) return "bg-red-100 text-red-700";
    if (s.includes("medium")) return "bg-amber-100 text-amber-700";
    return "bg-emerald-100 text-emerald-700";
  };

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-7 py-5 shadow-md">
        <h1 className="text-2xl font-extrabold tracking-tight text-white">Expert Dispatch</h1>
        <p className="mt-0.5 text-sm text-indigo-200/80 font-medium">Assign, schedule, and manage expert site visits</p>
      </div>

      {/* Filter pills */}
      <div className="flex flex-wrap gap-2.5">
        {FILTERS.map(({ key, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-bold transition-colors ${
              filter === key
                ? "bg-blue-600 text-white shadow-sm"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            <Icon className="h-3.5 w-3.5" /> {key}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-violet-600" /></div>
      ) : error ? (
        <div className="bg-red-50 text-red-600 p-4 rounded-xl border border-red-200 font-medium">{error}</div>
      ) : data ? (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 px-6 py-5 shadow-md flex items-center justify-between">
              <div>
                <div className="text-xs font-bold text-blue-100 mb-1">Pending Dispatches</div>
                <div className="text-3xl font-extrabold text-white">{data.stats.pendingDispatches}</div>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/15">
                <Users className="h-5 w-5 text-white" />
              </div>
            </div>
            <div className="rounded-xl bg-gradient-to-br from-red-500 to-rose-600 px-6 py-5 shadow-md flex items-center justify-between">
              <div>
                <div className="text-xs font-bold text-red-100 mb-1">Overdue Visits</div>
                <div className="text-3xl font-extrabold text-white">{data.stats.overdueVisits}</div>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/15">
                <Clock className="h-5 w-5 text-white" />
              </div>
            </div>
            <div className="rounded-xl bg-gradient-to-br from-violet-500 to-purple-700 px-6 py-5 shadow-md flex items-center justify-between">
              <div>
                <div className="text-xs font-bold text-violet-100 mb-1">Drone Combo Requests</div>
                <div className="text-3xl font-extrabold text-white">{data.stats.droneComboRequests}</div>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/15">
                <Radar className="h-5 w-5 text-white" />
              </div>
            </div>
          </div>

          {/* Map + queue */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Dispatch Map */}
            <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden flex flex-col">
              <div className="px-6 py-4 border-b border-slate-100">
                <h2 className="flex items-center gap-2 font-extrabold text-slate-900">
                  <MapPin className="h-4.5 w-4.5 text-blue-600" /> Dispatch Map
                </h2>
              </div>
              <div className="relative flex-1 min-h-[420px] bg-[#e8ecdf] overflow-hidden">
                {/* Stylized map */}
                <div className="absolute inset-0">
                  {/* parks / blocks */}
                  <div className="absolute left-[8%] top-[10%] h-24 w-32 rounded-lg bg-[#cfe3bd]" />
                  <div className="absolute right-[12%] top-[22%] h-28 w-40 rounded-lg bg-[#cfe3bd]" />
                  <div className="absolute left-[20%] bottom-[28%] h-20 w-28 rounded-lg bg-[#cfe3bd]" />
                  <div className="absolute right-[8%] bottom-[18%] h-24 w-24 rounded-lg bg-[#d8e6f3]" />
                  {/* roads */}
                  <div className="absolute left-0 right-0 top-[35%] h-3 bg-white shadow-sm" />
                  <div className="absolute left-0 right-0 top-[68%] h-2.5 bg-white shadow-sm" />
                  <div className="absolute top-0 bottom-0 left-[30%] w-3 bg-white shadow-sm" />
                  <div className="absolute top-0 bottom-0 left-[62%] w-2.5 bg-white shadow-sm" />
                  <div className="absolute left-0 right-0 top-[35%] h-3 flex items-center">
                    <div className="w-full border-t border-dashed border-amber-300" />
                  </div>
                  {/* markers */}
                  {filteredQueue.slice(0, 6).map((c: any, i: number) => (
                    <div
                      key={c.claimNumber}
                      className="absolute"
                      style={{
                        left: `${18 + ((i * 13) % 62)}%`,
                        top: `${16 + ((i * 19) % 52)}%`,
                      }}
                    >
                      <MapPin className="h-7 w-7 text-red-500 drop-shadow" fill="#ef4444" strokeWidth={1.5} stroke="#fff" />
                    </div>
                  ))}
                </div>
                {/* claim chips */}
                <div className="absolute bottom-3 left-3 right-3 flex flex-wrap gap-2">
                  {filteredQueue.slice(0, 6).map((c: any) => (
                    <span
                      key={c.claimNumber}
                      className="inline-flex items-center gap-1 rounded-full bg-white/95 border border-slate-200 px-3 py-1 text-[10px] font-bold text-slate-700 shadow-sm"
                    >
                      <MapPin className="h-3 w-3 text-red-500" /> {c.claimNumber}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Dispatch Queue */}
            <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden flex flex-col">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between gap-3">
                <h2 className="flex items-center gap-2 font-extrabold text-slate-900 whitespace-nowrap">
                  <FileText className="h-4.5 w-4.5 text-indigo-600" /> Dispatch Queue
                </h2>
                <div className="relative w-52">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search claims..."
                    className="w-full rounded-full bg-slate-50 border border-slate-200 pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                </div>
              </div>
              <div className="p-4 space-y-3 overflow-y-auto max-h-[480px]">
                {filteredQueue.length === 0 ? (
                  <p className="text-center text-sm text-slate-500 py-12">No claims match the current filter</p>
                ) : (
                  filteredQueue.map((c: any) => (
                    <div key={c.claimNumber} className="rounded-xl border border-slate-200 px-4 py-3.5 hover:border-blue-200 transition-colors">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="font-extrabold text-blue-600 text-sm">{c.claimNumber}</span>
                        <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${severityPill(c.severity)}`}>
                          {c.severity}
                        </span>
                        {c.slaBreached && (
                          <span className="text-[10px] font-extrabold text-red-500">SLA Breached</span>
                        )}
                      </div>
                      <div className="text-xs font-semibold text-slate-700">{c.policyholder}</div>
                      <div className="flex items-center gap-1 text-[11px] text-slate-500 mt-0.5">
                        <MapPin className="h-3 w-3" /> {c.location}
                      </div>
                      <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                        <span className="rounded-full border border-slate-300 px-2.5 py-0.5 text-[10px] font-bold text-slate-600">
                          {c.lossType}
                        </span>
                        <span className="rounded-full border border-slate-300 px-2.5 py-0.5 text-[10px] font-bold text-slate-600">
                          Recommended: {c.recommendedSpecialty}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2 mt-3">
                        <button
                          onClick={() => handleAction("Assign Expert", c.claimNumber)}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 px-3.5 py-1.5 text-[11px] font-bold text-white shadow-sm transition-colors"
                        >
                          <UserPlus className="h-3 w-3" /> Assign Expert
                        </button>
                        <button
                          onClick={() => handleAction("Virtual First", c.claimNumber)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-3.5 py-1.5 text-[11px] font-bold text-slate-700 transition-colors"
                        >
                          <Monitor className="h-3 w-3" /> Virtual First
                        </button>
                        <button
                          onClick={() => handleAction("Drone Sweep", c.claimNumber)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-3.5 py-1.5 text-[11px] font-bold text-slate-700 transition-colors"
                        >
                          <Radar className="h-3 w-3" /> Drone Sweep
                        </button>
                        <button
                          onClick={() => handleAction("No Visit Needed", c.claimNumber)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-3.5 py-1.5 text-[11px] font-bold text-slate-700 transition-colors"
                        >
                          <Ban className="h-3 w-3" /> No Visit Needed
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
