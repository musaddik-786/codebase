import {
  FileText,
  MessageSquare,
  Database,
  Sparkles,
  AlertTriangle,
  ChevronRight,
  Camera,
} from "lucide-react";
import { SourceTag } from "./SourceTag";
import type { EvidencePhoto } from "./Step4AddEvidence";
import { customerText, sectionA, sectionB, type LossSource } from "@/lib/fnol-data";

const sourceTagFor = (source: LossSource) => {
  switch (source) {
    case "AI-Inferred":
      return <SourceTag variant="ai-inferred-solid" label="AI-Inferred" />;
    case "Customer-Confirmed":
      return <SourceTag variant="customer-confirmed-solid" label="Customer-Confirmed" />;
    case "Customer-Provided":
      return <SourceTag variant="customer-provided-solid" label="Customer-Provided" />;
  }
};

export function Step5ReviewForm({
  comments,
  photos,
  onNext,
  onBack,
}: {
  comments: string;
  photos: EvidencePhoto[];
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <div className="max-w-5xl mx-auto">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="bg-gradient-to-r from-slate-900 to-slate-800 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-white font-bold">
            <FileText className="h-5 w-5" />
            PRE-FILLED FNOL REPORT
          </div>
          <span className="rounded-full border border-white/30 px-3 py-1 text-[11px] font-semibold text-white/90">
            DRAFT - REVIEW REQUIRED
          </span>
        </div>

        <div className="p-6">
          <div className="flex flex-wrap items-center gap-2 mb-6">
            <span className="text-sm font-semibold text-gray-600 mr-1">
              Data Source Legend:
            </span>
            <SourceTag variant="customer-provided" label="Customer-Provided" />
            <SourceTag variant="ai-inferred" label="AI-Inferred" />
            <SourceTag variant="auto-filled" label="Auto-Filled (Policy System)" />
          </div>

          <div className="rounded-lg bg-blue-50/50 px-4 py-2.5 flex items-center gap-2 text-blue-700 font-semibold text-sm mb-3">
            <MessageSquare className="h-4 w-4" />
            Original Customer Text Input
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50/50 px-4 py-3 text-gray-700 italic">
            "{customerText} "
          </div>
          <div className="mt-3 mb-6">
            <SourceTag variant="customer-provided" label="Customer-Provided" />
          </div>

          {(photos.length > 0 || comments.trim().length > 0) && (
            <>
              <div className="rounded-lg bg-blue-50/50 px-4 py-2.5 flex items-center gap-2 text-blue-700 font-semibold text-sm mb-3">
                <Camera className="h-4 w-4" />
                Attached Evidence
              </div>
              {photos.length > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                  {photos.map((photo) => (
                    <div
                      key={photo.id}
                      className="rounded-xl overflow-hidden border border-gray-200 bg-gray-50"
                    >
                      <img
                        src={photo.url}
                        alt={photo.name}
                        className="h-28 w-full object-cover"
                      />
                      <div className="px-2 py-1.5 text-[11px] text-gray-500 truncate">
                        {photo.name}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-gray-200 bg-gray-50/50 px-4 py-3 text-sm text-gray-400 italic">
                  No photos attached.
                </div>
              )}
              {comments.trim().length > 0 && (
                <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50/50 px-4 py-3 text-gray-700 italic">
                  "{comments}"
                </div>
              )}
              <div className="mt-3 mb-6">
                <SourceTag variant="customer-provided" label="Customer-Provided" />
              </div>
            </>
          )}

          <div className="rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2.5 flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-white font-semibold text-sm">
              <Database className="h-4 w-4" />
              Section A — Policy &amp; Insured (Auto-Filled from Policy System)
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
            Section B — Loss Details (Mixed Sources)
          </div>
          <div className="overflow-x-auto mb-6">
            <table className="w-full border-collapse min-w-[640px]">
              <thead>
                <tr className="text-left text-sm text-gray-500 border-b border-gray-100">
                  <th className="font-medium py-2 pr-4">Field</th>
                  <th className="font-medium py-2 pr-4">Value</th>
                  <th className="font-medium py-2 pr-4">Source</th>
                  <th className="font-medium py-2">Extracted From</th>
                </tr>
              </thead>
              <tbody>
                {sectionB.map((row) => (
                  <tr key={row.field} className="border-b border-gray-50">
                    <td className="py-3 pr-4 text-sm text-gray-700">
                      {row.field}
                      {row.required && <span className="text-red-500"> *</span>}
                    </td>
                    <td className="py-3 pr-4 text-sm font-semibold text-gray-800">
                      {row.value}
                    </td>
                    <td className="py-3 pr-4">{sourceTagFor(row.source)}</td>
                    <td className="py-3 text-sm text-gray-400 italic">
                      {row.extractedFrom}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="rounded-lg bg-amber-50 border border-amber-100 px-4 py-4">
            <div className="flex items-center gap-2 text-amber-700 font-semibold text-sm mb-3">
              <AlertTriangle className="h-4 w-4" />
              Section D — AI Assumptions &amp; Confidence
            </div>
            <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
              <ul className="space-y-1.5 text-sm text-gray-600">
                <li>• 6 fields were inferred by AI and require your confirmation</li>
                <li>• 1 fields were provided directly by you</li>
                <li>• 3 fields were auto-filled from policy system</li>
              </ul>
              <div className="text-right">
                <div className="text-xs text-gray-500">Overall AI Confidence</div>
                <div className="text-4xl font-extrabold text-amber-500">90%</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 mt-6">
        <button
          type="button"
          onClick={onBack}
          className="rounded-xl border border-gray-200 px-6 py-3 font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
        <button
          type="button"
          onClick={onNext}
          className="flex-1 rounded-xl bg-blue-600 text-white font-bold py-3 shadow-md hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
        >
          Review &amp; Confirm AI Fields
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
