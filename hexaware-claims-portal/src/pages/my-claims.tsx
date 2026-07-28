import { GradientBanner } from "@/components/ui/GradientBanner";
import { StatusPill } from "@/components/ui/StatusPill";
import { mockClaims } from "@/data/mock";
import { Calendar, FileText, MapPin, Plus } from "lucide-react";

export default function MyClaims() {
  const getBorderColor = (type: string) => {
    switch (type.toLowerCase()) {
      case "collision": return "border-l-blue-500";
      case "water damage": return "border-l-cyan-500";
      case "wind/hail": return "border-l-violet-500";
      case "theft": return "border-l-rose-500";
      case "fire": return "border-l-orange-500";
      default: return "border-l-gray-400";
    }
  };

  return (
    <div className="animate-in fade-in duration-500">
      <GradientBanner
        title="My Claims"
        subtitle="View and track all your submitted insurance claims"
        rightContent={
          <button className="flex items-center gap-2 bg-white/20 hover:bg-white/30 backdrop-blur-sm px-4 py-2 rounded-lg text-white font-medium transition-colors border border-white/10">
            <Plus className="h-4 w-4" />
            File New Claim
          </button>
        }
      />

      <div className="grid gap-4 mt-6">
        {mockClaims.map((claim) => (
          <div 
            key={claim.id} 
            className={`bg-white rounded-xl border border-gray-200 shadow-sm p-6 hover:shadow-md transition-shadow border-l-4 ${getBorderColor(claim.type)}`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
              <div className="flex items-center gap-4">
                <span className="font-mono text-sm text-gray-500 bg-gray-50 px-2 py-1 rounded border border-gray-100">
                  {claim.id}
                </span>
                <StatusPill status={claim.status} />
              </div>
            </div>
            
            <h3 className="text-lg font-bold text-gray-900 mb-4">{claim.description}</h3>
            
            <div className="flex flex-wrap items-center gap-6 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-gray-400" />
                {claim.date}
              </div>
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-gray-400" />
                {claim.type}
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-gray-400" />
                {claim.location}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
