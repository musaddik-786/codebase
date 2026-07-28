import { Clock, Timer, ShieldCheck, AlertTriangle, ArrowUpDown, BarChart3, AlertCircle, Bell, Trophy, Send } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const slaMetrics = [
  { name: "SummitView Construction", specialty: "Roofing", response: "4 hrs", completion: "10 days", compliance: 98 },
  { name: "AquaPure Water Services", specialty: "Water", response: "3 hrs", completion: "7 days", compliance: 97 },
  { name: "BrightSpark Electric", specialty: "Electrical", response: "2 hrs", completion: "5 days", compliance: 96 },
  { name: "SteelFrame Structural", specialty: "Structural", response: "1 hr", completion: "4 days", compliance: 94 },
  { name: "QuickFix Handyman", specialty: "General", response: "24 hrs", completion: "3 days", compliance: 93 },
  { name: "TrueNorth Roofing", specialty: "Roofing", response: "12 hrs", completion: "2 days", compliance: 91 },
  { name: "AllStar Maintenance", specialty: "General", response: "8 hrs", completion: "14 days", compliance: 90 },
  { name: "FireGuard Systems", specialty: "Fire", response: "6 hrs", completion: "10 days", compliance: 88 },
  { name: "FloodStop Remediation", specialty: "Water", response: "4 hrs", completion: "7 days", compliance: 87 },
  { name: "PrimeCraft Builders", specialty: "Structural", response: "3 hrs", completion: "5 days", compliance: 85 },
  { name: "SafeHaven Security", specialty: "Security Systems", response: "2 hrs", completion: "4 days", compliance: 84 },
  { name: "GreenTree Landscaping", specialty: "Landscaping", response: "5 hrs", completion: "6 days", compliance: 82 },
  { name: "ElectriFix Solutions", specialty: "Electrical", response: "7 hrs", completion: "8 days", compliance: 81 },
  { name: "RoofMasters Inc", specialty: "Roofing", response: "9 hrs", completion: "9 days", compliance: 79 },
  { name: "AquaShield Plumbing", specialty: "Water", response: "6 hrs", completion: "11 days", compliance: 77 },
  { name: "ClearView Glass", specialty: "Glass/Windows", response: "10 hrs", completion: "12 days", compliance: 76 },
  { name: "ProBuild Contractors", specialty: "Structural", response: "11 hrs", completion: "13 days", compliance: 75 },
  { name: "StormGuard Services", specialty: "Wind", response: "14 hrs", completion: "15 days", compliance: 73 },
  { name: "BlueLine Restoration", specialty: "Water", response: "16 hrs", completion: "16 days", compliance: 72 },
  { name: "Apex Repairs", specialty: "Fire", response: "18 hrs", completion: "18 days", compliance: 70 },
];

const breachAlerts = [
  { name: "Apex Repairs", compliance: 70, below: 10 },
  { name: "BlueLine Restoration", compliance: 72, below: 8 },
  { name: "StormGuard Services", compliance: 73, below: 7 },
  { name: "ProBuild Contractors", compliance: 75, below: 5 },
  { name: "ClearView Glass", compliance: 76, below: 4 },
  { name: "AquaShield Plumbing", compliance: 77, below: 3 },
  { name: "RoofMasters Inc", compliance: 79, below: 1 },
];

const openJobs = [
  { claimId: "CLM-2025-010", vendor: "StormGuard Services", assigned: "16/3/2026", days: 123 },
  { claimId: "CLM-2025-007", vendor: "StormGuard Services", assigned: "1/3/2026", days: 138 },
  { claimId: "CLM-2025-005", vendor: "BlueLine Restoration", assigned: "6/2/2026", days: 161 },
  { claimId: "CLM-2025-010", vendor: "AllStar Maintenance", assigned: "20/3/2026", days: 119 },
  { claimId: "CLM-2025-010", vendor: "ElectriFix Solutions", assigned: "31/3/2026", days: 108 },
  { claimId: "CLM-2025-005", vendor: "AquaPure Water Services", assigned: "1/1/2026", days: 197 },
  { claimId: "CLM-2025-010", vendor: "SummitView Construction", assigned: "11/2/2026", days: 156 },
  { claimId: "CLM-2025-002", vendor: "ClearView Glass", assigned: "20/3/2026", days: 119 },
];

const top5 = slaMetrics.slice(0, 5);
const bottom5 = [...slaMetrics].slice(-5).reverse().map((v, i) => ({ ...v, rank: 20 - i }));

