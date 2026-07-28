import { useMemo, useState } from "react";
import { Users, CheckCircle2, Star, Search, Eye, Ban, AlertTriangle, X, Zap, Clock } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { vendors as seedVendors, Vendor } from "@/lib/vendor-data";

const filterPills = ["All", "Active", "Inactive", "Under Review", "Suspended"] as const;

function StarRating({ rating }: { rating: number | null }) {
  if (rating == null) return <span className="text-xs text-slate-400 font-medium">N/A</span>;
  return (
    <span className="inline-flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <Star key={s} className={`h-3.5 w-3.5 ${s <= Math.round(rating) ? "fill-amber-400 text-amber-400" : "text-slate-300"}`} />
      ))}
      <span className="ml-1 text-xs font-bold text-slate-600">{rating.toFixed(1)}</span>
    </span>
  );
}

function statusBadge(status: string) {
  if (status === "Active") return "bg-emerald-600 text-white";
  if (status === "Inactive") return "bg-slate-400 text-white";
  if (status === "Under Review") return "bg-amber-500 text-white";
  return "bg-red-500 text-white";
}

const deactivationReasons = [
  "Poor SLA performance",
  "High cost variance",
  "Fraud suspicion",
  "Compliance issue",
  "Manager Decision",
];

export default function VendorDirectory() {
  const { toast } = useToast();
  const [vendors, setVendors] = useState<Vendor[]>(seedVendors);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<(typeof filterPills)[number]>("All");
  const [viewVendor, setViewVendor] = useState<Vendor | null>(null);
  const [deactivateVendor, setDeactivateVendor] = useState<Vendor | null>(null);
  const [selectedReasons, setSelectedReasons] = useState<string[]>([]);

  const filtered = useMemo(() => {
    let list = vendors;
    if (filter !== "All") list = list.filter((v) => v.status === filter);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (v) =>
          v.name.toLowerCase().includes(q) ||
          v.specialty.toLowerCase().includes(q) ||
          v.location.toLowerCase().includes(q)
      );
    }
    return list;
  }, [vendors, filter, search]);

  const activeCount = vendors.filter((v) => v.status === "Active").length;
  const rated = vendors.filter((v) => v.rating != null);
  const avgRating = rated.length ? rated.reduce((s, v) => s + (v.rating || 0), 0) / rated.length : 0;

  const doDeactivate = (mode: string) => {
    if (!deactivateVendor) return;
    setVendors((prev) =>
      prev.map((v) =>
        v.id === deactivateVendor.id ? { ...v, status: "Inactive" as const, assignmentEligible: false } : v
      )
    );
    toast({
      title: "Vendor Deactivated",
      description: `${deactivateVendor.name} — ${mode}${selectedReasons.length ? ` (${selectedReasons.join(", ")})` : ""}`,
    });
    setDeactivateVendor(null);
    setSelectedReasons([]);
  };

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-8 py-7 shadow-md">
        <h1 className="text-3xl font-extrabold tracking-tight text-white">Vendor Directory</h1>
        <p className="mt-1 text-sm text-indigo-200/80 font-medium">Browse and manage vendor partners across all specialties</p>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-slate-900 to-slate-800">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Total Vendors</span>
            <Users className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">{vendors.length + 12}</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-emerald-600 to-green-700">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Active Vendors</span>
            <CheckCircle2 className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">{activeCount + 12}</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-orange-500 to-red-600">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Average Rating</span>
            <Star className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold flex items-center gap-2">
            {avgRating.toFixed(1)}
            <span className="inline-flex items-center gap-0.5">
              {[1, 2, 3, 4, 5].map((s) => (
                <Star key={s} className={`h-3.5 w-3.5 ${s <= Math.round(avgRating) ? "fill-white text-white" : "text-white/40"}`} />
              ))}
            </span>
          </div>
        </div>
      </div>

      {/* Search + filter pills */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm px-4 py-3 flex flex-col md:flex-row md:items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, specialty, or location..."
            className="w-full rounded-full bg-slate-50 border border-slate-200 pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap md:ml-auto">
          {filterPills.map((p) => (
            <button
              key={p}
              onClick={() => setFilter(p)}
              className={`rounded-full px-4 py-1.5 text-xs font-bold border transition-colors ${
                filter === p
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Vendor table */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gradient-to-r from-indigo-950 via-violet-950 to-purple-900 text-white text-xs font-bold">
                <th className="px-4 py-3">Vendor ID</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Specialty</th>
                <th className="px-4 py-3">Location</th>
                <th className="px-4 py-3">License Expiry</th>
                <th className="px-4 py-3">Rating</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Assignment Eligible</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-sm text-slate-500">No vendors found</td>
                </tr>
              ) : (
                filtered.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-50/60">
                    <td className="px-4 py-3.5 text-xs font-semibold text-slate-600 whitespace-nowrap">{v.id}</td>
                    <td className="px-4 py-3.5 text-sm font-bold text-slate-900 min-w-[160px]">{v.name}</td>
                    <td className="px-4 py-3.5 text-xs font-medium text-slate-700">{v.specialty}</td>
                    <td className="px-4 py-3.5 text-xs font-medium text-slate-700">{v.location}</td>
                    <td className="px-4 py-3.5 text-xs font-medium text-slate-700 whitespace-nowrap">{v.licenseExpiry}</td>
                    <td className="px-4 py-3.5 whitespace-nowrap"><StarRating rating={v.rating} /></td>
                    <td className="px-4 py-3.5">
                      <span className={`rounded-full px-3 py-1 text-[10px] font-bold ${statusBadge(v.status)}`}>{v.status}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`rounded-full px-3 py-1 text-[10px] font-bold ${v.assignmentEligible ? "bg-emerald-600 text-white" : "bg-red-500 text-white"}`}>
                        {v.assignmentEligible ? "Yes" : "No"}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center justify-end gap-2 whitespace-nowrap">
                        <button
                          onClick={() => setViewVendor(v)}
                          className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-700 hover:text-slate-900"
                        >
                          <Eye className="h-3.5 w-3.5" /> View
                        </button>
                        {v.status === "Active" && (
                          <button
                            onClick={() => {
                              setDeactivateVendor(v);
                              setSelectedReasons([]);
                            }}
                            className="inline-flex items-center gap-1.5 rounded-full bg-red-600 hover:bg-red-700 text-white px-3.5 py-1.5 text-[11px] font-bold transition-colors"
                          >
                            <Ban className="h-3 w-3" /> Deactivate
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* View detail popup */}
      <Dialog open={!!viewVendor} onOpenChange={(o) => !o && setViewVendor(null)}>
        <DialogContent className="max-w-lg p-6">
          {viewVendor && (
            <>
              <DialogTitle className="text-lg font-extrabold text-slate-900 mb-4">{viewVendor.name}</DialogTitle>
              <div className="grid grid-cols-2 gap-x-8 gap-y-5">
                <div>
                  <div className="text-[10px] font-extrabold tracking-wider text-slate-400 uppercase mb-1">Vendor ID</div>
                  <div className="text-sm font-semibold text-slate-900">{viewVendor.id}</div>
                </div>
                <div>
                  <div className="text-[10px] font-extrabold tracking-wider text-slate-400 uppercase mb-1">Status</div>
                  <span className={`rounded-full px-3 py-1 text-[10px] font-bold ${statusBadge(viewVendor.status)}`}>{viewVendor.status}</span>
                </div>
                <div>
                  <div className="text-[10px] font-extrabold tracking-wider text-slate-400 uppercase mb-1">Specialty</div>
                  <div className="text-sm font-semibold text-slate-900">{viewVendor.specialty}</div>
                </div>
                <div>
                  <div className="text-[10px] font-extrabold tracking-wider text-slate-400 uppercase mb-1">Location</div>
                  <div className="text-sm font-semibold text-slate-900">{viewVendor.location}</div>
                </div>
                <div>
                  <div className="text-[10px] font-extrabold tracking-wider text-slate-400 uppercase mb-1">Assignment Eligible</div>
                  <span className={`rounded-full px-3 py-1 text-[10px] font-bold ${viewVendor.assignmentEligible ? "bg-emerald-600 text-white" : "bg-red-500 text-white"}`}>
                    {viewVendor.assignmentEligible ? "Yes" : "No"}
                  </span>
                </div>
                <div>
                  <div className="text-[10px] font-extrabold tracking-wider text-slate-400 uppercase mb-1">License Number</div>
                  <div className="text-sm font-semibold text-slate-900">{viewVendor.licenseNumber}</div>
                </div>
                <div>
                  <div className="text-[10px] font-extrabold tracking-wider text-slate-400 uppercase mb-1">License Expiry Date</div>
                  <div className="text-sm font-semibold text-slate-900">{viewVendor.licenseExpiry}</div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Deactivate dialog */}
      <Dialog open={!!deactivateVendor} onOpenChange={(o) => !o && setDeactivateVendor(null)}>
        <DialogContent className="max-w-md p-6">
          {deactivateVendor && (
            <>
              <DialogTitle className="flex items-center gap-2 text-base font-extrabold text-red-700 mb-3">
                <AlertTriangle className="h-4 w-4 text-red-500" /> Deactivate Vendor: {deactivateVendor.name}?
              </DialogTitle>
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 mb-4">
                <div className="text-xs font-extrabold text-red-700 mb-1.5">Impact:</div>
                <ul className="space-y-1 text-[11px] font-semibold text-red-600">
                  <li className="flex items-center gap-1.5"><Ban className="h-3 w-3" /> Vendor will NOT receive new assignments</li>
                  <li className="flex items-center gap-1.5"><AlertTriangle className="h-3 w-3" /> Existing claims will continue OR need reassignment</li>
                  <li className="flex items-center gap-1.5"><Clock className="h-3 w-3" /> Vendor score will be frozen</li>
                </ul>
              </div>
              <div className="mb-1 text-sm font-bold text-slate-900">
                Reason for Deactivation <span className="text-red-500">*</span>
              </div>
              <div className="text-[11px] text-amber-600 font-semibold mb-3">Select one or more reasons</div>
              <div className="space-y-2 mb-5">
                {deactivationReasons.map((r) => {
                  const checked = selectedReasons.includes(r);
                  return (
                    <button
                      key={r}
                      type="button"
                      onClick={() =>
                        setSelectedReasons((prev) => (checked ? prev.filter((x) => x !== r) : [...prev, r]))
                      }
                      className={`w-full flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm text-left transition-colors ${
                        checked ? "border-blue-400 bg-blue-50" : "border-slate-200 bg-white hover:bg-slate-50"
                      }`}
                    >
                      <span className={`h-4 w-4 rounded-full border-2 flex items-center justify-center ${checked ? "border-blue-500" : "border-slate-300"}`}>
                        {checked && <span className="h-2 w-2 rounded-full bg-blue-500" />}
                      </span>
                      <span className="font-medium text-slate-800">{r}</span>
                    </button>
                  );
                })}
              </div>
              <div className="space-y-2.5">
                <button
                  onClick={() => doDeactivate("Deactivated Immediately")}
                  disabled={selectedReasons.length === 0}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-red-400 to-rose-400 hover:from-red-500 hover:to-rose-500 disabled:opacity-60 px-4 py-2.5 text-sm font-bold text-white transition-colors"
                >
                  <Zap className="h-4 w-4" /> Deactivate Immediately
                </button>
                <button
                  onClick={() => doDeactivate("Deactivate After Active Jobs Complete")}
                  disabled={selectedReasons.length === 0}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-indigo-400 to-blue-400 hover:from-indigo-500 hover:to-blue-500 disabled:opacity-60 px-4 py-2.5 text-sm font-bold text-white transition-colors"
                >
                  <Clock className="h-4 w-4" /> Deactivate After Active Jobs Complete
                </button>
                <button
                  onClick={() => setDeactivateVendor(null)}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-4 py-2.5 text-sm font-bold text-slate-700 transition-colors"
                >
                  <X className="h-4 w-4" /> Cancel
                </button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
