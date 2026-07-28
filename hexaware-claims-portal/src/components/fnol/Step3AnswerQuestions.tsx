import { MessageSquare, AlertCircle, Pencil, HelpCircle, User } from "lucide-react";
import { SourceTag } from "./SourceTag";
import { customerText, questions } from "@/lib/fnol-data";

export function Step3AnswerQuestions({
  index,
  onIndexChange,
  onNext,
}: {
  index: number;
  onIndexChange: (value: number) => void;
  onNext: () => void;
}) {
  const total = questions.length;
  const current = questions[index];

  const handleAnswer = () => {
    if (index < total - 1) {
      onIndexChange(index + 1);
    } else {
      onNext();
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 text-blue-700 font-semibold">
            <MessageSquare className="h-4 w-4" />
            What You Told Us (Text)
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
        <div className="rounded-lg border border-gray-200 bg-gray-50/50 px-4 py-3 text-gray-700">
          "We understand there was a{" "}
          <span className="font-semibold text-violet-600">sudden</span>{" "}
          <span className="font-semibold text-pink-600">water damage</span> in your{" "}
          <span className="font-semibold text-violet-600">not specified</span> caused by{" "}
          <span className="font-semibold text-pink-600">unknown - needs clarification</span>."
        </div>
        <div className="mt-3">
          <SourceTag variant="ai-generated-summary" label="AI-Generated Summary" />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-blue-700 font-semibold">
            <HelpCircle className="h-4 w-4" />
            We Need More Information
          </div>
          <span className="rounded-full border border-gray-200 px-2.5 py-0.5 text-xs font-medium text-gray-500">
            {index + 1} of {total}
          </span>
        </div>

        <div className="h-1.5 w-full rounded-full bg-gray-100 mb-5">
          <div
            className="h-full rounded-full bg-blue-600 transition-all"
            style={{ width: `${((index + 1) / total) * 100}%` }}
          />
        </div>

        <p className="text-gray-800 font-medium mb-4">{current.question}</p>

        <div className="space-y-3">
          {current.options.map((option) => (
            <button
              key={option}
              type="button"
              onClick={handleAnswer}
              className="w-full text-left rounded-lg border border-gray-200 px-4 py-3 text-gray-700 hover:border-blue-400 hover:bg-blue-50/40 transition-colors"
            >
              {option}
            </button>
          ))}
        </div>

        <div className="mt-4 flex items-center gap-1.5 text-xs text-gray-400">
          <User className="h-3.5 w-3.5" />
          Your answer will be marked as "Customer-Provided"
        </div>
      </div>
    </div>
  );
}
