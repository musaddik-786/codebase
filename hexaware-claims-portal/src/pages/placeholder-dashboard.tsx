import { GradientBanner } from "@/components/ui/GradientBanner";
import { usePersona } from "@/lib/persona-context";
import { LayoutDashboard } from "lucide-react";

export default function PlaceholderDashboard() {
  const { activePersona } = usePersona();

  return (
    <div className="animate-in fade-in duration-500">
      <GradientBanner
        title={activePersona.portalTitle}
        subtitle={`Welcome to the ${activePersona.role} workspace.`}
        icon={<LayoutDashboard className="h-5 w-5" />}
      />

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 flex flex-col items-center justify-center text-center mt-6">
        <div className="h-16 w-16 bg-blue-50 rounded-full flex items-center justify-center text-blue-600 mb-4">
          <LayoutDashboard className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Workspace Coming Soon</h2>
        <p className="text-gray-500 max-w-md">
          This portal view for the {activePersona.role} persona is currently under development. 
          Please switch to the Policyholder persona to view the full experience.
        </p>
      </div>
    </div>
  );
}
