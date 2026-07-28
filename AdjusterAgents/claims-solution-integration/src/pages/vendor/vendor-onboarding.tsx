import { useState } from "react";
import { Upload, MapPin, Sparkles, Mail, Phone, FileText, CheckCircle2, XCircle, UserPlus, ClipboardList, ShieldCheck, Calendar } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { pendingApprovals, processedApplications, serviceAreaStates, specializations, PendingVendor } from "@/lib/vendor-data";

export default function VendorOnboarding() {
  const { toast } = useToast();
  const [pending, setPending] = useState<PendingVendor[]>(pendingApprovals);
  const [processed, setProcessed] = useState<PendingVendor[]>(processedApplications);
  const [licenseNumber, setLicenseNumber] = useState("");
  const [licenseExpiry, setLicenseExpiry] = useState("");
  const [serviceAreas, setServiceAreas] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  const decide = (vendor: PendingVendor, decision: "Approved" | "Rejected") => {
    setPending((prev) => prev.filter((p) => p.name !== vendor.name));
    setProcessed((prev) => [{ ...vendor, status: decision }, ...prev]);
    toast({
      title: decision === "Approved" ? "Vendor Approved" : "Vendor Rejected",
      description: `${vendor.name} has been ${decision.toLowerCase()}.`,
    });
  };

  const submitApplication = () => {
    toast({
      title: "Application Submitted",
      description: "Vendor application has been submitted for review.",
    });
  };

  const addState = (st: string) => {
    const parts = serviceAreas
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!parts.includes(st)) setServiceAreas([...parts, st].join(", "));
  };

  return (
    <div className="animate-in fade-in duration-500 pb-16 space-y-5">
      {/* Banner */}
      <div className="rounded-xl bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 px-8 py-7 shadow-md">
        <h1 className="text-3xl font-extrabold tracking-tight text-white">Vendor Onboarding</h1>
        <p className="mt-1 text-sm text-indigo-200/80 font-medium">Submit new vendor applications and manage pending approvals</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">
        {/* Application form */}
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-violet-600 to-blue-600">
            <UserPlus className="h-4 w-4 text-white" />
            <h2 className="text-white font-extrabold text-sm">New Vendor Application</h2>
          </div>
          <div className="p-6 space-y-5">
            <div>
              <label className="flex items-center gap-1.5 text-sm font-bold text-slate-800 mb-2">
                <FileText className="h-3.5 w-3.5 text-violet-500" /> Vendor Name <span className="text-red-500">*</span>
              </label>
              <input
                placeholder="e.g., Acme Restoration LLC"
                className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              />
            </div>

            <div>
              <label className="flex items-center gap-1.5 text-sm font-bold text-slate-800 mb-2">
                <ShieldCheck className="h-3.5 w-3.5 text-violet-500" /> License Number <span className="text-red-500">*</span>
              </label>
              <input
                value={licenseNumber}
                onChange={(e) => setLicenseNumber(e.target.value)}
                placeholder="Enter license number"
                className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              />
            </div>

            <div>
              <label className="flex items-center gap-1.5 text-sm font-bold text-slate-800 mb-2">
                <Calendar className="h-3.5 w-3.5 text-violet-500" /> License Expiry Date
              </label>
              <input
                type="date"
                value={licenseExpiry}
                onChange={(e) => setLicenseExpiry(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-400"
              />
            </div>

            <div>
              <label className="flex items-center gap-1.5 text-sm font-bold text-slate-800 mb-2">
                <Upload className="h-3.5 w-3.5 text-violet-500" /> Certification Upload
              </label>
              <div className="rounded-lg border-2 border-dashed border-violet-200 bg-violet-50/30 px-6 py-8 text-center cursor-pointer hover:bg-violet-50 transition-colors">
                <Upload className="h-5 w-5 text-violet-400 mx-auto mb-2" />
                <div className="text-xs font-semibold text-slate-500">Drop certification files here or click to browse</div>
              </div>
            </div>

            <div>
              <label className="flex items-center gap-1.5 text-sm font-bold text-slate-800 mb-2">
                <MapPin className="h-3.5 w-3.5 text-violet-500" /> Service Areas
              </label>
              <input
                value={serviceAreas}
                onChange={(e) => setServiceAreas(e.target.value)}
                placeholder="Comma-separated state codes (e.g., NY, CA, FL, TX, IL)"
                className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              />
              <div className="flex flex-wrap gap-1.5 mt-2.5">
                {serviceAreaStates.map((st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => addState(st)}
                    className="rounded-md border border-indigo-200 bg-indigo-50 text-indigo-600 px-2.5 py-1 text-[10px] font-bold hover:bg-indigo-100 transition-colors"
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="flex items-center gap-1.5 text-sm font-bold text-slate-800 mb-2">
                <Sparkles className="h-3.5 w-3.5 text-violet-500" /> Specialization <span className="text-red-500">*</span>
              </label>
              <Select value={specialization} onValueChange={setSpecialization}>
                <SelectTrigger className="w-full rounded-lg border-slate-200 text-sm h-10">
                  <SelectValue placeholder="Select specialization" />
                </SelectTrigger>
                <SelectContent>
                  {specializations.map((s) => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="flex items-center gap-1.5 text-sm font-bold text-slate-800 mb-2">
                <Mail className="h-3.5 w-3.5 text-violet-500" /> Contact Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="vendor@example.com"
                className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              />
            </div>

            <div>
              <label className="flex items-center gap-1.5 text-sm font-bold text-slate-800 mb-2">
                <Phone className="h-3.5 w-3.5 text-violet-500" /> Contact Phone
              </label>
              <input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="(555) 123-4567"
                className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
              />
            </div>

            <button
              onClick={submitApplication}
              className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 px-4 py-3 text-sm font-bold text-white shadow-sm transition-colors"
            >
              <FileText className="h-4 w-4" /> Submit Vendor Application
            </button>
          </div>
        </div>

        {/* Pending approvals */}
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 flex items-center gap-2.5 bg-gradient-to-r from-amber-500 to-orange-600">
            <ClipboardList className="h-4 w-4 text-white" />
            <h2 className="text-white font-extrabold text-sm">Pending Approvals ({pending.length})</h2>
          </div>
          <div className="divide-y divide-slate-100">
            {pending.length === 0 && (
              <div className="px-5 py-6 text-sm text-slate-500 text-center">No pending applications</div>
            )}
            {pending.map((p) => (
              <div key={p.name} className="px-5 py-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-extrabold text-slate-900 text-sm">{p.name}</span>
                  <span className="rounded-full bg-amber-500 text-white px-3 py-1 text-[10px] font-bold">Pending Review</span>
                </div>
                <div className="text-[11px] text-slate-500 font-medium">
                  {p.specialty} · {p.state} · Submitted {p.submitted}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  License: {p.license} · Expires: {p.expires}
                </div>
                <div className="flex items-center gap-2.5 mt-3">
                  <button
                    onClick={() => decide(p, "Approved")}
                    className="inline-flex items-center gap-1.5 rounded-full bg-emerald-700 hover:bg-emerald-800 text-white px-4 py-1.5 text-[11px] font-bold transition-colors"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                  </button>
                  <button
                    onClick={() => decide(p, "Rejected")}
                    className="inline-flex items-center gap-1.5 rounded-full bg-red-600 hover:bg-red-700 text-white px-4 py-1.5 text-[11px] font-bold transition-colors"
                  >
                    <XCircle className="h-3.5 w-3.5" /> Reject
                  </button>
                </div>
              </div>
            ))}

            {/* Processed list below pending */}
            {processed.map((p) => (
              <div key={`${p.name}-${p.status}`} className="px-5 py-3.5 flex items-center justify-between">
                <div>
                  <div className="font-bold text-slate-500 text-sm">{p.name}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {p.specialty} · {p.state} · Submitted {p.submitted}
                  </div>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-[10px] font-bold text-white ${
                    p.status === "Approved" ? "bg-emerald-500/80" : "bg-red-400"
                  }`}
                >
                  {p.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
