import { useMemo, useState } from "react";
import { ClipboardList, Clock, CheckCircle2, AlertTriangle, UserCheck, Search, RefreshCw, BarChart3, X, FileText, PenLine, Bell, Send } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { assignments as seedAssignments, workloadDistribution, vendors, Assignment } from "@/lib/vendor-data";

const statusBadge: Record<string, string> = {
  Reassigned: "border border-slate-300 text-slate-400 bg-white",
  Assigned: "border border-amber-300 bg-amber-50 text-amber-600",
  "Pending Review": "border border-orange-300 bg-orange-50 text-orange-600",
  Completed: "bg-emerald-700 text-white",
  "In Progress": "bg-blue-600 text-white",
};

const statusFilters = ["All", "Assigned", "In Progress", "Pending Review", "Completed", "Reassigned"];

export default function VendorAssignmentMonitor() {
  const { toast } = useToast();
  const [rows, setRows] = useState<Assignment[]>(seedAssignments);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [reassignRow, setReassignRow] = useState<Assignment | null>(null);
  const [newVendor, setNewVendor] = useState("");
  const [escalateRow, setEscalateRow] = useState<Assignment | null>(null);
  const [editingMessage, setEditingMessage] = useState(false);
  const [escalationMessage, setEscalationMessage] = useState("");
  const [escalationActions, setEscalationActions] = useState<Record<string, boolean>>({});

  const openEscalate = (r: Assignment) => {
    setEscalateRow(r);
    setEditingMessage(false);
    setEscalationMessage(
      `We have observed a delay in the assigned repair work for Claim ${r.claimId}. The job has exceeded the expected SLA timeline. Please provide an immediate update and revised completion timeline.`
    );
    setEscalationActions({
      "Notify Vendor": true,
      "Notify Adjuster": false,
      "Notify Vendor Supervisor": false,
      "Mark as High Priority": true,
    });
  };

  const sendEscalation = () => {
    if (!escalateRow) return;
    toast({
      title: "Escalation Sent",
      description: `Escalation notification sent to ${escalateRow.vendor} for ${escalateRow.claimId}.`,
    });
    setEscalateRow(null);
  };

  const availableVendors = useMemo(
    () => vendors.filter((v) => v.status === "Active" && v.assignmentEligible).map((v) => v.name),
    []
  );

  const filtered = useMemo(() => {
    let list = rows;
    if (statusFilter !== "All") list = list.filter((r) => r.status === statusFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((r) => r.claimId.toLowerCase().includes(q) || r.vendor.toLowerCase().includes(q));
    }
    return list;
  }, [rows, statusFilter, search]);

  const counts = {
    total: 62,
    inProgress: 11,
    completed: 15,
    pendingReview: 15,
    assigned: 17,
  };

  const confirmReassign = () => {
    if (!reassignRow || !newVendor) return;
    setRows((prev) =>
      prev.flatMap((r) => {
        if (r === reassignRow) {
          return [
            { ...r, status: "Reassigned" as const, slaStatus: "Reassigned" as const },
            { ...r, vendor: newVendor, status: "Assigned" as const, slaStatus: null },
          ];
        }
        return [r];
      })
    );
    toast({
      title: "Vendor Reassigned",
      description: `${reassignRow.claimId} reassigned to ${newVendor}.`,
    });
    setReassignRow(null);
    setNewVendor("");
  };

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-8 py-7 shadow-md">
        <h1 className="text-3xl font-extrabold tracking-tight text-white">Vendor Assignment Monitor</h1>
        <p className="mt-1 text-sm text-indigo-200/80 font-medium">Track vendor assignments, workload distribution, and SLA compliance</p>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-slate-900 to-slate-800">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Total Assignments</span>
            <ClipboardList className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">{counts.total}</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-blue-800 to-indigo-900">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">In Progress</span>
            <Clock className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">{counts.inProgress}</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-emerald-600 to-green-700">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Completed</span>
            <CheckCircle2 className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">{counts.completed}</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-orange-500 to-red-600">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Pending Review</span>
            <AlertTriangle className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">{counts.pendingReview}</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-violet-600 to-purple-700">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Assigned</span>
            <UserCheck className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">{counts.assigned}</div>
        </div>
      </div>

      {/* Search + filter */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm px-4 py-3 flex flex-col md:flex-row items-stretch md:items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Claim ID or Vendor Name..."
            className="w-full rounded-lg bg-slate-50 border border-slate-200 pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-full md:w-40 rounded-lg border-slate-200 text-sm h-10 font-semibold">
            <SelectValue placeholder="All" />
          </SelectTrigger>
          <SelectContent>
            {statusFilters.map((s) => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Assignment details table */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-violet-600 to-blue-600">
          <ClipboardList className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Assignment Details ({counts.total})</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gradient-to-r from-indigo-950 to-violet-950 text-white text-xs font-bold">
                <th className="px-4 py-3">Claim ID</th>
                <th className="px-4 py-3">Vendor</th>
                <th className="px-4 py-3">Specialty</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Assigned Date</th>
                <th className="px-4 py-3">Completion Date</th>
                <th className="px-4 py-3">SLA Status</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((r, i) => {
                const reassigned = r.status === "Reassigned";
                const completed = r.status === "Completed";
                const canReassign = !reassigned && !completed;
                return (
                  <tr key={`${r.claimId}-${r.vendor}-${i}`} className={reassigned ? "text-slate-400" : ""}>
                    <td className={`px-4 py-3.5 text-sm font-semibold whitespace-nowrap ${reassigned ? "line-through" : "text-slate-800"}`}>{r.claimId}</td>
                    <td className={`px-4 py-3.5 text-sm font-medium whitespace-nowrap ${reassigned ? "line-through" : "text-slate-700"}`}>{r.vendor}</td>
                    <td className={`px-4 py-3.5 text-sm ${reassigned ? "line-through" : "text-slate-600"}`}>{r.specialty}</td>
                    <td className="px-4 py-3.5">
                      <span className={`rounded-full px-3 py-1 text-[10px] font-bold whitespace-nowrap ${statusBadge[r.status]}`}>{r.status}</span>
                    </td>
                    <td className={`px-4 py-3.5 text-sm whitespace-nowrap ${reassigned ? "line-through" : "text-slate-600"}`}>{r.assignedDate}</td>
                    <td className="px-4 py-3.5 text-sm text-slate-600 whitespace-nowrap">{r.completionDate ?? "—"}</td>
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      {r.slaStatus === "At Risk" ? (
                        <span className="rounded-md bg-red-800 text-white px-2.5 py-1 text-[10px] font-bold">At Risk</span>
                      ) : r.slaStatus === "Reassigned" ? (
                        <span className="text-xs italic text-slate-400">Reassigned</span>
                      ) : (
                        <span className="text-sm text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      {reassigned ? (
                        <span className="text-xs italic text-slate-400">No actions</span>
                      ) : (
                        <button
                          onClick={() => canReassign && setReassignRow(r)}
                          disabled={!canReassign}
                          className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-[11px] font-bold transition-colors ${
                            canReassign
                              ? "bg-gradient-to-r from-blue-700 to-indigo-800 hover:from-blue-800 hover:to-indigo-900 text-white"
                              : "bg-slate-100 text-slate-400 cursor-not-allowed"
                          }`}
                        >
                          <RefreshCw className="h-3 w-3" /> Reassign
                        </button>
                      )}
                      {!reassigned && r.status === "In Progress" && r.slaStatus === "At Risk" && (
                        <button
                          onClick={() => openEscalate(r)}
                          className="ml-2 inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-[11px] font-bold bg-gradient-to-r from-red-700 to-red-800 hover:from-red-800 hover:to-red-900 text-white transition-colors"
                        >
                          <AlertTriangle className="h-3 w-3" /> Escalate
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Workload distribution */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-emerald-600 to-cyan-600">
          <BarChart3 className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Vendor Workload Distribution</h2>
        </div>
        <div className="p-5 space-y-3">
          {workloadDistribution.map((w) => {
            const moderate = w.level === "Moderate";
            return (
              <div
                key={w.name}
                className={`rounded-xl px-4 py-3 ${moderate ? "bg-amber-50/70" : "bg-emerald-50/60"}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold text-slate-800">{w.name}</span>
                  <span className="flex items-center gap-3">
                    <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${moderate ? "bg-white text-amber-600 border border-amber-200" : "bg-white text-emerald-600 border border-emerald-200"}`}>
                      {w.level}
                    </span>
                    <span className="text-xs font-extrabold text-slate-900">{w.jobs} jobs</span>
                  </span>
                </div>
                <div className="w-full h-2.5 rounded-full bg-white overflow-hidden">
                  <div
                    className={`h-full rounded-full ${moderate ? "bg-amber-400" : "bg-emerald-500"}`}
                    style={{ width: `${Math.max((w.jobs / 4) * 100, 4)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Reassign dialog */}
      <Dialog open={!!reassignRow} onOpenChange={(o) => { if (!o) { setReassignRow(null); setNewVendor(""); } }}>
        <DialogContent className="max-w-md p-6">
          {reassignRow && (
            <>
              <DialogTitle className="text-base font-extrabold text-slate-900 mb-1">Reassign Vendor</DialogTitle>
              <p className="text-xs text-slate-500 mb-4">Select a new vendor for claim {reassignRow.claimId}</p>
              <Select value={newVendor} onValueChange={setNewVendor}>
                <SelectTrigger className="w-full rounded-lg border-blue-300 text-sm h-10 mb-5">
                  <SelectValue placeholder="Select a vendor..." />
                </SelectTrigger>
                <SelectContent>
                  {availableVendors
                    .filter((v) => v !== reassignRow.vendor)
                    .map((v) => (
                      <SelectItem key={v} value={v}>{v}</SelectItem>
                    ))}
                </SelectContent>
              </Select>
              <div className="flex items-center justify-end gap-2.5">
                <button
                  onClick={() => { setReassignRow(null); setNewVendor(""); }}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-4 py-2 text-sm font-bold text-slate-700 transition-colors"
                >
                  <X className="h-3.5 w-3.5" /> Cancel
                </button>
                <button
                  onClick={confirmReassign}
                  disabled={!newVendor}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 px-4 py-2 text-sm font-bold text-white transition-colors"
                >
                  Confirm Reassignment
                </button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Escalate dialog */}
      <Dialog open={!!escalateRow} onOpenChange={(o) => { if (!o) setEscalateRow(null); }}>
        <DialogContent className="max-w-lg p-6 max-h-[90vh] overflow-y-auto">
          {escalateRow && (
            <>
              <div className="flex items-start gap-3 mb-4">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-red-700 shrink-0">
                  <FileText className="h-4 w-4 text-white" />
                </span>
                <div>
                  <DialogTitle className="text-base font-extrabold text-slate-900">Escalate Vendor Delay / Issue</DialogTitle>
                  <p className="text-xs text-slate-500 mt-0.5">Review details and send escalation notification</p>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 mb-4">
                <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-indigo-600 mb-3">
                  <ClipboardList className="h-3.5 w-3.5" /> Issue Summary
                </div>
                <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Claim ID</div>
                    <div className="mt-0.5 text-sm font-extrabold text-slate-900">{escalateRow.claimId}</div>
                  </div>
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Vendor Name</div>
                    <div className="mt-0.5 text-sm font-extrabold text-slate-900">{escalateRow.vendor}</div>
                  </div>
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Job Status</div>
                    <span className="mt-1 inline-flex rounded-full border border-blue-300 bg-blue-50 px-2.5 py-0.5 text-[10px] font-bold text-blue-600">
                      {escalateRow.status}
                    </span>
                  </div>
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">SLA Status</div>
                    <span className="mt-1 inline-flex rounded-full bg-amber-400 px-2.5 py-0.5 text-[10px] font-bold text-amber-900">
                      {escalateRow.slaStatus}
                    </span>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 mb-4">
                <div className="flex items-center justify-between mb-2.5">
                  <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-600">
                    <PenLine className="h-3.5 w-3.5" /> AI-Drafted Message
                  </div>
                  <button
                    onClick={() => setEditingMessage((e) => !e)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1 text-[11px] font-bold text-slate-700 hover:bg-slate-50"
                  >
                    <PenLine className="h-3 w-3" /> {editingMessage ? "Done Editing" : "Edit Message"}
                  </button>
                </div>
                {editingMessage ? (
                  <textarea
                    value={escalationMessage}
                    onChange={(e) => setEscalationMessage(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 bg-white p-3 text-xs font-medium text-slate-700 h-24 resize-none focus:outline-none focus:ring-2 focus:ring-red-200"
                  />
                ) : (
                  <div className="rounded-lg border border-amber-100 bg-amber-50/50 px-4 py-3 text-xs italic font-medium text-slate-600 leading-relaxed">
                    {escalationMessage}
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-slate-200 p-4 mb-5">
                <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-600 mb-3">
                  <Bell className="h-3.5 w-3.5" /> Escalation Actions
                </div>
                <div className="space-y-2.5">
                  {Object.entries(escalationActions).map(([label, checked]) => (
                    <label key={label} className="flex items-center gap-2.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => setEscalationActions((a) => ({ ...a, [label]: !a[label] }))}
                        className="h-4 w-4 rounded-full accent-blue-600"
                      />
                      <span className="text-xs font-bold text-slate-700">{label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2.5">
                <button
                  onClick={() => setEscalateRow(null)}
                  className="rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-4 py-2 text-sm font-bold text-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={sendEscalation}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-red-700 to-red-800 hover:from-red-800 hover:to-red-900 px-4 py-2 text-sm font-bold text-white transition-colors"
                >
                  <Send className="h-3.5 w-3.5" /> Send Escalation
                </button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
