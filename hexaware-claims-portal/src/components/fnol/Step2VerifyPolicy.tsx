import {
  MessageSquare,
  AlertCircle,
  Pencil,
  Shield,
  FileText,
  User,
  MapPin,
  Calendar,
  Check,
  type LucideIcon,
} from "lucide-react";
import { SourceTag, ConfidenceBadge } from "./SourceTag";
import { customerText, extractedRows, policyInfo } from "@/lib/fnol-data";

const fieldIcons: Record<string, LucideIcon> = {
  "Policy Number": FileText,
  "Insured Name": User,
  "Insured Address": MapPin,
  "Policy Period": Calendar,
};

export function Step2VerifyPolicy({ onNext }: { onNext: () => void }) {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 text-blue-700 font-semibold">
            <MessageSquare className="h-4 w-4" />
            What You Told Us
          </div>
          <button
            type="button"
            className="flex items-center gap-1.5 border border-gray-200 rounded-lg px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <Pencil className="h-3.5 w-3.5" />
            Edit
          </button>
        </div>
        <div className="rounded-lg border border-gray-200 bg-gray-50/50 px-4 py-3 text-gray-700 italic">
          "{customerText} "
        </div>
        <div className="mt-3">
          <SourceTag variant="customer-provided" label="Customer-Provided" />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-2 text-violet-700 font-semibold mb-4">
          <AlertCircle className="h-4 w-4" />
          What AI Extracted From Your Description
        </div>

        <table className="w-full border-collapse">
          <thead>
            <tr className="text-left text-sm text-gray-500 border-b border-gray-100">
              <th className="font-medium py-2 pr-4">Data Element</th>
              <th className="font-medium py-2 pr-4">AI Extracted Value</th>
              <th className="font-medium py-2 text-right">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {extractedRows.map((row) => {
              const high = row.confidence >= 87;
              return (
                <tr
                  key={row.element}
                  className={
                    high ? "bg-emerald-50/40" : "bg-amber-50/40"
                  }
                >
                  <td className="py-3 pr-4 text-sm font-semibold text-gray-800">
                    {row.element}
                  </td>
                  <td className="py-3 pr-4 text-sm text-gray-600">{row.value}</td>
                  <td className="py-3 text-right">
                    <ConfidenceBadge value={row.confidence} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        <div className="mt-4">
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-violet-600">
            <AlertCircle className="h-3.5 w-3.5" />
            AI-Inferred (Tentative - needs your confirmation)
          </span>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-emerald-200 shadow-sm p-6">
        <div className="flex items-center gap-2 text-emerald-700 font-semibold">
          <Shield className="h-4 w-4" />
          Your Policy Information
        </div>
        <p className="text-sm text-gray-500 mt-1 mb-4">
          Retrieved from policy system. Please confirm.
        </p>

        <div className="space-y-3">
          {policyInfo.map((field) => {
            const Icon = fieldIcons[field.label] ?? FileText;
            return (
              <div
                key={field.label}
                className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                  <div>
                    <div className="text-xs text-gray-400">{field.label}</div>
                    <div className="text-sm font-semibold text-gray-800">
                      {field.value}
                    </div>
                  </div>
                </div>
                <SourceTag variant="auto-filled" label="Auto-Filled" />
              </div>
            );
          })}
        </div>

        <button
          type="button"
          onClick={onNext}
          className="w-full mt-6 py-3.5 rounded-xl bg-emerald-600 text-white font-bold shadow-md hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2"
        >
          <Check className="h-5 w-5" />
          Confirm &amp; Continue
        </button>
      </div>
    </div>
  );
}
