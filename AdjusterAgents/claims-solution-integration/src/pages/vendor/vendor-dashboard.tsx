import { useState } from "react";
import {
  Users,
  Star,
  ShieldCheck,
  Clock,
  TrendingUp,
  BarChart3,
  Ban,
  Briefcase,
  AlertTriangle,
} from "lucide-react";
import {
  highPerformers,
  mediumPerformers,
  lowPerformers,
  slaCompliant,
  slaAtRisk,
  slaBreached,
  costVariances,
  deactivatedVendors,
  recentActivity,
} from "@/lib/vendor-data";

const activityBadge: Record<string, string> = {
  Completed: "bg-emerald-600 text-white",
  Assigned: "bg-amber-400 text-white",
  "Pending Review": "bg-slate-400 text-white",
  "In Progress": "bg-blue-500 text-white",
};

function KpiTile({
  label,
  value,
  icon: Icon,
  className,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  className: string;
}) {
  return (
    <div className={`rounded-xl px-5 py-4 text-white shadow-md ${className}`}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-bold tracking-wider uppercase opacity-90">{label}</span>
        <Icon className="h-4 w-4 opacity-80" />
      </div>
      <div className="text-2xl font-extrabold">{value}</div>
    </div>
  );
}

interface BarRow {
  label: string;
  sub: string;
  count: number;
  pct: number;
  barClass: string;
  vendors: { name: string; specialty: string; location: string; score: number }[];
  scoreLabel: string;
}

