import { useEffect, useState, useMemo } from "react";
import { useToast } from "@/hooks/use-toast";
import {
  AlertTriangle,
  Calendar,
  Camera,
  CheckCircle2,
  FileText,
  Loader2,
  MapPin,
  MessageSquare,
  Plane,
  Radar,
  Search,
  Send,
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { streamOrchestratorChat, decideClaimGate } from "@/lib/adjuster-orchestrator";

export default function VerificationIntelligence() {
  const { toast } = useToast();
  const [claims, setClaims] = useState<any[]>([]);
  const [selectedClaimNumber, setSelectedClaimNumber] = useState<string>("");
  const [claimSearch, setClaimSearch] = useState("");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeImage, setActiveImage] = useState(0);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const runOrchestrator = async (label: string, fn: () => Promise<string>) => {
    if (busyAction) return;
    setBusyAction(label);
    try {
      const description = await fn();
      toast({ title: label, description });
    } catch (err) {
      toast({
        title: label,
        description:
          err instanceof Error ? err.message : "Could not reach the adjuster orchestrator.",
        variant: "destructive",
      });
    } finally {
      setBusyAction(null);
    }
  };

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
        else setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load claims");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedClaimNumber) return;
    setLoading(true);
    setError(null);
    setActiveImage(0);
    fetch(`/api/adjuster/verification?claimNumber=${encodeURIComponent(selectedClaimNumber)}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load verification data");
        return res.json();
      })
      .then((json) => setData(json))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedClaimNumber]);

  const filteredClaims = useMemo(() => {
    if (!claimSearch.trim()) return claims;
    const q = claimSearch.toLowerCase();
    return claims.filter((c: any) =>
      String(c.id).toLowerCase().includes(q) || String(c.policyholder || "").toLowerCase().includes(q)
    );
  }, [claims, claimSearch]);

  const handleAction = (action: string) => {
    toast({ title: "Action Recorded", description: `Successfully executed: ${action}` });
  };

  const images = data?.customerImages || [];
  const drone = data?.drone;
  const fraudRisk = data?.claim?.fraudRisk || "Low";
  const fraudPill =
    fraudRisk === "High" ? "bg-red-500" : fraudRisk === "Medium" ? "bg-amber-500" : "bg-emerald-500";

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-7 py-5 shadow-md flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
            <Radar className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-white">Verification Intelligence</h1>
            <p className="mt-0.5 text-sm text-indigo-200/80 font-medium">
              Validate customer-uploaded images against drone captures, weather, and location data
            </p>
          </div>
        </div>
        <span className="rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs font-bold text-white whitespace-nowrap">Adjuster</span>
      </div>

      {/* Claim Selection */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="bg-gradient-to-r from-violet-700 to-purple-700 px-6 py-4">
          <h2 className="flex items-center gap-2 text-white font-extrabold">
            <FileText className="h-4 w-4" /> Claim Selection
          </h2>
          <p className="text-xs text-violet-100/90 mt-0.5">Select a claim to verify drone imagery</p>
        </div>
        <div className="p-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-5 items-start">
          <div>
            <label className="block text-[11px] font-bold text-slate-500 mb-1.5">Search Claim</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
              <input
                value={claimSearch}
                onChange={(e) => setClaimSearch(e.target.value)}
                placeholder="Search claim #"
                className="w-full rounded-full border border-slate-200 pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              />
            </div>
          </div>
          <div>
            <label className="block text-[11px] font-bold text-slate-500 mb-1.5">Select Claim</label>
            <Select value={selectedClaimNumber} onValueChange={setSelectedClaimNumber}>
              <SelectTrigger className="w-full rounded-lg border-slate-200 font-semibold text-sm h-9">
                <SelectValue placeholder="Select claim" />
              </SelectTrigger>
              <SelectContent>
                {filteredClaims.map((c: any) => (
                  <SelectItem key={c.id} value={c.id}>{c.id}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <div className="text-[11px] font-bold text-slate-500 mb-1.5">Insured Name</div>
            <div className="text-sm font-extrabold text-slate-900">{data?.claim?.insuredName || "—"}</div>
          </div>
          <div>
            <div className="text-[11px] font-bold text-slate-500 mb-2">Loss Type</div>
            <span className="inline-flex rounded-full border border-slate-300 px-3 py-1 text-[11px] font-bold text-slate-700 whitespace-nowrap">
              {data?.claim?.lossType || "—"}
            </span>
          </div>
          <div>
            <div className="text-[11px] font-bold text-slate-500 mb-1.5">Location</div>
            <div className="text-xs font-semibold text-slate-700 flex items-start gap-1">
              <MapPin className="h-3.5 w-3.5 text-slate-400 shrink-0 mt-0.5" />
              <span>{data?.claim?.location || "—"}</span>
            </div>
          </div>
          <div>
            <div className="text-[11px] font-bold text-slate-500 mb-2">Fraud Risk Score</div>
            <span className={`inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white whitespace-nowrap ${fraudPill}`}>
              {fraudRisk} Risk ({data?.claim?.fraudScore ?? 0})
            </span>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-violet-600" /></div>
      ) : error ? (
        <div className="bg-red-50 text-red-600 p-4 rounded-xl border border-red-200 font-medium">{error}</div>
      ) : data ? (
        <>
          {/* Imagery comparison */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Customer Uploaded Images */}
            <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden flex flex-col">
              <div className="bg-gradient-to-r from-blue-600 to-cyan-500 px-6 py-4">
                <h2 className="flex items-center gap-2 text-white font-extrabold">
                  <Camera className="h-4 w-4" /> Customer Uploaded Images
                </h2>
                <p className="text-xs text-blue-100/90 mt-0.5">Images submitted by policyholder</p>
              </div>
              <div className="bg-blue-50/70 px-5 py-2.5 flex items-center justify-between border-b border-blue-100">
                <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-600">
                  <Calendar className="h-3.5 w-3.5 text-blue-500" />
                  Uploaded: {images[activeImage]?.uploadedAt || "—"}
                </span>
                <span className="text-xs font-bold text-blue-600">{images.length} photos</span>
              </div>
              <div className="p-4 flex-1 flex flex-col">
                {images.length > 0 ? (
                  <>
                    <div className="rounded-lg overflow-hidden bg-slate-100 aspect-[4/3]">
                      <img
                        src={images[activeImage]?.url}
                        alt={images[activeImage]?.fileName}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="flex gap-2 mt-3 overflow-x-auto">
                      {images.map((img: any, i: number) => (
                        <button
                          key={img.documentId}
                          onClick={() => setActiveImage(i)}
                          className={`h-16 w-20 shrink-0 rounded-lg overflow-hidden border-2 transition-colors ${
                            i === activeImage ? "border-blue-500" : "border-transparent opacity-70 hover:opacity-100"
                          }`}
                        >
                          <img src={img.url} alt={img.fileName} className="w-full h-full object-cover" />
                        </button>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center py-16 text-slate-400">
                    <Camera className="h-10 w-10 mb-3" />
                    <p className="text-sm font-semibold">No customer images uploaded</p>
                  </div>
                )}
              </div>
            </div>

            {/* Drone Aerial Imagery */}
            <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden flex flex-col">
              <div className="bg-gradient-to-r from-violet-700 to-purple-600 px-6 py-4">
                <h2 className="flex items-center gap-2 text-white font-extrabold">
                  <Radar className="h-4 w-4" /> Drone Aerial Imagery
                </h2>
                <p className="text-xs text-violet-100/90 mt-0.5">Verified drone captures</p>
              </div>
              <div className="bg-violet-50/70 px-5 py-2.5 flex items-center justify-between border-b border-violet-100">
                <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-600">
                  <Calendar className="h-3.5 w-3.5 text-violet-500" />
                  Captured: {drone?.captureTime || "—"}
                </span>
                <span className="text-xs font-bold text-violet-600">{drone ? "1 capture" : "0 photos"}</span>
              </div>
              <div className="p-4 flex-1">
                {drone ? (
                  <div className="flex flex-col gap-3 h-full">
                    <div className="grid grid-cols-2 gap-3 flex-none">
                      <div className="rounded-lg border border-violet-200 bg-violet-50 p-4 flex flex-col justify-center">
                        <div className="text-[11px] font-semibold uppercase tracking-wide text-violet-700">
                          Site Condition Rating
                        </div>
                        <div className="mt-1.5 text-lg font-extrabold text-violet-900">
                          {drone.roofCondition || "—"}
                        </div>
                      </div>
                      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 flex flex-col justify-center">
                        <div className="text-[11px] font-semibold uppercase tracking-wide text-emerald-700">
                          Damage Match Percent
                        </div>
                        <div className="mt-1.5 text-lg font-extrabold text-emerald-700">
                          {drone.damageMatchPercent}%
                        </div>
                      </div>
                    </div>
                    <div className="rounded-lg border border-sky-200 bg-sky-50 p-4 flex-1 flex flex-col justify-center">
                      <div className="text-[11px] font-semibold uppercase tracking-wide text-sky-700">
                        Scene Alignment
                      </div>
                      <div className="mt-1.5 text-sm font-medium text-slate-800 leading-relaxed">
                        {drone.weatherAlignment || "—"}
                      </div>
                    </div>
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 flex-1 flex flex-col justify-center">
                      <div className="text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                        Site Condition
                      </div>
                      <div className="mt-1.5 text-sm font-medium text-slate-800 leading-relaxed">
                        {drone.siteCondition || "—"}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 h-full min-h-[180px] flex flex-col items-center justify-center text-center px-8 py-10">
                    <Radar className="h-9 w-9 text-slate-400 mb-3" />
                    <div className="text-slate-500 text-xs font-bold tracking-widest">NO DRONE DATA</div>
                    <div className="text-slate-400 text-[11px] mt-1">Awaiting drone sweep</div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* No drone data alert */}
          {!drone && (
            <div className="rounded-xl overflow-hidden shadow-sm border border-orange-200">
              <div className="bg-gradient-to-r from-orange-500 to-red-500 px-6 py-4 flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-white" />
                <div>
                  <h2 className="text-white font-extrabold">No Drone Verification Data Available</h2>
                  <p className="text-xs text-orange-100 mt-0.5">Drone sweep has not been completed for this claim</p>
                </div>
              </div>
              <div className="bg-white px-8 py-10 text-center">
                <div className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 mb-4">
                  <Plane className="h-6 w-6 text-slate-400" />
                </div>
                <h3 className="font-extrabold text-slate-900 mb-2">Pending Drone Verification</h3>
                <p className="text-sm text-slate-500 max-w-lg mx-auto mb-6">
                  Drone evidence has not been captured for claim{" "}
                  <span className="font-bold text-slate-700">{data?.claim?.claimNumber}</span>. Request a drone sweep to
                  enable image verification against aerial captures, weather, and location data.
                </p>
                <button
                  onClick={() =>
                    runOrchestrator("Request Drone Sweep", async () => {
                      await streamOrchestratorChat(
                        `Run external data checks and request a drone sweep for claim ${selectedClaimNumber}`
                      );
                      return `External data / drone checks triggered for ${selectedClaimNumber}.`;
                    })
                  }
                  disabled={busyAction !== null}
                  className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 px-6 py-2.5 text-sm font-bold text-white shadow-md transition-colors disabled:opacity-60"
                >
                  <Radar className="h-4 w-4" /> Request Drone Sweep
                </button>
              </div>
            </div>
          )}

          {/* Adjuster Actions */}
          <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
            <div className="bg-gradient-to-r from-violet-700 to-purple-700 px-6 py-4">
              <h2 className="flex items-center gap-2 text-white font-extrabold">
                <CheckCircle2 className="h-4 w-4" /> Drone Verification - Adjuster Actions
              </h2>
              <p className="text-xs text-violet-100/90 mt-0.5">Take action on this verification</p>
            </div>
            <div className="p-5 flex flex-wrap gap-3">
              <button
                onClick={() =>
                  runOrchestrator("Approve Verified", async () => {
                    const r = await decideClaimGate(selectedClaimNumber, "Approved", {
                      gateType: "damage_assessment_review",
                    });
                    return r.decided > 0
                      ? `Approved ${r.gates.join(", ")} for ${selectedClaimNumber}.`
                      : "No pending approval gate for this claim.";
                  })
                }
                disabled={busyAction !== null}
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 px-5 py-2.5 text-sm font-bold text-white shadow-sm transition-colors disabled:opacity-60"
              >
                <CheckCircle2 className="h-4 w-4" /> Approve Verified
              </button>
              <button
                onClick={() =>
                  runOrchestrator("Forward to SIU", async () => {
                    const r = await decideClaimGate(selectedClaimNumber, "Rejected", {
                      gateType: "damage_assessment_review",
                      notes: "Escalated to SIU by adjuster",
                    });
                    return r.decided > 0
                      ? `Escalated ${r.gates.join(", ")} to SIU for ${selectedClaimNumber}.`
                      : "No pending approval gate to escalate for this claim.";
                  })
                }
                disabled={busyAction !== null}
                className="inline-flex items-center gap-2 rounded-lg bg-orange-500 hover:bg-orange-600 px-5 py-2.5 text-sm font-bold text-white shadow-sm transition-colors disabled:opacity-60"
              >
                <Send className="h-4 w-4" /> Forward to SIU
              </button>
              <button
                onClick={() => handleAction("Request Clarification")}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-5 py-2.5 text-sm font-bold text-slate-700 transition-colors"
              >
                <MessageSquare className="h-4 w-4" /> Request Clarification
              </button>
              <button
                onClick={() => handleAction("Generate Report")}
                className="inline-flex items-center gap-2 rounded-lg bg-slate-900 hover:bg-slate-800 px-5 py-2.5 text-sm font-bold text-white shadow-sm transition-colors"
              >
                <FileText className="h-4 w-4" /> Generate Report
              </button>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
