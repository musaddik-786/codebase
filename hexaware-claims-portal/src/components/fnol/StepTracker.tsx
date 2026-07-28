import { cn } from "@/lib/utils";
import { Check, ChevronRight } from "lucide-react";

const STEP_LABELS = [
  "Describe Loss",
  "Verify Policy",
  "Answer Questions",
  "Add Evidence",
  "Review Form",
  "Confirm & Submit",
];

export function StepTracker({ currentStep }: { currentStep: number }) {
  return (
    <div className="mb-8 overflow-x-auto">
      <div className="flex items-center justify-between gap-1 min-w-[680px] max-w-5xl mx-auto">
        {STEP_LABELS.map((label, idx) => {
          const stepNum = idx + 1;
          const completed = stepNum < currentStep;
          const active = stepNum === currentStep;

          return (
            <div
              key={label}
              className={cn(
                "flex items-center gap-1",
                idx < STEP_LABELS.length - 1 ? "flex-1" : "flex-none"
              )}
            >
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    "h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold border-2 flex-shrink-0",
                    completed
                      ? "bg-emerald-500 border-emerald-500 text-white"
                      : active
                        ? "bg-blue-600 border-blue-600 text-white shadow-md shadow-blue-200"
                        : "bg-white border-gray-200 text-gray-400"
                  )}
                >
                  {completed ? <Check className="h-4 w-4" /> : stepNum}
                </div>
                <span
                  className={cn(
                    "text-[11px] leading-tight font-medium w-16",
                    active
                      ? "text-blue-600"
                      : completed
                        ? "text-gray-700"
                        : "text-gray-400"
                  )}
                >
                  {label}
                </span>
              </div>
              {idx < STEP_LABELS.length - 1 && (
                <ChevronRight className="h-4 w-4 text-gray-300 flex-shrink-0" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