function DistributionCard({
  title,
  icon: Icon,
  headerClass,
  rows,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  headerClass: string;
  rows: BarRow[];
}) {
  const [openRow, setOpenRow] = useState<string | null>(null);

  return (
    <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
      <div className={`px-5 py-3.5 flex items-center gap-2.5 ${headerClass}`}>
        <Icon className="h-4 w-4 text-white" />
        <h2 className="text-white font-extrabold text-sm">{title}</h2>
      </div>
      <div className="p-5 space-y-6">
        {rows.map((row) => (
          <div key={row.label}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-bold text-slate-800">
                {row.label} <span className="text-[10px] font-semibold text-slate-400 ml-1">({row.sub})</span>
              </span>
              <span className="text-sm font-extrabold text-slate-900">
                {row.count} <span className="text-[11px] font-semibold text-slate-400">({row.pct}%)</span>
              </span>
            </div>
            <button
              type="button"
              onClick={() => setOpenRow(openRow === row.label ? null : row.label)}
              className="w-full h-4 rounded-full bg-slate-100 overflow-hidden cursor-pointer"
              aria-label={`Toggle ${row.label} details`}
            >
              <div
                className={`h-full rounded-full ${row.barClass} transition-all`}
                style={{ width: `${Math.max(row.pct, 5)}%` }}
              />
            </button>
            {openRow === row.label && (
              <div className="mt-3 rounded-lg border border-slate-200 overflow-hidden animate-in fade-in duration-300">
                {row.vendors.length === 0 ? (
                  <div className="px-4 py-3 text-xs text-slate-500">No vendors in this group</div>
                ) : (
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="bg-slate-50 text-[10px] font-extrabold tracking-wide text-slate-500">
                        <th className="px-3 py-2">VENDOR</th>
                        <th className="px-3 py-2">SPECIALTY</th>
                        <th className="px-3 py-2">LOCATION</th>
                        <th className="px-3 py-2 text-right">{row.scoreLabel}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {row.vendors.map((v) => (
                        <tr key={v.name}>
                          <td className="px-3 py-2 font-bold text-slate-800">{v.name}</td>
                          <td className="px-3 py-2 text-slate-600">{v.specialty}</td>
                          <td className="px-3 py-2 text-slate-600">{v.location}</td>
                          <td className="px-3 py-2 text-right font-extrabold text-slate-900">{v.score}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function VendorDashboard() {
  const perfRows: BarRow[] = [
    {
      label: "High Performers",
      sub: "VIS 80-100",
      count: 6,
      pct: 30,
      barClass: "bg-gradient-to-r from-emerald-700 to-emerald-500",
      vendors: highPerformers.map((v) => ({ name: v.name, specialty: v.specialty, location: v.location, score: v.vis })),
      scoreLabel: "VIS",
    },
    {
      label: "Medium Performers",
      sub: "VIS 60-79",
      count: 14,
      pct: 70,
      barClass: "bg-gradient-to-r from-orange-500 to-amber-700",
      vendors: mediumPerformers.map((v) => ({ name: v.name, specialty: v.specialty, location: v.location, score: v.vis })),
      scoreLabel: "VIS",
    },
    {
      label: "Low Performers",
      sub: "VIS < 60",
      count: 0,
      pct: 0,
      barClass: "bg-gradient-to-r from-red-800 to-red-600",
      vendors: lowPerformers.map((v) => ({ name: v.name, specialty: v.specialty, location: v.location, score: v.vis })),
      scoreLabel: "VIS",
    },
  ];

  const slaRows: BarRow[] = [
    {
      label: "Compliant",
      sub: "SLA ≥ 90%",
      count: 7,
      pct: 35,
      barClass: "bg-gradient-to-r from-emerald-700 to-emerald-500",
      vendors: slaCompliant.map((v) => ({ name: v.name, specialty: v.specialty, location: v.location, score: v.sla })),
      scoreLabel: "SLA %",
    },
    {
      label: "At Risk",
      sub: "SLA 75-89%",
      count: 10,
      pct: 50,
      barClass: "bg-gradient-to-r from-orange-500 to-amber-700",
      vendors: slaAtRisk.map((v) => ({ name: v.name, specialty: v.specialty, location: v.location, score: v.sla })),
      scoreLabel: "SLA %",
    },
    {
      label: "Breached",
      sub: "SLA < 75%",
      count: 3,
      pct: 15,
      barClass: "bg-gradient-to-r from-red-800 to-red-600",
      vendors: slaBreached.map((v) => ({ name: v.name, specialty: v.specialty, location: v.location, score: v.sla })),
      scoreLabel: "SLA %",
    },
  ];

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-8 py-7 shadow-md">
        <h1 className="text-3xl font-extrabold tracking-tight text-white">Vendor Dashboard</h1>
        <p className="mt-1 text-sm text-indigo-200/80 font-medium">Monitor vendor network performance &amp; assignments</p>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <KpiTile label="Total Active Vendors" value="30" icon={Users} className="bg-gradient-to-br from-slate-900 to-slate-800" />
        <KpiTile label="Avg Vendor Score" value="74.5" icon={Star} className="bg-gradient-to-br from-blue-800 to-indigo-900" />
        <KpiTile label="SLA Compliance %" value="84.4%" icon={ShieldCheck} className="bg-gradient-to-br from-red-600 to-orange-600" />
        <KpiTile label="Avg Repair Time" value="5 days" icon={Clock} className="bg-gradient-to-br from-emerald-600 to-green-700" />
        <KpiTile label="Cost Variance %" value="4.0%" icon={TrendingUp} className="bg-gradient-to-br from-violet-600 to-purple-700" />
      </div>

      {/* Distribution cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <DistributionCard
          title="Vendor Performance Distribution"
          icon={Star}
          headerClass="bg-gradient-to-r from-violet-600 to-blue-600"
          rows={perfRows}
        />
        <DistributionCard
          title="SLA Adherence Trends"
          icon={ShieldCheck}
          headerClass="bg-gradient-to-r from-teal-600 to-cyan-600"
          rows={slaRows}
        />
      </div>

      {/* Cost vs Estimate Variance */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-orange-500 via-orange-600 to-red-600">
          <TrendingUp className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Cost vs Estimate Variance</h2>
        </div>
        <div className="p-5 space-y-3">
          {costVariances.map((cv) => (
            <div key={cv.vendor} className="flex items-center gap-3">
              <span className="w-40 text-xs font-semibold text-slate-700 truncate flex-shrink-0">{cv.vendor}</span>
              <div className="flex-1 h-4 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className={`h-full rounded-full ${cv.variance > 0 ? "bg-gradient-to-r from-red-500 to-red-600" : "bg-gradient-to-r from-emerald-500 to-emerald-600"}`}
                  style={{ width: `${Math.abs(cv.variance) * 3}%` }}
                />
              </div>
              <span className={`w-14 text-right text-xs font-extrabold ${cv.variance > 0 ? "text-red-600" : "text-emerald-600"}`}>
                {cv.variance > 0 ? "+" : ""}
                {cv.variance.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Deactivated / Ineligible Vendors */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-red-900 via-red-700 to-red-600">
          <Ban className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Deactivated / Ineligible Vendors ({deactivatedVendors.length})</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {deactivatedVendors.map((v) => (
            <div key={v.id} className="flex items-center justify-between px-5 py-4">
              <div className="flex items-stretch gap-3">
                <div className="w-1 rounded-full bg-red-600" />
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-extrabold text-slate-900 text-sm">{v.name}</span>
                    <span className="text-[11px] font-semibold text-slate-400">{v.id}</span>
                    <span className="rounded-full border border-slate-200 bg-slate-50 text-slate-600 px-2.5 py-0.5 text-[10px] font-bold">Inactive</span>
                    {v.immediate && (
                      <span className="rounded-full border border-red-200 bg-red-50 text-red-500 px-2.5 py-0.5 text-[10px] font-bold">Immediate</span>
                    )}
                  </div>
                  {v.reason && (
                    <div className="flex items-center gap-1.5 mt-1 text-[11px] font-semibold text-amber-600">
                      <AlertTriangle className="h-3 w-3" /> {v.reason}
                    </div>
                  )}
                </div>
              </div>
              <span className="rounded-full bg-red-50 text-red-500 border border-red-100 px-3 py-1 text-[10px] font-bold whitespace-nowrap">
                Not Eligible
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Vendor Activity */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-slate-950 to-slate-800">
          <Briefcase className="h-4 w-4 text-white" />
          <h2 className="text-white font-extrabold text-sm">Recent Vendor Activity</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {recentActivity.map((a, i) => (
            <div key={`${a.claimId}-${i}`} className="flex items-center justify-between px-5 py-3.5">
              <div className="flex items-stretch gap-3">
                <div className={`w-1 rounded-full ${a.status === "Completed" ? "bg-emerald-500" : a.status === "In Progress" ? "bg-blue-500" : a.status === "Assigned" ? "bg-amber-400" : "bg-violet-500"}`} />
                <div>
                  <div className="text-sm">
                    <span className="font-semibold text-slate-400">{a.claimId}</span>
                    <span className="mx-1.5 text-slate-300">•</span>
                    <span className="font-extrabold text-slate-900">{a.vendor}</span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">Assigned: {a.assignedDate}</div>
                </div>
              </div>
              <span className={`rounded-full px-3 py-1 text-[10px] font-bold whitespace-nowrap ${activityBadge[a.status]}`}>
                {a.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
