import { GradientBanner } from "@/components/ui/GradientBanner";
import { Sparkles } from "lucide-react";

export default function ComingSoon({ title }: { title: string }) {
  return (
    <div className="animate-in fade-in duration-500">
      <GradientBanner
        title={title}
        subtitle="This module is on the roadmap."
        icon={<Sparkles className="h-5 w-5" />}
      />

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 flex flex-col items-center justify-center text-center mt-6">
        <div className="h-16 w-16 bg-blue-50 rounded-full flex items-center justify-center text-blue-600 mb-4">
          <Sparkles className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Coming Soon</h2>
        <p className="text-gray-500 max-w-md">
          The {title} module is currently under development and will be available in an
          upcoming release.
        </p>
      </div>
    </div>
  );
}