function medal(rank: number) {
  if (rank === 1) return { wrap: "bg-amber-50 border-amber-300", icon: "🏅" };
  if (rank === 2) return { wrap: "bg-slate-50 border-slate-300", icon: "🥈" };
  if (rank === 3) return { wrap: "bg-amber-50 border-amber-300", icon: "🥉" };
  return { wrap: "bg-white border-slate-200", icon: null };
}

function complianceColor(c: number) {
  if (c >= 90) return "bg-emerald-500";
  if (c >= 80) return "bg-amber-400";
  return "bg-red-500";
}

function statusBadge(c: number) {
  if (c >= 90)
    return <span className="inline-flex rounded-full bg-emerald-600 px-2.5 py-0.5 text-[10px] font-bold text-white">Compliant</span>;
  if (c >= 80)
    return <span className="inline-flex rounded-full bg-orange-500 px-2.5 py-0.5 text-[10px] font-bold text-white">At Risk</span>;
  return <span className="inline-flex rounded-full bg-red-600 px-2.5 py-0.5 text-[10px] font-bold text-white">Breached</span>;
}

export default function VendorSlaTracker() {
  const { toast } = useToast();

  const escalate = (vendor: string) => {
    toast({
      title: "Escalation Raised",
      description: `SLA breach for ${vendor} has been escalated to the vendor management team.`,
    });
  };

  const sendReminder = (vendor: string, claimId: string) => {
    toast({
      title: "Reminder Sent",
      description: `A reminder for ${claimId} has been sent to ${vendor}.`,
    });
  };

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-8 py-7 shadow-md">
        <h1 className="text-3xl font-extrabold tracking-tight text-white">Vendor SLA Tracker</h1>
        <p className="mt-1 text-sm text-indigo-200/80 font-medium">Monitor vendor service level agreements, compliance metrics, and escalation triggers</p>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-slate-900 to-slate-800">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Avg Time to Accept</span>
            <Clock className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">4 hrs</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-blue-800 to-indigo-900">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Avg Completion Time</span>
            <Timer className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">5 days</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-emerald-600 to-green-700">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Overall SLA Compliance</span>
            <ShieldCheck className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">84%</div>
        </div>
        <div className="rounded-xl px-5 py-4 text-white shadow-md bg-gradient-to-br from-red-600 to-orange-600">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">Delay Frequency</span>
            <AlertTriangle className="h-4 w-4 opacity-80" />
          </div>
          <div className="text-2xl font-extrabold">7 vendors</div>
        </div>
      </div>

      {/* SLA Metrics by Vendor */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center justify-between bg-gradient-to-r from-violet-600 to-blue-600">
          <span className="flex items-center gap-2.5">
            <BarChart3 className="h-4 w-4 text-white" />
            <h2 className="text-white font-extrabold text-sm">SLA Metrics by Vendor</h2>
          </span>
          <span className="flex items-center gap-1.5 text-[11px] font-bold text-white/80">
            <ArrowUpDown className="h-3.5 w-3.5" /> Best First
          </span>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-900 text-white text-left text-[11px] uppercase tracking-wide">
              <th className="px-5 py-2.5 font-bold">Vendor Name</th>
              <th className="px-5 py-2.5 font-bold">Specialty</th>
              <th className="px-5 py-2.5 font-bold">Avg Response Time</th>
              <th className="px-5 py-2.5 font-bold">Avg Completion Time</th>
              <th className="px-5 py-2.5 font-bold">SLA Compliance %</th>
              <th className="px-5 py-2.5 font-bold">SLA Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {slaMetrics.map((v) => (
              <tr key={v.name} className="hover:bg-slate-50">
                <td className="px-5 py-3 font-bold text-slate-900">{v.name}</td>
                <td className="px-5 py-3 text-slate-600">{v.specialty}</td>
                <td className="px-5 py-3 text-slate-600">{v.response}</td>
                <td className="px-5 py-3 text-slate-600">{v.completion}</td>
                <td className="px-5 py-3">
                  <span className="flex items-center gap-2">
                    <span className="w-20 h-2 rounded-full bg-slate-100 overflow-hidden">
                      <span className={`block h-full rounded-full ${complianceColor(v.compliance)}`} style={{ width: `${v.compliance}%` }} />
                    </span>
                    <span className="text-xs font-extrabold text-slate-800">{v.compliance}%</span>
                  </span>
                </td>
                <td className="px-5 py-3">{statusBadge(v.compliance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* SLA Breach Alerts */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <AlertCircle className="h-4 w-4 text-red-600" />
          <h2 className="text-slate-900 font-extrabold text-sm">SLA Breach Alerts</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {breachAlerts.map((b) => (
            <div key={b.name} className="rounded-xl border-2 border-amber-400 bg-amber-50/40 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-extrabold text-slate-900 text-sm">{b.name}</div>
                  <span className="mt-1 inline-flex rounded-full border border-amber-400 bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                    Warning
                  </span>
                </div>
                <span className="text-2xl font-extrabold text-red-600">{b.compliance}%</span>
              </div>
              <div className="mt-2 text-[11px] font-semibold text-slate-500">{b.below}% below 80% SLA threshold</div>
              <button
                onClick={() => escalate(b.name)}
                className="mt-3 w-full flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-red-800 to-red-700 px-3 py-2 text-[11px] font-bold text-white hover:from-red-700 hover:to-red-600 transition-colors"
              >
                <AlertTriangle className="h-3.5 w-3.5" /> Escalate
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Escalation Triggers — Open Jobs */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-orange-500 to-red-500">
          <Bell className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Escalation Triggers — Open Jobs</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-indigo-950 text-white text-left text-[11px] uppercase tracking-wide">
              <th className="px-5 py-2.5 font-bold">Claim ID</th>
              <th className="px-5 py-2.5 font-bold">Vendor Name</th>
              <th className="px-5 py-2.5 font-bold">Assigned Date</th>
              <th className="px-5 py-2.5 font-bold">Days Since Assignment</th>
              <th className="px-5 py-2.5 font-bold">Status</th>
              <th className="px-5 py-2.5 font-bold">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {openJobs.map((j, i) => (
              <tr key={`${j.claimId}-${j.vendor}-${i}`} className="hover:bg-slate-50">
                <td className="px-5 py-3 text-slate-600 text-xs font-semibold">{j.claimId}</td>
                <td className="px-5 py-3 font-bold text-slate-900">{j.vendor}</td>
                <td className="px-5 py-3 text-slate-600">{j.assigned}</td>
                <td className="px-5 py-3 font-bold text-red-600">{j.days} days</td>
                <td className="px-5 py-3">
                  <span className="inline-flex rounded-full bg-red-800 px-2.5 py-0.5 text-[10px] font-bold text-white">Overdue</span>
                </td>
                <td className="px-5 py-3">
                  <button
                    onClick={() => sendReminder(j.vendor, j.claimId)}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-[11px] font-bold text-white hover:bg-blue-700 transition-colors"
                  >
                    <Send className="h-3 w-3" /> Send Reminder
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Top 5 / Bottom 5 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-emerald-600 to-cyan-600">
            <Trophy className="h-4 w-4 text-white" />
            <h2 className="text-white font-extrabold text-sm">Top 5 — Best SLA Compliance</h2>
          </div>
          <div className="p-4 space-y-3">
            {top5.map((v, i) => {
              const m = medal(i + 1);
              return (
                <div key={v.name} className={`rounded-lg border ${m.wrap} px-4 py-3`}>
                  <div className="flex items-center gap-3">
                    <span className="w-7 text-center text-sm font-extrabold text-slate-600">{m.icon ?? `#${i + 1}`}</span>
                    <div className="flex-1">
                      <div className="text-xs font-extrabold text-slate-900">{v.name}</div>
                      <div className="mt-1.5 flex items-center gap-2">
                        <span className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                          <span className="block h-full rounded-full bg-emerald-500" style={{ width: `${v.compliance}%` }} />
                        </span>
                        <span className="text-[11px] font-extrabold text-slate-700">{v.compliance}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-rose-600 to-pink-600">
            <AlertTriangle className="h-4 w-4 text-white" />
            <h2 className="text-white font-extrabold text-sm">Bottom 5 — Lowest SLA Compliance</h2>
          </div>
          <div className="p-4 space-y-3">
            {bottom5.map((v) => (
              <div key={v.name} className="rounded-lg border border-rose-200 bg-rose-50/40 px-4 py-3">
                <div className="flex items-center gap-3">
                  <span className="w-8 text-center text-xs font-extrabold text-rose-600">#{v.rank}</span>
                  <div className="flex-1">
                    <div className="text-xs font-extrabold text-slate-900">{v.name}</div>
                    <div className="mt-1.5 flex items-center gap-2">
                      <span className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                        <span className={`block h-full rounded-full ${v.compliance >= 75 ? "bg-amber-400" : "bg-red-500"}`} style={{ width: `${v.compliance}%` }} />
                      </span>
                      <span className="text-[11px] font-extrabold text-rose-600">{v.compliance}%</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
