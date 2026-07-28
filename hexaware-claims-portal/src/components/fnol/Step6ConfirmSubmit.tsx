import { Sparkles, Check, Pencil, AlertCircle, User, Send } from "lucide-react";
import { SourceTag } from "./SourceTag";
import { aiFields } from "@/lib/fnol-data";

export function Step6ConfirmSubmit({
  confirmed,
  onConfirmedChange,
  onSubmit,
  onBack,
}: {
  confirmed: boolean[];
  onConfirmedChange: (value: boolean[]) => void;
  onSubmit: () => void;
  onBack: () => void;
}) {
  const total = aiFields.length;

  const confirmedCount = confirmed.filter(Boolean).length;
  const remaining = total - confirmedCount;
  const allConfirmed = remaining === 0;

  const confirmOne = (idx: number) =>
    onConfirmedChange(confirmed.map((v, i) => (i === idx ? true : v)));
  const confirmAll = () => onConfirmedChange(aiFields.map(() => true));

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="rounded-xl border border-violet-100 bg-gradient-to-br from-violet-50/70 to-blue-50/40 p-6">
        <div className="flex items-center gap-2 text-violet-700 font-bold">
          <Sparkles className="h-5 w-5" />
          Confirm AI-Inferred Information
        </div>
        <p className="text-sm text-gray-600 mt-1">
          These fields were detected by AI from your description. You{" "}
          <span className="font-semibold text-gray-800">must confirm each one</span>{" "}
          before submitting.
        </p>

        <div className="mt-5 rounded-lg bg-white border border-gray-100 px-4 py-3 flex items-center justify-between shadow-sm">
          <div>
            <div className="text-sm font-semibold text-gray-800">
              AI Fields Confirmation Progress
            </div>
            <div className="text-xs text-gray-500">
              Submission blocked until all AI fields are confirmed
            </div>
          </div>
          <span
            className={`rounded-full px-3 py-1 text-xs font-bold ${
              allConfirmed
                ? "bg-emerald-100 text-emerald-700"
                : "bg-violet-100 text-violet-700"
            }`}
          >
            {confirmedCount} / {total} Confirmed
          </span>
        </div>

        <div className="mt-5 space-y-4">
          {aiFields.map((field, idx) => {
            const isConfirmed = confirmed[idx];
            return (
              <div
                key={field.label}
                className={`rounded-lg border bg-white p-4 ${
                  isConfirmed ? "border-emerald-200" : "border-gray-200"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <SourceTag variant="ai-inferred" label="AI-Inferred" />
                      <span className="text-xs text-gray-400">
                        {field.confidence}% confidence
                      </span>
                      {field.required && (
                        <span className="text-[11px] font-semibold text-red-500">
                          Required
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-400 mt-2">{field.label}</div>
                    <div className="text-base font-bold text-gray-900">
                      {field.value}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-gray-400 mt-1.5">
                      <AlertCircle className="h-3 w-3" />
                      Extracted from: {field.extractedFrom}
                    </div>
                  </div>

                  <div className="flex flex-col gap-2 flex-shrink-0">
                    <button
                      type="button"
                      onClick={() => confirmOne(idx)}
                      disabled={isConfirmed}
                      className={`flex items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white transition-colors ${
                        isConfirmed
                          ? "bg-emerald-400 cursor-default"
                          : "bg-emerald-500 hover:bg-emerald-600"
                      }`}
                    >
                      <Check className="h-4 w-4" />
                      {isConfirmed ? "Confirmed" : "Confirm"}
                    </button>
                    <button
                      type="button"
                      className="flex items-center justify-center gap-1.5 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                      Edit
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-5">
        <div className="flex items-center gap-2 text-blue-700 font-semibold">
          <User className="h-4 w-4" />
          Customer-Provided Information (Already Verified)
        </div>
        <div className="mt-3 flex items-center justify-between">
          <div>
            <div className="text-xs text-gray-400">Emergency Services Contacted</div>
            <div className="text-sm font-bold text-gray-900">Yes</div>
          </div>
          <SourceTag variant="verified" label="Verified" />
        </div>
      </div>

      {!allConfirmed && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-amber-700 text-sm font-medium">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            Please confirm all {remaining} remaining AI-inferred field
            {remaining === 1 ? "" : "s"} to submit your claim.
          </div>
          <button
            type="button"
            onClick={confirmAll}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-600 transition-colors flex-shrink-0"
          >
            <Check className="h-4 w-4" />
            Confirm All
          </button>
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          className="rounded-xl border border-gray-200 px-6 py-3 font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Back to Report
        </button>
        <button
          type="button"
          onClick={onSubmit}
          disabled={!allConfirmed}
          className={`flex-1 rounded-xl py-3 font-bold text-white shadow-md transition-colors flex items-center justify-center gap-2 ${
            allConfirmed
              ? "bg-blue-600 hover:bg-blue-700"
              : "bg-blue-300 cursor-not-allowed"
          }`}
        >
          <Send className="h-4 w-4" />
          Confirm &amp; Submit FNOL
        </button>
      </div>
    </div>
  );
}
