import { cn } from "@/lib/utils";

interface StatusPillProps {
  status: string;
  className?: string;
}

export function StatusPill({ status, className }: StatusPillProps) {
  let bgColor = "bg-gray-100 text-gray-700 border-gray-200";

  switch (status.toLowerCase()) {
    case "approved":
      bgColor = "bg-emerald-50 text-emerald-700 border-emerald-200";
      break;
    case "pending":
      bgColor = "bg-amber-50 text-amber-700 border-amber-200";
      break;
    case "loss investigation":
      bgColor = "bg-purple-50 text-purple-700 border-purple-200";
      break;
    case "claim intake validation":
      bgColor = "bg-cyan-50 text-cyan-700 border-cyan-200";
      break;
    case "under review":
      bgColor = "bg-transparent text-gray-600 border-gray-300 border-dashed";
      break;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        bgColor,
        className
      )}
    >
      {status}
    </span>
  );
}
