import { GradientBanner } from "@/components/ui/GradientBanner";
import { StatusPill } from "@/components/ui/StatusPill";
import { ClaimSummaryModal } from "@/components/claims/ClaimSummaryModal";
import type { ClaimRecord } from "@/lib/claims-data";
import { Calendar, FileText, Loader2, MapPin, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { useLocation } from "wouter";

export default function MyClaims() {
  const [, navigate] = useLocation();
  const [selectedClaim, setSelectedClaim] = useState<ClaimRecord | null>(null);
  const [claims, setClaims] = useState<ClaimRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/claims");
        const data = await res.json().catch(() => null);
        if (!res.ok) {
          throw new Error((data && data.error) || "Could not load claims.");
        }
        if (!cancelled) setClaims(Array.isArray(data?.claims) ? data.claims : []);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load claims.");
          setClaims([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const getBorderColor = (type: string) => {
    switch (type.toLowerCase()) {
      case "collision": return "border-l-blue-500";
      case "water damage": return "border-l-cyan-500";
      case "wind/hail": return "border-l-violet-500";
      case "theft": return "border-l-rose-500";
      case "fire": return "border-l-orange-500";
      default: return "border-l-gray-400";
    }
  };

  return (
    <div className="animate-in fade-in duration-500">
      <GradientBanner
        title="My Claims"
        subtitle="View and track all your submitted insurance claims"
        rightContent={
          <button
            onClick={() => navigate("/smart-loss-reporting")}
            className="flex items-center gap-2 bg-white/20 hover:bg-white/30 backdrop-blur-sm px-4 py-2 rounded-lg text-white font-medium transition-colors border border-white/10"
          >
            <Plus className="h-4 w-4" />
            File New Claim
          </button>
        }
      />

      {loading ? (
        <div className="flex items-center justify-center gap-2 text-gray-500 mt-10 py-10">
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading your claims...
        </div>
      ) : error ? (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-6 py-5 text-sm text-red-700">
          {error}
        </div>
      ) : claims.length === 0 ? (
        <div className="mt-6 rounded-xl border border-gray-200 bg-white px-6 py-10 text-center text-gray-500 shadow-sm">
          No claims found yet.
        </div>
      ) : (
        <div className="grid gap-4 mt-6">
          {claims.map((claim) => (
            <div 
              key={claim.id} 
              onClick={() => setSelectedClaim(claim)}
              className={`bg-white rounded-xl border border-gray-200 shadow-sm p-6 hover:shadow-md hover:-translate-y-0.5 transition-all cursor-pointer border-l-4 ${getBorderColor(claim.type)}`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                <div className="flex items-center gap-4">
                  <span className="font-mono text-sm text-gray-500 bg-gray-50 px-2 py-1 rounded border border-gray-100">
                    {claim.id}
                  </span>
                  <StatusPill status={claim.status} />
                </div>
              </div>
              
              <h3 className="text-lg font-bold text-gray-900 mb-4">{claim.description}</h3>
              
              <div className="flex flex-wrap items-center gap-6 text-sm text-gray-600">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-gray-400" />
                  {claim.date}
                </div>
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-gray-400" />
                  {claim.type}
                </div>
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-gray-400" />
                  {claim.location}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <ClaimSummaryModal claim={selectedClaim} onClose={() => setSelectedClaim(null)} />
    </div>
  );
}
