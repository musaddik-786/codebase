import { GradientBanner } from "@/components/ui/GradientBanner";
import { StatusPill } from "@/components/ui/StatusPill";
import { mockClaims } from "@/data/mock";
import { Search, FileText, ChevronRight, Eye } from "lucide-react";

export default function FollowMyClaims() {
  return (
    <div className="animate-in fade-in duration-500">
      <GradientBanner
        title="Claim Journey Workspace"
        subtitle="Track your claims progress in real-time"
        rightContent={
          <button className="flex items-center gap-2 bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2 rounded-lg text-white font-medium shadow-md hover:shadow-lg transition-all border border-blue-500/50">
            <Eye className="h-4 w-4" />
            Customer View
          </button>
        }
      />

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mb-6">
        <div className="bg-gradient-to-r from-[#1e1b4b]/10 to-[#5b21b6]/10 p-4 border-b border-gray-200 flex items-center gap-3">
          <FileText className="h-5 w-5 text-indigo-700" />
          <h2 className="font-semibold text-indigo-950">Select a Claim to Track</h2>
        </div>
        
        <div className="p-4 border-b border-gray-100">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input 
              type="text" 
              placeholder="Search by claim number, name, or loss type..." 
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-sm transition-shadow bg-gray-50/50"
            />
          </div>
        </div>

        <div className="divide-y divide-gray-100">
          {mockClaims.map((claim) => (
            <div 
              key={claim.id} 
              className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors cursor-pointer group"
            >
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-100 to-blue-50 flex items-center justify-center border border-indigo-100 group-hover:scale-105 transition-transform">
                  <FileText className="h-5 w-5 text-indigo-600" />
                </div>
                <div>
                  <div className="font-semibold text-gray-900">{claim.id}</div>
                  <div className="text-sm text-gray-500 capitalize">{claim.type.toLowerCase()}</div>
                </div>
              </div>
              
              <div className="flex items-center gap-4">
                <StatusPill status={claim.status} />
                <ChevronRight className="h-5 w-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
