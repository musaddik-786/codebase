import { GradientBanner } from "@/components/ui/GradientBanner";
import { Search, FolderOpen, Upload, Eye, FileText, FileImage, Calculator, Receipt } from "lucide-react";

export default function DocumentHub() {
  return (
    <div className="animate-in fade-in duration-500 h-full flex flex-col">
      <GradientBanner
        title="Document Hub"
        subtitle="Centralized document workspace — upload, AI-classify, extract data, and track every artifact for a claim."
        badge="AI-Powered"
        icon={<FolderOpen className="h-5 w-5" />}
        className="mb-6 flex-shrink-0"
      >
        <div className="flex flex-wrap items-center gap-4 pt-4 border-t border-white/10 mt-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/50" />
            <input 
              type="text" 
              placeholder="Search claim # or name..." 
              className="w-full pl-9 pr-4 py-2 rounded-lg bg-black/20 border border-white/10 focus:border-white/30 focus:bg-black/30 outline-none text-sm text-white placeholder-white/50"
            />
          </div>
          
          <select className="bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-sm text-white outline-none focus:bg-black/30 appearance-none min-w-[250px]">
            <option className="text-gray-900">FNOL-2026-483729 — FNTest_132 L...</option>
          </select>

          <button className="flex items-center gap-2 bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2 rounded-lg text-white font-medium shadow-md hover:shadow-lg transition-all border border-blue-400/30 text-sm whitespace-nowrap">
            <Upload className="h-4 w-4" />
            Upload Document
          </button>
        </div>
        
        <div className="flex items-center gap-3 mt-4 text-xs font-medium text-white/80">
          <span className="bg-black/20 px-2.5 py-1 rounded-md border border-white/10">Claim: FNOL-2026-483729</span>
          <span className="bg-black/20 px-2.5 py-1 rounded-md border border-white/10">Type: water damage</span>
          <span className="bg-black/20 px-2.5 py-1 rounded-md border border-white/10 text-purple-200">Status: Loss Investigation</span>
        </div>
      </GradientBanner>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-[400px]">
        {/* Left Column: Filters */}
        <div className="lg:col-span-3 bg-white rounded-xl border border-gray-200 shadow-sm p-4 flex flex-col">
          <h3 className="font-semibold text-gray-900 mb-4 px-2">Filters</h3>
          <div className="space-y-1">
            <FilterItem icon={<FolderOpen />} label="All Documents" count={0} active />
            <FilterItem icon={<FileImage />} label="Photos" count={0} />
            <FilterItem icon={<FileText />} label="Reports" count={0} />
            <FilterItem icon={<Calculator />} label="Estimates" count={0} />
            <FilterItem icon={<Receipt />} label="Invoices" count={0} />
          </div>
        </div>

        {/* Center Column: Documents */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b border-gray-100 p-4">
            <h3 className="font-semibold text-gray-900">Documents (0)</h3>
            <div className="flex bg-gray-100 p-1 rounded-lg">
              <button className="px-3 py-1 text-xs font-medium bg-white shadow-sm rounded-md text-gray-900">List</button>
              <button className="px-3 py-1 text-xs font-medium text-gray-500 hover:text-gray-900">Timeline</button>
            </div>
          </div>
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-gray-50/50">
            <div className="h-16 w-16 bg-gray-100 rounded-full flex items-center justify-center text-gray-400 mb-4">
              <FolderOpen className="h-8 w-8" />
            </div>
            <h4 className="text-gray-900 font-medium mb-1">No documents yet for this claim.</h4>
            <p className="text-sm text-gray-500 max-w-[250px]">
              Upload a file to see AI classification & extraction in action.
            </p>
          </div>
        </div>

        {/* Right Column: AI Insights */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col overflow-hidden">
          <div className="border-b border-gray-100 p-4 flex items-center gap-2">
            <div className="h-6 w-6 rounded bg-purple-100 text-purple-700 flex items-center justify-center">
              <Eye className="h-3.5 w-3.5" />
            </div>
            <h3 className="font-semibold text-gray-900">AI Insights & Extracted Data</h3>
          </div>
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-gray-50/50">
            <p className="text-sm text-gray-500 max-w-[200px]">
              Select a document to view AI insights and extracted fields.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-6 bg-blue-50/50 border border-blue-100 rounded-lg p-4 text-xs text-gray-600">
        <span className="font-semibold text-gray-900">Access Rules:</span> Policyholders see their own docs and shared items only. Adjusters have full access and may override classifications. SIU has full access plus flagged-doc visibility and can add investigation notes. Vendors see only docs for their assigned claim.
      </div>
    </div>
  );
}

function FilterItem({ icon, label, count, active = false }: { icon: React.ReactNode; label: string; count: number; active?: boolean }) {
  return (
    <button 
      className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
        active ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-600 hover:bg-gray-50"
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`[&>svg]:h-4 [&>svg]:w-4 ${active ? "text-blue-600" : "text-gray-400"}`}>
          {icon}
        </div>
        {label}
      </div>
      <span className={`px-2 py-0.5 rounded-full text-xs ${
        active ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-500"
      }`}>
        {count}
      </span>
    </button>
  );
}
