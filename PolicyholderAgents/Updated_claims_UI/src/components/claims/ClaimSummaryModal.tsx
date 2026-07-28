import { useEffect } from "react";
import type { ClaimRecord } from "@/lib/claims-data";
import { FileText, X } from "lucide-react";

interface ClaimSummaryModalProps {
  claim: ClaimRecord | null;
  onClose: () => void;
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      <div className="text-base font-semibold text-gray-900">{value}</div>
    </div>
  );
}

function SectionHeader({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span className={`h-1 w-6 rounded-full ${color}`} />
      <h3 className="text-sm font-bold tracking-wide text-gray-700 uppercase">
        {label}
      </h3>
    </div>
  );
}

export function ClaimSummaryModal({ claim, onClose }: ClaimSummaryModalProps) {
  useEffect(() => {
    if (!claim) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [claim, onClose]);

  if (!claim) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Claim Summary"
      >
        {/* Header */}
        <div className="flex items-center justify-between bg-gradient-to-r from-emerald-500 to-teal-500 px-6 py-4 text-white flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <FileText className="h-5 w-5" />
            <h2 className="text-lg font-bold">Claim Summary</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-white/80 hover:text-white hover:bg-white/20 transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto px-6 py-6 space-y-6">
          <section>
            <SectionHeader color="bg-emerald-500" label="Claim Information" />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
              <Field label="Claim Number" value={claim.id} />
              <Field label="Policyholder" value={claim.policyholder} />
              <Field label="Policy Number" value={claim.policyNumber} />
              <Field label="Date Filed" value={claim.dateFiled} />
            </div>
          </section>

          <div className="border-t border-gray-100" />

          <section>
            <SectionHeader color="bg-fuchsia-500" label="Claim Details" />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
              <Field label="Loss Type" value={claim.type} />
              <Field label="Date of Loss" value={claim.dateOfLoss} />
              <Field label="Property / Location" value={claim.location} />
              <Field label="Estimated Cost" value={claim.estimatedCost} />
              <Field label="Severity" value={claim.severity} />
              <div>
                <div className="text-xs text-gray-400 mb-1">Coverage</div>
                {claim.coverage.toLowerCase() === "covered" ? (
                  <span className="inline-flex items-center rounded-full bg-emerald-500 px-3 py-1 text-xs font-bold text-white">
                    Covered
                  </span>
                ) : (
                  <span className="inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-700">
                    {claim.coverage}
                  </span>
                )}
              </div>
            </div>
            <div className="mt-4">
              <div className="text-xs text-gray-400 mb-1">Short Description</div>
              <p className="text-base font-semibold text-gray-900">
                {claim.assessmentSummary}
              </p>
            </div>
          </section>

          <div className="border-t border-gray-100" />

          <section>
            <SectionHeader color="bg-orange-500" label="Assessment Summary" />
            <p className="text-sm text-gray-700 leading-relaxed">
              {claim.assessmentSummary}
            </p>
            <p className="mt-3 text-xs text-gray-400">
              AI Confidence:{" "}
              {claim.aiConfidence === null
                ? "Not scored"
                : `${claim.aiConfidence}%`}
            </p>
          </section>
        </div>

        {/* Footer */}
        <div className="flex justify-end border-t border-gray-100 px-6 py-4 flex-shrink-0">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
