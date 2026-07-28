import { useEffect, useMemo, useRef, useState } from "react";
import { GradientBanner } from "@/components/ui/GradientBanner";
import {
  Search,
  FolderOpen,
  Upload,
  Eye,
  FileText,
  FileImage,
  Calculator,
  Receipt,
  Loader2,
  X,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  UploadCloud,
  List,
  Clock,
  Sparkles,
} from "lucide-react";

function parseInsights(raw: string | null): { confidence: number | null; summary: string | null; fallback: string | null } {
  const text = raw?.trim();
  if (!text) return { confidence: null, summary: null, fallback: null };
  try {
    const obj = JSON.parse(text);
    if (obj && typeof obj === "object" && !Array.isArray(obj)) {
      const confidence = typeof obj.confidence_score === "number" ? obj.confidence_score : null;
      const summary = typeof obj.summary === "string" && obj.summary.trim() ? obj.summary.trim() : null;
      if (confidence !== null || summary !== null) {
        return { confidence, summary, fallback: null };
      }
    }
  } catch {
    // not JSON — fall through to plain text
  }
  return { confidence: null, summary: null, fallback: text };
}

// Parses the "Authenticity Verdict" out of documents.investigation_notes.
// "genuine" → not AI generated, "suspicious" (also tolerates the "suspecious"
// misspelling) → AI generated. The confidence score sits in brackets in the
// same text, either as a percentage ("(92%)") or a 0–1 fraction ("(0.92)").
function parseAuthenticity(raw: string | null): { aiGenerated: boolean; confidence: number | null } | null {
  const text = raw?.trim();
  if (!text) return null;
  const verdictMatch = text.match(/authenticity\s+verdict\s*[:\-–—]?\s*(genuine|susp[ei]cious)/i);
  if (!verdictMatch) return null;
  const aiGenerated = !/^genuine$/i.test(verdictMatch[1]);
  // Look for a bracketed number — round or square brackets — after the
  // verdict first, then anywhere in the text.
  const bracketNum = /[([]([^)\]]*?(\d+(?:\.\d+)?)\s*%?[^)\]]*)[)\]]/;
  const after = text.slice((verdictMatch.index ?? 0) + verdictMatch[0].length);
  const numMatch = after.match(bracketNum) ?? text.match(bracketNum);
  let confidence: number | null = null;
  if (numMatch) {
    const n = Number(numMatch[2]);
    if (Number.isFinite(n)) confidence = n <= 1 ? Math.round(n * 100) : Math.round(n);
  }
  return { aiGenerated, confidence };
}

function parseExtractedData(raw: string | null): { rows: { label: string; value: string }[]; fallback: string | null } {
  const text = raw?.trim();
  if (!text) return { rows: [], fallback: null };
  const parts = text
    .split("|")
    .map((p) => p.trim())
    .filter(Boolean);
  const rows: { label: string; value: string }[] = [];
  const prose: string[] = [];
  for (const part of parts) {
    const idx = part.indexOf(":");
    const label = idx > 0 ? part.slice(0, idx).trim() : "";
    // Only treat a segment as a label/value row when the label looks like a
    // short field name (not a prose sentence that happens to contain a colon).
    if (label && label.length <= 40 && !/[.;!?]/.test(label)) {
      rows.push({ label, value: part.slice(idx + 1).trim() });
    } else {
      prose.push(part);
    }
  }
  return { rows, fallback: prose.length > 0 ? prose.join(" ") : null };
}

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { POLICYHOLDER_MCP_URL } from "@/config/agents";
// The Document Hub is identical for every persona, so it always targets one MCP.
const UPLOAD_ENDPOINT = `${POLICYHOLDER_MCP_URL}/api/v1/document_submission/api/documents/upload`;

type DocCategory = "Photos" | "Reports" | "Estimates" | "Invoices";

interface DocItem {
  id: string;
  name: string;
  category: DocCategory;
  sizeKb: number;
  uploadedAt: string;
  uploadedAtIso: string | null;
  classificationConfidence: number | null;
  documentType: string | null;
  status: string | null;
  uploadedByRole: string | null;
  fileUrl: string | null;
  insights: string | null;
  investigationNotes: string | null;
  extractedData: string | null;
}

type ViewMode = "list" | "timeline";

