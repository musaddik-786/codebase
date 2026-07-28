import { useState } from "react";
import { Shield, Search, Loader2, CheckCircle2, XCircle, X } from "lucide-react";
import { Step1Describe } from "./Step1Describe";

const MCP_URL = import.meta.env.VITE_MCP_URL ?? "http://localhost:7720";
const POLICY_LOOKUP_ENDPOINT = `${MCP_URL}/api/v1/policy_coverage/gw_search_policy`;
const POLICY_SAVE_ENDPOINT = `${MCP_URL}/api/v1/policy_coverage/save_policy_details`;

export function Stage1PolicyLookup({
  policyNumber,
  onPolicyNumberChange,
  description,
  onDescriptionChange,
  estimatedCost,
  onEstimatedCostChange,
  onNext,
}: {
  policyNumber: string;
  onPolicyNumberChange: (value: string) => void;
  description: string;
  onDescriptionChange: (value: string) => void;
  estimatedCost: string;
  onEstimatedCostChange: (value: string) => void;
  onNext: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [valid, setValid] = useState<boolean | null>(null);
  const [showResult, setShowResult] = useState(false);

  const handleLookup = async () => {
    if (!policyNumber.trim() || loading) return;
    setLoading(true);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const res = await fetch(POLICY_LOOKUP_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ policy_number: policyNumber.trim() }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`Lookup failed: ${res.status}`);
      const data = await res.json();
      const found = data?.found === true;
      setValid(found);

      // Persist policy data to the local DB so Stage 2's "Your Policy Information"
      // section can read insured name, address and policy period from policy_details.
      if (found) {
        fetch(POLICY_SAVE_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ policy_number: policyNumber.trim() }),
        }).catch(() => {
          // Non-blocking — Stage 2 will just show empty fields if this fails
        });
      }
    } catch (err) {
      console.error("Policy lookup error:", err);
      setValid(false);
    } finally {
      clearTimeout(timeout);
      setShowResult(true);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-2 text-emerald-700 font-semibold">
          <Shield className="h-5 w-5" />
          Verify Your Policy
        </div>
        <p className="text-sm text-gray-500 mt-1 mb-4">
          Enter your policy number so we can confirm your coverage before you
          report a loss.
        </p>

        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={policyNumber}
            onChange={(e) => onPolicyNumberChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void handleLookup();
              }
            }}
            placeholder="Enter policy number"
            className="flex-1 rounded-xl border border-gray-200 px-4 py-3 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
          />
          <button
            type="button"
            onClick={handleLookup}
            disabled={loading || !policyNumber.trim()}
            className={`flex items-center justify-center gap-2 rounded-xl px-6 py-3 font-bold text-white shadow-md transition-colors ${
              loading || !policyNumber.trim()
                ? "bg-emerald-300 cursor-not-allowed"
                : "bg-emerald-600 hover:bg-emerald-700"
            }`}
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Search className="h-5 w-5" />
            )}
            {loading ? "Looking up..." : "Lookup"}
          </button>
        </div>
      </div>

      <Step1Describe
        description={description}
        policyNumber={policyNumber}
        onDescriptionChange={onDescriptionChange}
        estimatedCost={estimatedCost}
        onEstimatedCostChange={onEstimatedCostChange}
        onNext={onNext}
      />

      {showResult && valid !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
          onClick={() => setShowResult(false)}
        >
          <div
            className="bg-white rounded-2xl shadow-xl max-w-sm w-full p-8 text-center relative animate-in fade-in zoom-in duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              aria-label="Close"
              onClick={() => setShowResult(false)}
              className="absolute top-3 right-3 h-8 w-8 rounded-full flex items-center justify-center text-gray-400 hover:bg-gray-100 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
            <div
              className={`h-16 w-16 rounded-full flex items-center justify-center mx-auto mb-4 ${
                valid ? "bg-emerald-50" : "bg-red-50"
              }`}
            >
              {valid ? (
                <CheckCircle2 className="h-9 w-9 text-emerald-500" />
              ) : (
                <XCircle className="h-9 w-9 text-red-500" />
              )}
            </div>
            <h3 className="text-lg font-bold text-gray-900">
              {valid
                ? "The user is a valid policyholder."
                : "The user is an invalid policyholder."}
            </h3>
            <button
              type="button"
              onClick={() => setShowResult(false)}
              className={`mt-6 w-full rounded-xl py-3 font-bold text-white shadow-md transition-colors ${
                valid
                  ? "bg-emerald-600 hover:bg-emerald-700"
                  : "bg-gray-700 hover:bg-gray-800"
              }`}
            >
              Got it
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
