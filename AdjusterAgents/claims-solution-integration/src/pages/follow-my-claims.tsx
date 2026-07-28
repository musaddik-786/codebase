import { useEffect, useState } from "react";
import { GradientBanner } from "@/components/ui/GradientBanner";
import { StatusPill } from "@/components/ui/StatusPill";
import { ClaimJourneyWorkspace } from "@/components/claims/ClaimJourneyWorkspace";
import type { ClaimRecord } from "@/lib/claims-data";
import type { ClaimJourney, ClaimInsights } from "@/lib/journey-data";
import { Search, FileText, ChevronRight, Eye, Loader2 } from "lucide-react";

// Remembers which claim workspace was open so it survives leaving and returning
// to this page within the same browser session.
const OPEN_CLAIM_STORAGE_KEY = "followMyClaims.openClaim";

export default function FollowMyClaims() {
  const [claims, setClaims] = useState<ClaimRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const [journey, setJourney] = useState<ClaimJourney | null>(null);
  const [journeyLoading, setJourneyLoading] = useState(false);
  const [journeyError, setJourneyError] = useState<string | null>(null);
  const [insights, setInsights] = useState<ClaimInsights | null>(null);

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

  // Re-open the previously open claim (if any) when the page mounts, so the
  // user returns to the same workspace with Latest Updates reloaded.
  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = sessionStorage.getItem(OPEN_CLAIM_STORAGE_KEY);
    } catch {
      stored = null;
    }
    if (stored) {
      void selectClaim(stored);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectClaim = async (claimNumber: string) => {
    try {
      sessionStorage.setItem(OPEN_CLAIM_STORAGE_KEY, claimNumber);
    } catch {
      // sessionStorage unavailable — persistence is best-effort
    }
    setJourney(null);
    setJourneyError(null);
    setInsights(null);
    setJourneyLoading(true);
    try {
      const [journeyRes, insightsRes] = await Promise.all([
        fetch(`/api/claim-journey?claimNumber=${encodeURIComponent(claimNumber)}`),
        fetch(`/api/claim-insights?claimNumber=${encodeURIComponent(claimNumber)}`),
      ]);
      const journeyData = await journeyRes.json().catch(() => null);
      if (!journeyRes.ok) {
        if (journeyRes.status === 404) {
          // Claim no longer has a journey — drop it so auto-reopen doesn't
          // loop straight back into this error on every return to the page.
          try {
            sessionStorage.removeItem(OPEN_CLAIM_STORAGE_KEY);
          } catch {
            // sessionStorage unavailable — nothing to clear
          }
        }
        throw new Error(
          journeyRes.status === 404
            ? "No journey details found for this claim yet."
            : (journeyData && journeyData.error) || "Could not load claim journey."
        );
      }
      setJourney(journeyData as ClaimJourney);
      if (insightsRes.ok) {
        const insightsData = await insightsRes.json().catch(() => null);
        if (insightsData) setInsights(insightsData as ClaimInsights);
      }
    } catch (err) {
      setJourneyError(
        err instanceof Error ? err.message : "Could not load claim journey."
      );
    } finally {
      setJourneyLoading(false);
    }
  };

  const closeWorkspace = () => {
    try {
      sessionStorage.removeItem(OPEN_CLAIM_STORAGE_KEY);
    } catch {
      // sessionStorage unavailable — nothing to clear
    }
    setJourney(null);
    setJourneyError(null);
    setJourneyLoading(false);
    setInsights(null);
  };

  const filtered = claims.filter((claim) => {
    const q = query.toLowerCase();
    return (
      claim.id.toLowerCase().includes(q) ||
      claim.type.toLowerCase().includes(q) ||
      claim.policyholder.toLowerCase().includes(q)
    );
  });

  const showingWorkspace = journeyLoading || journeyError !== null || journey !== null;

  return (
    <div className="animate-in fade-in duration-500">
      <GradientBanner
        title="Claim Journey Workspace"
        subtitle="Track your claims progress in real-time"
        rightContent={
          <button className="flex items-center gap-2 bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2 rounded-lg text-white font-medium shadow-md hover:shadow-lg transition-all border border-blue-500/50">
            <Eye className="h-4 w-4" />
            Customer View
          </button>
        }
      />

      {showingWorkspace ? (
        journeyLoading ? (
          <div className="flex items-center justify-center gap-2 text-gray-500 mt-10 py-10">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading claim journey...
          </div>
        ) : journeyError ? (
          <div className="mt-6">
            <button
              onClick={closeWorkspace}
              className="mb-4 text-sm text-blue-600 hover:underline"
            >
              ← Back to Claims
            </button>
            <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-5 text-sm text-red-700">
              {journeyError}
            </div>
          </div>
        ) : (
          journey && (
            <ClaimJourneyWorkspace
              claim={journey}
              insights={insights}
              onBack={closeWorkspace}
              onRefresh={() => selectClaim(journey.id)}
            />
          )
        )
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mb-6">
          <div className="bg-gradient-to-r from-[#1e1b4b]/10 to-[#5b21b6]/10 p-4 border-b border-gray-200 flex items-center gap-3">
            <FileText className="h-5 w-5 text-indigo-700" />
            <h2 className="font-semibold text-indigo-950">Select a Claim to Track</h2>
          </div>

          <div className="p-4 border-b border-gray-100">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by claim number, name, or loss type..."
                className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-sm transition-shadow bg-gray-50/50"
              />
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center gap-2 text-gray-500 p-8">
              <Loader2 className="h-5 w-5 animate-spin" />
              Loading your claims...
            </div>
          ) : error ? (
            <div className="p-8 text-center text-sm text-red-700">{error}</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filtered.length === 0 ? (
                <div className="p-8 text-center text-sm text-gray-500">
                  {claims.length === 0
                    ? "No claims found yet."
                    : "No claims match your search."}
                </div>
              ) : (
                filtered.map((claim) => (
                  <div
                    key={claim.id}
                    onClick={() => selectClaim(claim.id)}
                    className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-100 to-blue-50 flex items-center justify-center border border-indigo-100 group-hover:scale-105 transition-transform">
                        <FileText className="h-5 w-5 text-indigo-600" />
                      </div>
                      <div>
                        <div className="font-semibold text-gray-900">{claim.id}</div>
                        <div className="text-sm text-gray-500 capitalize">
                          {claim.type.toLowerCase()}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <StatusPill status={claim.status} />
                      <ChevronRight className="h-5 w-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
