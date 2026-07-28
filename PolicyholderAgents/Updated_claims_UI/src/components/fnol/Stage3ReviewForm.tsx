import {
  FileText,
  Database,
  Sparkles,
  Camera,
  Shield,
  Send,
  Loader2,
} from "lucide-react";
import { SourceTag } from "./SourceTag";
import {
  type LossSource,
  type EvidencePhoto,
  type FnolField,
  type PolicyField,
} from "@/lib/fnol-data";

const sourceTagFor = (source: LossSource) => {
  switch (source) {
    case "Human Edited":
      return <SourceTag variant="customer-confirmed-solid" label="Human Edited" />;
    case "Confirmed by You":
    case "Customer-Confirmed":
      return <SourceTag variant="customer-confirmed-solid" label="Confirmed by You" />;
    case "You Provided":
    case "Customer-Provided":
      return <SourceTag variant="customer-provided-solid" label="You Provided" />;
    case "From Your Voice":
      return <SourceTag variant="customer-provided-solid" label="From Your Voice" />;
    case "From Description":
      return <SourceTag variant="customer-provided-solid" label="From Description" />;
    case "Policy Record":
      return <SourceTag variant="auto-filled-solid" label="Policy Record" />;
    case "AI Extracted":
    case "AI-Inferred":
    default:
      return <SourceTag variant="ai-inferred-solid" label="AI Extracted" />;
  }
};

export function Stage3ReviewForm({
  policyNumber,
  sectionA,
  photos,
  comments,
  humanReview,
  lossFields,
  isSubmitting,
  submitError,
  onSubmit,
  onBack,
}: {
  policyNumber: string;
  sectionA: PolicyField[];
  photos: EvidencePhoto[];
  comments: string;
  humanReview: Record<string, string>;
  lossFields: FnolField[];
  isSubmitting?: boolean;
  submitError?: string | null;
  onSubmit: () => void;
  onBack: () => void;
}) {
  return (
    <div className="max-w-5xl mx-auto">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="bg-gradient-to-r from-slate-900 to-slate-800 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-white font-bold">
            <FileText className="h-5 w-5" />
            FINAL FNOL REPORT
          </div>
          <span className="rounded-full border border-white/30 px-3 py-1 text-[11px] font-semibold text-white/90">
            READY TO SUBMIT
          </span>
        </div>

        <div className="p-6">
          <div className="rounded-lg bg-emerald-50 px-4 py-2.5 flex items-center gap-2 text-emerald-700 font-semibold text-sm mb-3">
            <Shield className="h-4 w-4" />
            Verified Policy
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50/50 px-4 py-3 text-sm text-gray-700 mb-6">
            Policy Number:{" "}
            <span className="font-semibold text-gray-900">
              {policyNumber.trim() || "Not provided"}
            </span>
          </div>

          {photos.length > 0 && (
            <>
              <div className="rounded-lg bg-blue-50/50 px-4 py-2.5 flex items-center gap-2 text-blue-700 font-semibold text-sm mb-3">
                <Camera className="h-4 w-4" />
                Attached Evidence
              </div>
              <div className="space-y-2">
                {photos.map((photo) => (
                  <div
                    key={photo.id}
                    className="flex items-center gap-3 rounded-xl border border-gray-200 bg-gray-50/50 px-4 py-3"
                  >
                    <FileText className="h-5 w-5 text-gray-400 flex-shrink-0" />
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-gray-800 truncate">
                        {photo.name}
                      </div>
                      <div className="text-xs text-gray-400">
                        {photo.type || "Unknown type"}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {comments.trim().length > 0 && (
                <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50/50 px-4 py-3 text-gray-700 italic">
                  "{comments}"
                </div>
              )}
              <div className="mb-6" />
            </>
          )}

          <div className="rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2.5 flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-white font-semibold text-sm">
              <Database className="h-4 w-4" />
              Section A — Policy &amp; Insured
            </div>
            <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-[11px] font-semibold text-white">
              Verified Data
            </span>
          </div>
          <table className="w-full border-collapse mb-6">
            <thead>
              <tr className="text-left text-sm text-gray-500 border-b border-gray-100">
                <th className="font-medium py-2 pr-4">Field</th>
                <th className="font-medium py-2 pr-4">Value</th>
                <th className="font-medium py-2 text-right">Source</th>
              </tr>
            </thead>
            <tbody>
              {sectionA.length === 0 && (
                <tr>
                  <td
                    colSpan={3}
                    className="py-4 text-sm text-gray-500 text-center"
                  >
                    No verified policy information available.
                  </td>
                </tr>
              )}
              {sectionA.map((row) => (
                <tr key={row.label} className="border-b border-gray-50">
                  <td className="py-3 pr-4 text-sm text-gray-700">{row.label}</td>
                  <td className="py-3 pr-4 text-sm font-medium text-gray-800">
                    {row.value}
                  </td>
                  <td className="py-3 text-right">
                    <SourceTag variant="auto-filled-solid" label="Auto-Filled" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="rounded-lg bg-violet-50 px-4 py-2.5 flex items-center gap-2 text-violet-700 font-semibold text-sm mb-3">
            <Sparkles className="h-4 w-4" />
            Section B — Loss Details
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse min-w-[640px]">
              <thead>
                <tr className="text-left text-sm text-gray-500 border-b border-gray-100">
                  <th className="font-medium py-2 pr-4">Field</th>
                  <th className="font-medium py-2 pr-4">Value</th>
                  <th className="font-medium py-2">Source</th>
                </tr>
              </thead>
              <tbody>
                {lossFields.length === 0 && (
                  <tr>
                    <td
                      colSpan={3}
                      className="py-4 text-sm text-gray-500 text-center"
                    >
                      No extracted loss details available.
                    </td>
                  </tr>
                )}
                {lossFields.map((row) => {
                  const displayValue = row.value ?? "Not specified";
                  const finalValue = humanReview[row.field] ?? displayValue;
                  const edited =
                    humanReview[row.field] !== undefined &&
                    humanReview[row.field] !== (row.value ?? "");
                  return (
                    <tr key={row.field} className="border-b border-gray-50">
                      <td className="py-3 pr-4 text-sm text-gray-700">
                        {row.field}
                        {row.required && <span className="text-red-500"> *</span>}
                      </td>
                      <td className="py-3 pr-4 text-sm font-semibold text-gray-800">
                        {finalValue}
                        {edited && (
                          <span className="ml-2 text-[10px] font-semibold text-blue-600 uppercase">
                            Edited
                          </span>
                        )}
                      </td>
                      <td className="py-3">
                        {edited ? (
                          <SourceTag
                            variant="customer-confirmed-solid"
                            label="Human-Reviewed"
                          />
                        ) : (
                          sourceTagFor(row.source)
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {submitError && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {submitError}
        </div>
      )}

      <div className="flex items-center gap-3 mt-4">
        <button
          type="button"
          onClick={onBack}
          disabled={isSubmitting}
          className="rounded-xl border border-gray-200 px-6 py-3 font-semibold text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          Back
        </button>
        <button
          type="button"
          onClick={onSubmit}
          disabled={isSubmitting}
          className={`flex-1 rounded-xl text-white font-bold py-3 shadow-md transition-colors flex items-center justify-center gap-2 ${
            isSubmitting
              ? "bg-blue-400 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-700"
          }`}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Submitting…
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              Confirm &amp; Submit FNOL
            </>
          )}
        </button>
      </div>
    </div>
  );
}