const ROLE_DOT: Record<string, string> = {
  Policyholder: "bg-blue-500",
  Adjuster:     "bg-emerald-500",
  SIU:          "bg-amber-500",
  Vendor:       "bg-violet-500",
};

const ROLE_BADGE: Record<string, string> = {
  Policyholder: "bg-blue-50 text-blue-700 border-blue-200",
  Adjuster:     "bg-emerald-50 text-emerald-700 border-emerald-200",
  SIU:          "bg-amber-50 text-amber-700 border-amber-200",
  Vendor:       "bg-violet-50 text-violet-700 border-violet-200",
};

function isoToDateLabel(iso: string | null): string {
  if (!iso) return "Unknown date";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Unknown date";
  return d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
}

function isoToDateTimeLabel(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function isoToDateKey(iso: string | null): string {
  if (!iso) return "unknown";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "unknown";
  return d.toISOString().slice(0, 10); // YYYY-MM-DD for grouping
}

function isoToTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

interface DocumentClaim {
  claimId: string;
  docCount: number;
  policyholderName: string | null;
  lossType: string | null;
}

interface StagedFile {
  id: string;
  file: File;
  name: string;
  category: DocCategory;
  sizeKb: number;
}

function classifyFile(file: File): DocCategory {
  const name = file.name.toLowerCase();
  if (file.type.startsWith("image/")) return "Photos";
  if (name.includes("invoice") || name.includes("receipt")) return "Invoices";
  if (name.includes("estimate") || name.includes("quote")) return "Estimates";
  return "Reports";
}

function normalizeCategory(value: unknown): DocCategory {
  const v = String(value ?? "");
  if (v === "Photos" || v === "Reports" || v === "Estimates" || v === "Invoices") return v;
  return "Reports";
}

const categoryIcon: Record<DocCategory, React.ReactNode> = {
  Photos: <FileImage className="h-5 w-5 text-cyan-600" />,
  Reports: <FileText className="h-5 w-5 text-indigo-600" />,
  Estimates: <Calculator className="h-5 w-5 text-violet-600" />,
  Invoices: <Receipt className="h-5 w-5 text-rose-600" />,
};

export default function DocumentHub() {
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── claim selector ────────────────────────────────────────────────────────
  const [claims, setClaims] = useState<DocumentClaim[]>([]);
  const [selectedClaimId, setSelectedClaimId] = useState<string>("");
  const [claimsLoading, setClaimsLoading] = useState(true);

  // ── document list ─────────────────────────────────────────────────────────
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [docsError, setDocsError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<"All" | DocCategory>("All");
  const [selectedDoc, setSelectedDoc] = useState<DocItem | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [viewerOpen, setViewerOpen] = useState(false);

  // ── staged uploads ────────────────────────────────────────────────────────
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{
    ok: number;
    failed: number;
    error: string | null;
  } | null>(null);

  // ── load all claims (includes zero-document claims) ───────────────────────
  useEffect(() => {
    let cancelled = false;
    setClaimsLoading(true);
    (async () => {
      try {
        const res = await fetch("/api/document-claims");
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error((data && data.error) || "Failed to load claims");
        const list: DocumentClaim[] = Array.isArray(data?.claims) ? data.claims : [];
        if (!cancelled) {
          setClaims(list);
          if (list.length > 0) setSelectedClaimId(list[0].claimId);
        }
      } catch (err) {
        console.error("document-claims fetch error:", err);
      } finally {
        if (!cancelled) setClaimsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // ── load documents for selected claim ─────────────────────────────────────
  const refreshDocs = (claimId: string) => {
    if (!claimId) { setDocs([]); return; }
    setDocsLoading(true);
    setDocsError(null);
    setSelectedDoc(null);
    fetch(`/api/documents?claimId=${encodeURIComponent(claimId)}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load documents");
        return res.json();
      })
      .then((data) => {
        const list: DocItem[] = (Array.isArray(data?.documents) ? data.documents : []).map(
          (d: Record<string, unknown>) => ({
            id: String(d.id),
            name: String(d.name ?? "Untitled"),
            category: normalizeCategory(d.category),
            sizeKb: Number(d.sizeKb ?? 0),
            uploadedAt: String(d.uploadedAt ?? "—"),
            uploadedAtIso: d.uploadedAtIso ? String(d.uploadedAtIso) : null,
            classificationConfidence:
              typeof d.classificationConfidence === "number" ? d.classificationConfidence : null,
            documentType: d.documentType ? String(d.documentType) : null,
            status: d.status ? String(d.status) : null,
            uploadedByRole: d.uploadedByRole ? String(d.uploadedByRole) : null,
            fileUrl: d.fileUrl ? String(d.fileUrl) : null,
            insights: d.insights ? String(d.insights) : null,
            investigationNotes: d.investigationNotes ? String(d.investigationNotes) : null,
            extractedData: d.extractedData ? String(d.extractedData) : null,
          })
        );
        setDocs(list);
      })
      .catch((err) => {
        setDocs([]);
        setDocsError(err instanceof Error ? err.message : "Failed to load documents");
      })
      .finally(() => setDocsLoading(false));
  };

  useEffect(() => {
    refreshDocs(selectedClaimId);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedClaimId]);

  // ── file staging ──────────────────────────────────────────────────────────
  const stageFiles = (files: FileList | File[]) => {
    const incoming = Array.from(files).map((file) => ({
      id: `${file.name}-${file.size}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      file,
      name: file.name,
      category: classifyFile(file),
      sizeKb: Math.max(1, Math.round(file.size / 1024)),
    }));
    setStagedFiles((prev) => [...prev, ...incoming]);
    setUploadResult(null);
  };

  const removeStagedFile = (id: string) =>
    setStagedFiles((prev) => prev.filter((f) => f.id !== id));

  // ── upload to MCP ─────────────────────────────────────────────────────────
  const handleUpload = async () => {
    if (uploading || stagedFiles.length === 0 || !selectedClaimId) return;
    setUploading(true);
    setUploadResult(null);

    let ok = 0;
    let failed = 0;
    let firstError: string | null = null;

    for (const staged of stagedFiles) {
      try {
        const form = new FormData();
        form.append("claim_number", selectedClaimId);
        form.append("uploaded_by_role", "Policyholder");
        form.append("file", staged.file, staged.name);
        const res = await fetch(UPLOAD_ENDPOINT, { method: "POST", body: form });
        const data = await res.json().catch(() => null);
        if (!res.ok) {
          failed += 1;
          if (!firstError)
            firstError = (data && (data.detail || data.error)) || `Upload failed (${res.status})`;
        } else {
          ok += 1;
        }
      } catch (err) {
        failed += 1;
        if (!firstError)
          firstError = err instanceof Error ? err.message : "Upload failed";
      }
    }

    setUploading(false);
    setUploadResult({ ok, failed, error: firstError });

    if (ok > 0) {
      setStagedFiles([]);
      // Update the doc count in the claims list for the current claim
      setClaims((prev) =>
        prev.map((c) =>
          c.claimId === selectedClaimId ? { ...c, docCount: c.docCount + ok } : c
        )
      );
      // Refresh the document list
      refreshDocs(selectedClaimId);
    }
  };

  // ── derived ───────────────────────────────────────────────────────────────
  const counts = useMemo(() => {
    const base = { All: docs.length, Photos: 0, Reports: 0, Estimates: 0, Invoices: 0 };
    for (const d of docs) base[d.category] += 1;
    return base;
  }, [docs]);

  const visibleDocs = useMemo(() => {
    let result = activeFilter === "All" ? docs : docs.filter((d) => d.category === activeFilter);
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (d) =>
          d.name.toLowerCase().includes(q) ||
          (d.documentType ?? "").toLowerCase().includes(q) ||
          (d.status ?? "").toLowerCase().includes(q)
      );
    }
    return result;
  }, [docs, activeFilter, searchQuery]);

  // Group visibleDocs by calendar date for the timeline view (oldest → newest).
  const timelineGroups = useMemo(() => {
    const sorted = [...visibleDocs].sort((a, b) => {
      const ta = a.uploadedAtIso ? new Date(a.uploadedAtIso).getTime() : 0;
      const tb = b.uploadedAtIso ? new Date(b.uploadedAtIso).getTime() : 0;
      return ta - tb;
    });
    const groups: { dateKey: string; dateLabel: string; docs: DocItem[] }[] = [];
    for (const doc of sorted) {
      const key = isoToDateKey(doc.uploadedAtIso);
      const last = groups[groups.length - 1];
      if (last && last.dateKey === key) {
        last.docs.push(doc);
      } else {
        groups.push({ dateKey: key, dateLabel: isoToDateLabel(doc.uploadedAtIso), docs: [doc] });
      }
    }
    return groups;
  }, [visibleDocs]);

  const selectedClaim = claims.find((c) => c.claimId === selectedClaimId);

  return (
    <div className="animate-in fade-in duration-500 h-full flex flex-col">
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) stageFiles(e.target.files);
          e.target.value = "";
        }}
      />

      <GradientBanner
        title="Document Hub"
        subtitle="Upload, AI-classify, and track every evidence file for a claim."
        badge="AI-Powered"
        icon={<FolderOpen className="h-5 w-5" />}
        className="mb-6 flex-shrink-0"
      >
        <div className="flex flex-wrap items-center gap-4 pt-4 border-t border-white/10 mt-4">
          {/* Search */}
          <div className="relative flex-1 min-w-[180px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/50" />
            <input
              type="text"
              placeholder="Search by name, type…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-lg bg-black/20 border border-white/10 focus:border-white/30 outline-none text-sm text-white placeholder-white/50"
            />
          </div>

          {/* Claim selector */}
          <select
            value={selectedClaimId}
            onChange={(e) => setSelectedClaimId(e.target.value)}
            className="bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-sm text-white outline-none focus:bg-black/30 appearance-none min-w-[260px]"
          >
            {claimsLoading && <option className="text-gray-900" value="">Loading claims…</option>}
            {!claimsLoading && claims.length === 0 && (
              <option className="text-gray-900" value="">No claims found</option>
            )}
            {claims.map((c) => (
              <option key={c.claimId} className="text-gray-900" value={c.claimId}>
                {c.claimId}
                {c.lossType ? ` — ${c.lossType}` : ""}
                {" "}({c.docCount} doc{c.docCount === 1 ? "" : "s"})
              </option>
            ))}
          </select>

          {/* Upload trigger */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={!selectedClaimId}
            className="flex items-center gap-2 bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2 rounded-lg text-white font-medium shadow-md hover:shadow-lg transition-all border border-blue-400/30 text-sm whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Upload className="h-4 w-4" />
            Add Files
          </button>
        </div>

        <div className="flex items-center gap-3 mt-4 text-xs font-medium text-white/80">
          <span className="bg-black/20 px-2.5 py-1 rounded-md border border-white/10">
            {selectedClaim
              ? `${selectedClaim.claimId}${selectedClaim.policyholderName ? " · " + selectedClaim.policyholderName : ""}`
              : "No claim selected"}
          </span>
          <span className="bg-black/20 px-2.5 py-1 rounded-md border border-white/10">
            {docs.length} document{docs.length === 1 ? "" : "s"} on record
          </span>
        </div>
      </GradientBanner>

      {/* ── Upload staging area ────────────────────────────────────────────── */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (e.dataTransfer.files.length > 0) stageFiles(e.dataTransfer.files);
        }}
        className={`mb-6 rounded-xl border-2 border-dashed transition-colors ${
          isDragging
            ? "border-blue-400 bg-blue-50"
            : stagedFiles.length > 0
            ? "border-blue-200 bg-blue-50/40"
            : "border-gray-200 bg-white"
        }`}
      >
        {stagedFiles.length === 0 ? (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={!selectedClaimId}
            className="w-full flex flex-col items-center justify-center gap-2 py-8 text-center disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <UploadCloud className="h-8 w-8 text-gray-300" />
            <p className="text-sm font-medium text-gray-500">
              {selectedClaimId
                ? "Drag files here or click to browse"
                : "Select a claim above before uploading"}
            </p>
            <p className="text-xs text-gray-400">
              Photos, PDFs, reports, estimates — any format accepted
            </p>
          </button>
        ) : (
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-gray-700">
                {stagedFiles.length} file{stagedFiles.length > 1 ? "s" : ""} ready to upload
              </p>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="text-xs text-blue-600 hover:underline"
              >
                + Add more
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {stagedFiles.map((f) => (
                <div
                  key={f.id}
                  className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2"
                >
                  <div className="flex-shrink-0">{categoryIcon[f.category]}</div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-gray-800">{f.name}</div>
                    <div className="text-xs text-gray-400">{f.category} · {f.sizeKb} KB</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeStagedFile(f.id)}
                    disabled={uploading}
                    className="flex-shrink-0 text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>

            {uploadResult && (
              <div
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm border ${
                  uploadResult.failed === 0
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : "bg-red-50 text-red-600 border-red-200"
                }`}
              >
                {uploadResult.failed === 0 ? (
                  <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
                ) : (
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                )}
                <span>
                  {uploadResult.ok > 0 &&
                    `${uploadResult.ok} file${uploadResult.ok > 1 ? "s" : ""} uploaded successfully. `}
                  {uploadResult.failed > 0 &&
                    `${uploadResult.failed} failed${uploadResult.error ? `: ${uploadResult.error}` : "."}`}
                </span>
              </div>
            )}

            <div className="flex items-center gap-3 pt-1">
              <button
                type="button"
                onClick={() => { setStagedFiles([]); setUploadResult(null); }}
                disabled={uploading}
                className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                Clear
              </button>
              <button
                type="button"
                onClick={() => { void handleUpload(); }}
                disabled={uploading || !selectedClaimId}
                className={`flex items-center gap-2 rounded-lg px-5 py-2 text-sm font-bold text-white shadow transition-colors ${
                  uploading || !selectedClaimId
                    ? "bg-blue-300 cursor-not-allowed"
                    : "bg-blue-600 hover:bg-blue-700"
                }`}
              >
                {uploading ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Uploading…</>
                ) : (
                  <><UploadCloud className="h-4 w-4" /> Upload {stagedFiles.length} file{stagedFiles.length > 1 ? "s" : ""} to {selectedClaimId}</>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Main 3-column grid ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-[400px]">

        {/* Filters */}
        <div className="lg:col-span-3 bg-white rounded-xl border border-gray-200 shadow-sm p-4 flex flex-col">
          <h3 className="font-semibold text-gray-900 mb-4 px-2">Filters</h3>
          <div className="space-y-1">
            <FilterItem icon={<FolderOpen />} label="All Documents"  count={counts.All}      active={activeFilter === "All"}       onClick={() => setActiveFilter("All")} />
            <FilterItem icon={<FileImage />}  label="Photos"         count={counts.Photos}   active={activeFilter === "Photos"}    onClick={() => setActiveFilter("Photos")} />
            <FilterItem icon={<FileText />}   label="Reports"        count={counts.Reports}  active={activeFilter === "Reports"}   onClick={() => setActiveFilter("Reports")} />
            <FilterItem icon={<Calculator />} label="Estimates"      count={counts.Estimates} active={activeFilter === "Estimates"} onClick={() => setActiveFilter("Estimates")} />
            <FilterItem icon={<Receipt />}    label="Invoices"       count={counts.Invoices} active={activeFilter === "Invoices"}  onClick={() => setActiveFilter("Invoices")} />
          </div>
        </div>

        {/* Document list */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b border-gray-100 p-4">
            <h3 className="font-semibold text-gray-900">Documents ({visibleDocs.length})</h3>
            {/* List / Timeline toggle */}
            <div className="flex items-center rounded-lg border border-gray-200 overflow-hidden text-sm">
              <button
                onClick={() => setViewMode("list")}
                className={`flex items-center gap-1.5 px-3 py-1.5 transition-colors ${
                  viewMode === "list"
                    ? "bg-blue-600 text-white"
                    : "text-gray-500 hover:bg-gray-50"
                }`}
              >
                <List className="h-3.5 w-3.5" />
                List
              </button>
              <button
                onClick={() => setViewMode("timeline")}
                className={`flex items-center gap-1.5 px-3 py-1.5 transition-colors ${
                  viewMode === "timeline"
                    ? "bg-blue-600 text-white"
                    : "text-gray-500 hover:bg-gray-50"
                }`}
              >
                <Clock className="h-3.5 w-3.5" />
                Timeline
              </button>
            </div>
          </div>

          {docsLoading ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400 mb-3" />
              <p className="text-sm text-gray-500">Loading documents…</p>
            </div>
          ) : docsError ? (
            <div className="flex-1 flex items-center justify-center p-8">
              <p className="text-sm text-red-600 max-w-[260px] text-center">{docsError}</p>
            </div>
          ) : visibleDocs.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-gray-50/50">
              <div className="h-16 w-16 bg-gray-100 rounded-full flex items-center justify-center text-gray-400 mb-4">
                <FolderOpen className="h-8 w-8" />
              </div>
              <h4 className="text-gray-900 font-medium mb-1">
                {searchQuery ? "No documents match your search." : "No documents yet."}
              </h4>
              <p className="text-sm text-gray-500 max-w-[220px] mb-4">
                {searchQuery
                  ? "Try a different search term or clear the filter."
                  : "Drag files into the upload zone above to attach evidence to this claim."}
              </p>
            </div>
          ) : viewMode === "list" ? (
            <div className="flex-1 overflow-y-auto divide-y divide-gray-100">
              {visibleDocs.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => setSelectedDoc(doc)}
                  className={`w-full flex items-center gap-3 p-4 text-left transition-colors ${
                    selectedDoc?.id === doc.id ? "bg-blue-50" : "hover:bg-gray-50"
                  }`}
                >
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100">
                    {categoryIcon[doc.category]}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium text-gray-900 text-sm">{doc.name}</div>
                    <div className="text-xs text-gray-500">
                      {doc.category} · {doc.sizeKb} KB · {doc.uploadedAt}
                    </div>
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[11px] font-medium border whitespace-nowrap ${
                      doc.status === "Validated"
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : doc.status === "Invalid"
                        ? "bg-red-50 text-red-600 border-red-200"
                        : "bg-amber-50 text-amber-700 border-amber-200"
                    }`}
                  >
                    {doc.status ?? "Pending"}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            /* ── Timeline view ──────────────────────────────────────────── */
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
              {timelineGroups.map((group, gi) => (
                <div key={group.dateKey}>
                  {/* Date header */}
                  <div className="flex items-center gap-3 mb-3">
                    <div className="h-px flex-1 bg-gray-100" />
                    <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide whitespace-nowrap">
                      {group.dateLabel}
                    </span>
                    <div className="h-px flex-1 bg-gray-100" />
                  </div>

                  {/* Events for this date */}
                  <div className="relative">
                    {/* Vertical spine */}
                    {group.docs.length > 1 && (
                      <div className="absolute left-[11px] top-5 bottom-5 w-px bg-gray-200" />
                    )}

                    <div className="space-y-3">
                      {group.docs.map((doc, di) => {
                        const role = doc.uploadedByRole ?? "Unknown";
                        const dotColor = ROLE_DOT[role] ?? "bg-gray-400";
                        const badgeColor = ROLE_BADGE[role] ?? "bg-gray-100 text-gray-600 border-gray-200";
                        const isLast = gi === timelineGroups.length - 1 && di === group.docs.length - 1;
                        return (
                          <button
                            key={doc.id}
                            onClick={() => setSelectedDoc(doc)}
                            className={`w-full flex items-start gap-3 text-left group rounded-xl p-2 transition-colors ${
                              selectedDoc?.id === doc.id ? "bg-blue-50" : "hover:bg-gray-50"
                            }`}
                          >
                            {/* Timeline dot */}
                            <div className="relative flex-shrink-0 mt-1">
                              <div className={`h-[22px] w-[22px] rounded-full border-2 border-white shadow-sm flex items-center justify-center ${dotColor}`}>
                                <div className="h-2 w-2 rounded-full bg-white/70" />
                              </div>
                              {/* connector to next dot within the same date group */}
                              {!isLast && di < group.docs.length - 1 && (
                                <div className="absolute left-[10px] top-[22px] w-px bg-gray-200" style={{ height: "calc(100% + 0.75rem)" }} />
                              )}
                            </div>

                            {/* Card */}
                            <div className="flex-1 min-w-0 rounded-lg border border-gray-200 bg-white px-3 py-2.5 shadow-sm group-hover:border-blue-200 transition-colors">
                              <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <div className="flex-shrink-0">{categoryIcon[doc.category]}</div>
                                    <span className="truncate font-medium text-gray-900 text-sm">{doc.name}</span>
                                  </div>
                                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${badgeColor}`}>
                                      {role}
                                    </span>
                                    <span className="text-[11px] text-gray-400">
                                      {isoToTime(doc.uploadedAtIso)} · {doc.sizeKb} KB
                                    </span>
                                  </div>
                                </div>
                                <span
                                  className={`flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium border ${
                                    doc.status === "Validated"
                                      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                      : doc.status === "Invalid"
                                      ? "bg-red-50 text-red-600 border-red-200"
                                      : "bg-amber-50 text-amber-700 border-amber-200"
                                  }`}
                                >
                                  {doc.status ?? "Pending"}
                                </span>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ))}

              {/* Legend */}
              <div className="pt-2 border-t border-gray-100 flex flex-wrap gap-3">
                {Object.entries(ROLE_BADGE).map(([role, cls]) => (
                  <div key={role} className="flex items-center gap-1.5">
                    <div className={`h-2.5 w-2.5 rounded-full ${ROLE_DOT[role]}`} />
                    <span className="text-xs text-gray-500">{role}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* AI Insights panel */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col overflow-hidden">
          <div className="border-b border-purple-200/70 bg-gradient-to-r from-purple-100 via-fuchsia-100 to-purple-100 p-4 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-purple-600" />
            <h3 className="font-semibold text-gray-900">AI Insights &amp; Extracted Data</h3>
          </div>

          {selectedDoc ? (
            <div className="flex-1 overflow-y-auto bg-gradient-to-b from-purple-200/80 via-fuchsia-100/70 to-purple-200/80 p-4 space-y-4">
              <div className="rounded-xl bg-white shadow-sm border border-blue-100/70 p-4">
                <div className="mb-3">
                  <div className="text-xs text-gray-400 mb-0.5">Document</div>
                  <div className="text-sm font-semibold text-gray-900 break-words">{selectedDoc.name}</div>
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                  <div>
                    <div className="text-xs text-gray-400 mb-0.5">Classification</div>
                    <div className="text-sm font-medium text-gray-900">{selectedDoc.documentType || "—"}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-0.5">Confidence</div>
                    <div className="text-sm font-medium text-gray-900">
                      {selectedDoc.classificationConfidence !== null
                        ? `${Math.round(selectedDoc.classificationConfidence)}%`
                        : "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-0.5">Size</div>
                    <div className="text-sm font-medium text-gray-900">
                      {selectedDoc.sizeKb ? `${selectedDoc.sizeKb} KB` : "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-0.5">Uploaded</div>
                    <div className="text-sm font-medium text-gray-900">
                      {isoToDateTimeLabel(selectedDoc.uploadedAtIso) ?? selectedDoc.uploadedAt ?? "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-0.5">Uploaded by</div>
                    <div className="text-sm font-medium text-gray-900">{selectedDoc.uploadedByRole || "—"}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-0.5">Status</div>
                    <div className="text-sm font-medium text-gray-900">{selectedDoc.status || "—"}</div>
                  </div>
                </div>
              </div>

              {(() => {
                const ai = parseInsights(selectedDoc.insights);
                const authenticity = parseAuthenticity(selectedDoc.investigationNotes);
                const summaryText = ai.summary ?? ai.fallback;
                const hasAi = authenticity !== null || summaryText !== null;
                return hasAi ? (
                  <div className="rounded-xl bg-white shadow-sm border border-purple-100/70 p-4 space-y-3">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-purple-600" />
                      <span className="text-xs font-bold uppercase tracking-wide text-purple-700">AI Insights</span>
                    </div>
                    {authenticity && (
                      <div className="flex items-center justify-between gap-3">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${
                            authenticity.aiGenerated
                              ? "bg-red-50 text-red-700 border border-red-200"
                              : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          }`}
                        >
                          {authenticity.aiGenerated ? (
                            <AlertTriangle className="h-3.5 w-3.5" />
                          ) : (
                            <CheckCircle2 className="h-3.5 w-3.5" />
                          )}
                          {authenticity.aiGenerated ? "AI Generated" : "Not AI Generated"}
                        </span>
                        {authenticity.confidence !== null && (
                          <span className="text-xs text-gray-500">
                            Confidence{" "}
                            <span className="font-bold text-gray-900">{authenticity.confidence}%</span>
                          </span>
                        )}
                      </div>
                    )}
                    {summaryText && (
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1.5">
                          Summary
                        </div>
                        <div className="flex items-start gap-2 text-sm text-gray-700">
                          <CheckCircle2 className="h-4 w-4 mt-0.5 flex-shrink-0 text-emerald-500" />
                          <span>{summaryText}</span>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="rounded-xl bg-white shadow-sm border border-gray-200 p-4 text-sm text-gray-500 flex items-start gap-3">
                    <Sparkles className="h-4 w-4 mt-0.5 flex-shrink-0 text-gray-300" />
                    <div>
                      <div className="font-medium text-gray-600 mb-0.5">No AI insights yet</div>
                      AI extraction runs after adjuster review. Check back once the document has been processed.
                    </div>
                  </div>
                );
              })()}

              {(() => {
                  const extracted = parseExtractedData(selectedDoc.extractedData);
                  if (extracted.rows.length === 0 && !extracted.fallback) return null;
                  return (
                    <div className="rounded-xl bg-white shadow-sm border border-blue-100/70 p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="h-4 w-4 text-blue-600" />
                        <span className="text-xs font-bold uppercase tracking-wide text-blue-700">Extracted Data</span>
                      </div>
                      {extracted.rows.length > 0 && (
                        <div className="divide-y divide-gray-100">
                          {extracted.rows.map((row, i) => {
                            const items = row.value
                              .split(";")
                              .map((s) => s.trim())
                              .filter(Boolean);
                            return (
                              <div key={`${row.label}-${i}`} className="py-2">
                                <div className="text-xs text-gray-400 mb-0.5">{row.label}</div>
                                {items.length > 1 ? (
                                  <ul className="space-y-1">
                                    {items.map((item, j) => (
                                      <li key={j} className="flex items-start gap-1.5 text-sm font-medium text-gray-900">
                                        <span className="mt-[7px] h-1 w-1 rounded-full bg-blue-400 flex-shrink-0" />
                                        <span className="break-words">{item}</span>
                                      </li>
                                    ))}
                                  </ul>
                                ) : (
                                  <div className="text-sm font-medium text-gray-900 break-words">{row.value || "—"}</div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                      {extracted.fallback && (
                        <p
                          className={`text-sm text-gray-700 whitespace-pre-wrap break-words ${
                            extracted.rows.length > 0 ? "mt-2 pt-2 border-t border-gray-100" : ""
                          }`}
                        >
                          {extracted.fallback}
                        </p>
                      )}
                    </div>
                  );
                })()}

              {selectedDoc.fileUrl && (
                <button
                  type="button"
                  onClick={() => setViewerOpen(true)}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 px-4 py-2.5 text-sm font-semibold text-white shadow-md transition-colors"
                >
                  <Eye className="h-4 w-4" />
                  View original file
                </button>
              )}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-gray-50/50">
              <p className="text-sm text-gray-500 max-w-[200px]">
                Select a document from the list to view AI insights and extracted fields.
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 bg-blue-50/50 border border-blue-100 rounded-lg p-4 text-xs text-gray-600">
        <span className="font-semibold text-gray-900">Access Rules: </span>
        Policyholders see their own docs only. Adjusters have full access and may override
        classifications. SIU has full access plus flagged-doc visibility. Vendors see only
        docs for their assigned claim.
      </div>

      <Dialog open={viewerOpen} onOpenChange={setViewerOpen}>
        <DialogContent className="max-w-4xl w-[92vw] p-0 gap-0 overflow-hidden">
          <DialogHeader className="px-5 py-3 border-b border-gray-200">
            <DialogTitle className="text-sm font-semibold text-gray-900 break-all pr-8">
              {selectedDoc?.name ?? "Document"}
            </DialogTitle>
          </DialogHeader>
          <div className="bg-gray-100 flex items-center justify-center" style={{ height: "72vh" }}>
            {selectedDoc &&
              (/\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(selectedDoc.name) ? (
                <img
                  src={`/api/document-file?id=${encodeURIComponent(selectedDoc.id)}`}
                  alt={selectedDoc.name}
                  className="max-h-full max-w-full object-contain"
                />
              ) : (
                <iframe
                  src={`/api/document-file?id=${encodeURIComponent(selectedDoc.id)}`}
                  title={selectedDoc.name}
                  className="h-full w-full border-0 bg-white"
                />
              ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function FilterItem({
  icon,
  label,
  count,
  active = false,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
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
      <span
        className={`px-2 py-0.5 rounded-full text-xs ${
          active ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-500"
        }`}
      >
        {count}
      </span>
    </button>
  );
}
