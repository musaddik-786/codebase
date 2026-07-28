import { cn } from "@/lib/utils";
import { Check, ChevronRight } from "lucide-react";

const STEP_LABELS = ["Policy Lookup", "Answer Questions", "Review Form"];

export function StepTracker({
  currentStep,
  onStepClick,
}: {
  currentStep: number;
  onStepClick?: (step: number) => void;
}) {
  return (
    <div className="mb-8 overflow-x-auto">
      <div className="flex items-center justify-between gap-1 min-w-[420px] max-w-3xl mx-auto">
        {STEP_LABELS.map((label, idx) => {
          const stepNum = idx + 1;
          const completed = stepNum < currentStep;
          const active = stepNum === currentStep;
          const clickable = Boolean(onStepClick) && stepNum <= currentStep;

          return (
            <div
              key={label}
              className={cn(
                "flex items-center gap-1",
                idx < STEP_LABELS.length - 1 ? "flex-1" : "flex-none"
              )}
            >
              <button
                type="button"
                disabled={!clickable}
                onClick={() => clickable && onStepClick?.(stepNum)}
                aria-current={active ? "step" : undefined}
                className={cn(
                  "flex items-center gap-2 rounded-full transition-colors",
                  clickable
                    ? "cursor-pointer hover:opacity-80"
                    : "cursor-default"
                )}
              >
                <div
                  className={cn(
                    "h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold border-2 flex-shrink-0",
                    completed
                      ? "bg-emerald-500 border-emerald-500 text-white"
                      : active
                        ? "bg-blue-600 border-blue-600 text-white shadow-md shadow-blue-200"
                        : "bg-white border-gray-200 text-gray-400",
                    clickable && "hover:ring-2 hover:ring-blue-200"
                  )}
                >
                  {completed ? <Check className="h-4 w-4" /> : stepNum}
                </div>
                <span
                  className={cn(
                    "text-[11px] leading-tight font-medium w-20 text-left",
                    active
                      ? "text-blue-600"
                      : completed
                        ? "text-gray-700"
                        : "text-gray-400"
                  )}
                >
                  {label}
                </span>
              </button>
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
