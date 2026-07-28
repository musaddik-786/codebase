import { cn } from "@/lib/utils";
import {
  User,
  AlertCircle,
  Database,
  CheckCircle2,
  type LucideIcon,
} from "lucide-react";

type Variant =
  | "customer-provided"
  | "ai-inferred"
  | "auto-filled"
  | "ai-generated-summary"
  | "verified"
  | "auto-filled-solid"
  | "ai-inferred-solid"
  | "customer-confirmed-solid"
  | "customer-provided-solid";

const variants: Record<Variant, { cls: string; Icon: LucideIcon }> = {
  "customer-provided": {
    cls: "bg-blue-50 text-blue-600 border border-blue-100",
    Icon: User,
  },
  "ai-inferred": {
    cls: "bg-violet-50 text-violet-600 border border-violet-100",
    Icon: AlertCircle,
  },
  "auto-filled": {
    cls: "bg-emerald-50 text-emerald-600 border border-emerald-100",
    Icon: Database,
  },
  "ai-generated-summary": {
    cls: "bg-violet-50 text-violet-600 border border-violet-100",
    Icon: AlertCircle,
  },
  verified: {
    cls: "bg-emerald-50 text-emerald-600 border border-emerald-100",
    Icon: CheckCircle2,
  },
  "auto-filled-solid": {
    cls: "bg-indigo-900 text-white",
    Icon: Database,
  },
  "ai-inferred-solid": {
    cls: "bg-violet-600 text-white",
    Icon: AlertCircle,
  },
  "customer-confirmed-solid": {
    cls: "bg-emerald-500 text-white",
    Icon: CheckCircle2,
  },
  "customer-provided-solid": {
    cls: "bg-emerald-500 text-white",
    Icon: User,
  },
};

interface SourceTagProps {
  variant: Variant;
  label: string;
  className?: string;
}

export function SourceTag({ variant, label, className }: SourceTagProps) {
  const { cls, Icon } = variants[variant];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold whitespace-nowrap",
        cls,
        className
      )}
    >
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}

export function ConfidenceBadge({
  value,
  className,
}: {
  value: number;
  className?: string;
}) {
  const high = value >= 87;
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full px-2.5 py-0.5 text-[11px] font-bold text-white",
        high ? "bg-emerald-500" : "bg-amber-500",
        className
      )}
    >
      {value}%
    </span>
  );
}

export function ConfidenceIndicator({
  value,
  className,
}: {
  value: number | null;
  className?: string;
}) {
  if (value === null || value === undefined) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-full border border-gray-200 bg-gray-100 px-2.5 py-0.5 text-[11px] font-semibold text-gray-500",
          className
        )}
      >
        <AlertCircle className="h-3 w-3" />
        Not scored
      </span>
    );
  }
  return <ConfidenceBadge value={value} className={className} />;
}
