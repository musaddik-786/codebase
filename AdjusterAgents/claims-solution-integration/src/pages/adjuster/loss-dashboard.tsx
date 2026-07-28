import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  Clock,
  FileText,
  Loader2,
  UserRoundCheck,
  Zap,
} from "lucide-react";

interface DashboardData {
  kpis: {
    assigned: number;
    avgResolutionDays: number | null;
    atRisk: number;
    approvedToday: number;
  };
  stp: {
    readinessPct: number;
    avgReadiness: number;
    breakdown: Record<string, number>;
    classified: number;
  };
  priorityClaims: Array<{
    claimNumber: string;
    description: string;
    lossType: string;
    location: string;
    severity: string;
    status: string;
  }>;
  recentActivity: Array<{
    claimNumber: string;
    policyholder: string;
    description: string;
    stage: string;
    status: string;
    filedAt: string;
  }>;
  preLossAlerts: Array<{
    type: string;
    severity: string;
    title: string;
    description: string;
    location: string;
    date: string;
  }>;
}

function eligibilityLabel(pct: number): string {
  if (pct >= 60) return "High Eligibility";
  if (pct >= 25) return "Moderate Eligibility";
  return "Low Eligibility";
}

function isApprovedStatus(status: string): boolean {
  const s = status.toLowerCase();
  return s.includes("approved") || s.includes("payment") || s.includes("closed") || s.includes("settled");
}

export default function LossDashboard() {
  const [, navigate] = useLocation();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/adjuster/dashboard");
        const json = await res.json().catch(() => null);
        if (!res.ok) throw new Error(json?.error || "Could not load dashboard data.");
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load dashboard data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="p-6 md:p-8">
        <Banner />
        <div className="flex items-center justify-center py-32 text-slate-500 gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          <span className="text-lg font-medium">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 md:p-8">
        <Banner />
        <div className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-8 text-center text-red-700 font-medium">
          {error || "Failed to load data"}
        </div>
      </div>
    );
  }

  const stpCards = [
    { label: "Full STP", count: data.stp.breakdown["Full STP"] ?? 0, box: "bg-emerald-50 border-emerald-200", text: "text-emerald-600", underline: "border-emerald-400" },
    { label: "Vendor-STP", count: data.stp.breakdown["Vendor-STP"] ?? 0, box: "bg-amber-50 border-amber-200", text: "text-amber-500", underline: "border-amber-400" },
    { label: "Fast Track", count: data.stp.breakdown["Fast Track"] ?? 0, box: "bg-blue-50 border-blue-200", text: "text-blue-600", underline: "border-blue-400" },
    { label: "Manual", count: data.stp.breakdown["Manual"] ?? 0, box: "bg-rose-50 border-rose-200", text: "text-rose-500", underline: "border-rose-400" },
  ];

  return (
    <div className="p-6 md:p-8 space-y-6 bg-slate-50 min-h-screen animate-in fade-in duration-500">
      <Banner />

      {/* KPI tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        <KpiTile
          label="Assigned Claims"
          value={String(data.kpis.assigned)}
          icon={<ClipboardList className="h-5 w-5 text-white/80" />}
          gradient="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800 border border-slate-700"
        />
        <KpiTile
          label="Avg Resolution"
          value={data.kpis.avgResolutionDays !== null ? `${data.kpis.avgResolutionDays} days` : "—"}
          icon={<Clock className="h-5 w-5 text-white/80" />}
          gradient="bg-gradient-to-br from-blue-700 via-blue-600 to-blue-500"
        />
        <KpiTile
          label="Claims at Risk"
          value={String(data.kpis.atRisk)}
          icon={<AlertTriangle className="h-5 w-5 text-white/80" />}
          gradient="bg-gradient-to-br from-orange-600 via-orange-500 to-red-500"
        />
        <KpiTile
          label="Approved Today"
          value={String(data.kpis.approvedToday)}
          icon={<UserRoundCheck className="h-5 w-5 text-white/80" />}
          gradient="bg-gradient-to-br from-emerald-700 via-emerald-600 to-green-500"
        />
      </div>

      {/* Average STP Readiness band */}
      <div className="rounded-xl bg-gradient-to-r from-slate-900 to-slate-800 border border-slate-700 px-6 py-5 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-4">
          <div className="h-11 w-11 rounded-full border-2 border-blue-500/60 bg-blue-500/10 flex items-center justify-center">
            <Zap className="h-5 w-5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-white font-bold text-base">Average STP Readiness</h3>
            <p className="text-slate-400 text-xs mt-0.5">% of active claims eligible for STP (Full + Vendor-STP)</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-4xl font-extrabold text-blue-400 leading-none">
            {data.stp.readinessPct}<span className="text-xl align-top font-bold">%</span>
          </div>
          <span className="inline-block mt-1.5 rounded-full bg-blue-600 px-3 py-0.5 text-[10px] font-bold text-white tracking-wide">
            {eligibilityLabel(data.stp.readinessPct)}
          </span>
        </div>
      </div>

      {/* STP category cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-5">
        {stpCards.map((c) => (
          <div key={c.label} className={`rounded-xl border ${c.box} px-6 py-6 text-center shadow-sm`}>
            <div className={`text-4xl font-extrabold ${c.text}`}>{c.count}</div>
            <div className={`mt-2 inline-block text-[11px] font-bold uppercase tracking-wider ${c.text} border-b-2 ${c.underline} pb-0.5`}>
              {c.label}
            </div>
          </div>
        ))}
      </div>

      {/* Priority Claims + Recent Activity */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Priority Claims */}
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="bg-gradient-to-r from-purple-600 via-violet-600 to-indigo-500 px-5 py-4 flex items-center justify-between">
            <h3 className="text-white font-bold">Priority Claims</h3>
            <span className="flex items-center gap-1.5 text-white text-xs font-semibold">
              View All <ArrowRight className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="divide-y divide-slate-100">
            {data.priorityClaims.length === 0 ? (
              <div className="px-5 py-8 text-center text-sm text-slate-500">No priority claims right now.</div>
            ) : (
              data.priorityClaims.map((claim, i) => (
                <div
                  key={i}
                  className="relative px-5 py-4 pl-6 cursor-pointer hover:bg-slate-50 transition-colors"
                  onClick={() => navigate(`/loss-assessment?claim=${claim.claimNumber}`)}
                >
                  <span className="absolute left-0 top-3 bottom-3 w-1 rounded-full bg-gradient-to-b from-purple-500 to-indigo-500" />
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-[11px] font-bold tracking-wide text-purple-600 uppercase">{claim.claimNumber}</span>
                    <span className="shrink-0 rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-bold text-emerald-700">
                      {claim.severity}
                    </span>
                  </div>
                  <p className="mt-1 text-sm font-semibold text-slate-900 leading-snug truncate">{claim.description}</p>
                  <p className="mt-1.5 text-xs text-slate-500">
                    {claim.lossType} <span className="mx-1 text-slate-300">•</span> {claim.location}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-500 px-5 py-4 flex items-center justify-between">
            <h3 className="text-white font-bold">Recent Activity</h3>
            <span className="flex items-center gap-1.5 text-white text-xs font-semibold">
              View All <ArrowRight className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="divide-y divide-slate-100">
            {data.recentActivity.length === 0 ? (
              <div className="px-5 py-8 text-center text-sm text-slate-500">No recent activity.</div>
            ) : (
              data.recentActivity.map((activity, i) => {
                const approved = isApprovedStatus(activity.status);
                return (
                  <div
                    key={i}
                    className="px-5 py-3.5 flex items-center gap-3 cursor-pointer hover:bg-slate-50 transition-colors"
                    onClick={() => navigate(`/loss-assessment?claim=${activity.claimNumber}`)}
                  >
                    <div className={`h-9 w-9 shrink-0 rounded-full flex items-center justify-center ${approved ? "bg-emerald-100" : "bg-blue-100"}`}>
                      {approved ? (
                        <CheckCircle2 className="h-4.5 w-4.5 text-emerald-600" />
                      ) : (
                        <FileText className="h-4.5 w-4.5 text-blue-600" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-bold text-slate-900 truncate">{activity.policyholder}</p>
                      <p className="text-xs text-slate-500 truncate">{activity.description}</p>
                    </div>
                    <span
                      className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-bold text-white ${approved ? "bg-emerald-500" : "bg-blue-500"}`}
                    >
                      {approved ? "Approved" : "Loss Investigation"}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Pre-Loss Risk Alerts */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="bg-gradient-to-r from-amber-500 via-orange-500 to-red-500 px-5 py-4 flex items-center gap-2.5">
          <AlertTriangle className="h-4.5 w-4.5 text-white" />
          <h3 className="text-white font-bold">Pre-Loss Risk Alerts</h3>
        </div>
        <div className="divide-y divide-slate-100">
          {data.preLossAlerts.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm text-slate-500">No active alerts.</div>
          ) : (
            data.preLossAlerts.map((alert, i) => {
              const sev = alert.severity.toLowerCase();
              const sevClass = sev.includes("high") || sev.includes("critical")
                ? "bg-rose-100 text-rose-600"
                : sev.includes("medium")
                  ? "bg-emerald-100 text-emerald-600"
                  : "bg-slate-100 text-slate-600";
              return (
                <div key={i} className="relative px-5 py-4 pl-6">
                  <span className="absolute left-0 top-3 bottom-3 w-1 rounded-full bg-gradient-to-b from-amber-400 to-red-500" />
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h4 className="text-sm font-bold text-slate-900">{alert.title}</h4>
                      <p className="mt-1 text-xs text-slate-600 leading-relaxed">{alert.description}</p>
                      <p className="mt-1.5 text-xs text-slate-500">
                        {alert.type} <span className="mx-1 text-slate-300">•</span> {alert.location}
                      </p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-bold ${sevClass}`}>
                      {sev}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

function Banner() {
  return (
    <div className="rounded-xl bg-gradient-to-r from-indigo-900 via-violet-950 to-slate-950 px-8 py-8 shadow-md">
      <h1 className="text-3xl font-extrabold tracking-tight text-white">Claims Overview</h1>
      <p className="mt-1 text-sm text-indigo-200/80 font-medium">Manage assigned claims and assessments</p>
    </div>
  );
}

function KpiTile({ label, value, icon, gradient }: { label: string; value: string; icon: React.ReactNode; gradient: string }) {
  return (
    <div className={`rounded-xl ${gradient} px-5 py-5 shadow-sm text-white`}>
      <div className="flex items-start justify-between">
        <span className="text-[11px] font-bold uppercase tracking-wider text-white/85">{label}</span>
        {icon}
      </div>
      <div className="mt-3 text-3xl font-extrabold tracking-tight">{value}</div>
    </div>
  );
}
