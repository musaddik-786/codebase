import { useState, useRef, useEffect } from "react";
import {
  Send, Loader2, Wrench, Mic, MicOff, Upload, FileText,
  ClipboardList, ShieldCheck, CheckCircle2, Bell, MessageSquare,
  GitBranch, BadgeCheck, Star, Search, ChevronDown, ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

const ORCHESTRATOR_URL = "http://localhost:7710";
const MCP_BASE = "http://localhost:7700";

const TOOL_TO_PHASE: Record<string, string> = {
  create_fnol_submission: "fnol_intake",
  get_fnol_submission: "fnol_intake",
  get_fnol_by_policy: "fnol_intake",
  update_fnol_submission: "fnol_intake",
  submit_fnol: "fnol_intake",
  get_mandatory_fields: "fnol_intake",
  save_voice_text_extraction: "fnol_intake",
  get_voice_text_extractions: "fnol_intake",
  save_ai_inferences: "fnol_intake",
  log_question_answer: "fnol_intake",
  get_question_log: "fnol_intake",
  save_field_attribution: "fnol_intake",
  extract_fnol_fields_from_text: "fnol_intake",
  check_duplicate_claim: "duplicate_check",
  get_recent_claims_for_policy: "duplicate_check",
  upload_document: "documents",
  get_claim_documents: "documents",
  validate_document: "documents",
  get_document_by_id: "documents",
  get_coverage_verification_result: "coverage",
  get_policy_details: "coverage",
  verify_coverage: "coverage",
  score_claim_readiness: "readiness",
  acknowledge_missing_docs: "readiness",
  get_claim_for_segmentation: "segmentation",
  compute_stp_score: "segmentation",
  get_stp_classification: "segmentation",
  get_claim_status_summary: "status",
  log_policyholder_action: "status",
  log_inbound_communication: "communication",
  draft_status_notification: "communication",
  write_customer_feedback: "feedback",
  get_customer_feedback: "feedback",
};

interface PhaseDefinition {
  id: string;
  label: string;
  agentName: string;
  icon: React.ElementType;
  description: string;
}

const PHASES: PhaseDefinition[] = [
  { id: "fnol_intake",     label: "FNOL Intake",       agentName: "VoiceTextIntakeAgent",          icon: FileText,      description: "Collect loss details & submit claim" },
  { id: "duplicate_check", label: "Duplicate Check",   agentName: "DuplicateClaimCheckAgent",      icon: Search,        description: "Detect duplicate submissions" },
  { id: "documents",       label: "Documents",          agentName: "DocumentSubmissionAgent",       icon: Upload,        description: "Upload & validate evidence" },
  { id: "coverage",        label: "Coverage",           agentName: "PolicyCoverageVerificationAgent", icon: ShieldCheck, description: "Verify policy coverage & payable" },
  { id: "readiness",       label: "Readiness",          agentName: "ClaimReadinessAgent",           icon: CheckCircle2,  description: "Score FNOL completeness" },
  { id: "segmentation",    label: "Segmentation",       agentName: "ClaimSegmentationAgent",        icon: GitBranch,     description: "Route to STP / manual track" },
  { id: "status",          label: "Status Update",      agentName: "ClaimStatusAgent",              icon: ClipboardList, description: "Log filing action & stage" },
  { id: "communication",   label: "Communication",      agentName: "CommunicationAgent",            icon: Bell,          description: "Log interaction & draft notification" },
  { id: "feedback",        label: "Feedback",           agentName: "FeedbackAgent",                 icon: MessageSquare, description: "Capture policyholder satisfaction" },
];

const TOOL_REGEX = /\[Tool:\s*([^\]]+)\]\s*(Starting|Done)/gi;

// ─── Types ────────────────────────────────────────────────────────────────────

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  tools?: string[];
}

interface UploadedFile {
  document_id: string;
  file_name: string;
  document_type: string;
  file_url: string;
  status: string;
}

interface PolicyInfo {
  policy_number: string;
  insured_name: string;
  insured_address: string;
  status: string;
  coverage_type?: string;
  effective_date?: string;
}

type VoiceState = "idle" | "recording" | "transcribing" | "ready";
type PolicyLookupState = "idle" | "loading" | "found" | "error";
type UploadStatus = "idle" | "uploading" | "success" | "error";

// ─── Phase Tracker sidebar ────────────────────────────────────────────────────

function PhaseTracker({
  completedPhases,
  currentPhase,
}: {
  completedPhases: Set<string>;
  currentPhase: string | null;
}) {
  const claimStages = ["Submitted", "Triage", "Assessment", "Settlement", "Closed"];

  return (
    <div className="w-52 shrink-0 flex flex-col gap-1">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
        Agent Journey
      </p>
      {PHASES.map((phase, i) => {
        const isDone = completedPhases.has(phase.id);
        const isActive = currentPhase === phase.id && !isDone;
        const Icon = phase.icon;

        return (
          <div
            key={phase.id}
            className={cn(
              "flex items-start gap-2 rounded-md px-2 py-2 text-xs transition-all border",
              isDone
                ? "bg-green-50 border-green-200 text-green-800"
                : isActive
                ? "bg-primary/10 border-primary/40 text-primary animate-pulse"
                : "bg-muted/30 border-transparent text-muted-foreground"
            )}
          >
            <div className="flex flex-col items-center gap-0.5 shrink-0 mt-0.5">
              <span
                className={cn(
                  "h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold",
                  isDone
                    ? "bg-green-500 text-white"
                    : isActive
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {isDone ? "✓" : i + 1}
              </span>
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1">
                <Icon className="h-3 w-3 shrink-0" />
                <span className="font-medium truncate">{phase.label}</span>
                {isActive && (
                  <Loader2 className="h-3 w-3 animate-spin shrink-0" />
                )}
              </div>
              <p className="text-[10px] opacity-70 leading-tight mt-0.5">
                {phase.agentName}
              </p>
            </div>
          </div>
        );
      })}

      {/* Claim stage mini-tracker — shown when status phase activates */}
      {(completedPhases.has("status") || currentPhase === "status") && (
        <div className="mt-3 p-2 rounded-md border bg-card">
          <p className="text-[10px] font-semibold text-muted-foreground mb-2">Claim Stages</p>
          <div className="flex flex-col gap-1">
            {claimStages.map((stage, i) => (
              <div key={stage} className="flex items-center gap-1.5">
                <div
                  className={cn(
                    "h-2 w-2 rounded-full shrink-0",
                    i === 0 ? "bg-primary" : "bg-muted"
                  )}
                />
                <span className={cn("text-[10px]", i === 0 ? "font-medium text-foreground" : "text-muted-foreground")}>
                  {stage}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Star Rating ──────────────────────────────────────────────────────────────

function StarRating({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          onMouseEnter={() => setHover(star)}
          onMouseLeave={() => setHover(0)}
          className="p-0.5"
        >
          <Star
            className={cn(
              "h-6 w-6 transition-colors",
              star <= (hover || value)
                ? "fill-amber-400 text-amber-400"
                : "text-muted-foreground"
            )}
          />
        </button>
      ))}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function PolicyholderOrchestrator() {
  // Core state
  const [claimId, setClaimId] = useState("CLM-2026-1001");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Phase tracking
  const [completedPhases, setCompletedPhases] = useState<Set<string>>(new Set());
  const [currentPhase, setCurrentPhase] = useState<string | null>(null);

  // Policy lookup
  const [policyNumber, setPolicyNumber] = useState("");
  const [policyLookupState, setPolicyLookupState] = useState<PolicyLookupState>("idle");
  const [policyInfo, setPolicyInfo] = useState<PolicyInfo | null>(null);
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [showPolicyPanel, setShowPolicyPanel] = useState(true);

  // Voice
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [transcript, setTranscript] = useState("");
  const [transcribeError, setTranscribeError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Document upload
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [showDocPanel, setShowDocPanel] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Feedback
  const [starRating, setStarRating] = useState(0);
  const [feedbackText, setFeedbackText] = useState("");

  // Chat scroll
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // ── Policy lookup ──────────────────────────────────────────────────────────

  async function lookupPolicy() {
    if (!policyNumber.trim()) return;
    setPolicyLookupState("loading");
    setPolicyError(null);
    setPolicyInfo(null);
    try {
      const resp = await fetch(`${MCP_BASE}/api/v1/policy_coverage/gw_search_policy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ policy_number: policyNumber.trim() }),
      });
      const data = await resp.json();
      if (!resp.ok || !data.found) {
        setPolicyError(data.error || "Policy not found.");
        setPolicyLookupState("error");
        return;
      }
      const p = data.policy;
      setPolicyInfo({
        policy_number: policyNumber.trim(),
        insured_name: p.insured_name || p.insuredName || "Unknown",
        insured_address: p.insured_address || p.policyAddress || "",
        status: p.status || "Active",
        coverage_type: p.product_name || p.coverage_types?.[0] || "",
        effective_date: p.effective_date || "",
      });
      setPolicyLookupState("found");
    } catch (err: any) {
      setPolicyError(`Lookup failed: ${err?.message}`);
      setPolicyLookupState("error");
    }
  }

  function policyContextPrefix() {
    if (!policyInfo) return "";
    return (
      `[POLICY_CONTEXT: policy_number=${policyInfo.policy_number}, ` +
      `insured_name=${policyInfo.insured_name}, ` +
      `insured_address=${policyInfo.insured_address}, ` +
      `status=${policyInfo.status}` +
      (policyInfo.coverage_type ? `, coverage_type=${policyInfo.coverage_type}` : "") +
      (policyInfo.effective_date ? `, effective_date=${policyInfo.effective_date}` : "") +
      `] `
    );
  }

  // ── Voice recording ────────────────────────────────────────────────────────

  async function startRecording() {
    setTranscribeError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true },
      });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "";
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => { stream.getTracks().forEach((t) => t.stop()); sendToTranscribe(); };
      mediaRecorderRef.current = recorder;
      recorder.start(250);
      setVoiceState("recording");
    } catch {
      setTranscribeError("Microphone access denied.");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setVoiceState("transcribing");
  }

  async function sendToTranscribe() {
    const mimeType = mediaRecorderRef.current?.mimeType || "audio/webm";
    const blob = new Blob(chunksRef.current, { type: mimeType });
    const ext = mimeType.includes("ogg") ? "ogg" : mimeType.includes("mp4") ? "mp4" : "webm";
    const formData = new FormData();
    formData.append("file", blob, `recording.${ext}`);
    try {
      const resp = await fetch(`${ORCHESTRATOR_URL}/transcribe`, { method: "POST", body: formData });
      const data = await resp.json();
      if (!resp.ok || data.error) {
        setTranscribeError(data.error || `Transcription failed (${resp.status})`);
        setVoiceState("idle");
        return;
      }
      setTranscript(data.transcript ?? "");
      setVoiceState("ready");
    } catch (err: any) {
      setTranscribeError(`Transcription failed: ${err?.message}`);
      setVoiceState("idle");
    }
  }

  function sendTranscriptToChat() {
    if (!transcript.trim()) return;
    send(policyContextPrefix() + transcript, "voice_transcript");
    setTranscript("");
    setVoiceState("idle");
  }

  // ── Document upload ────────────────────────────────────────────────────────

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !claimId) return;
    setUploadStatus("uploading");
    setUploadError(null);
    const form = new FormData();
    form.append("claim_id", claimId);
    form.append("uploaded_by_role", "Policyholder");
    form.append("file", file);
    try {
      const resp = await fetch(`${MCP_BASE}/api/v1/document_submission/api/documents/upload`, {
        method: "POST",
        body: form,
      });
      const data = await resp.json();
      if (!resp.ok) {
        setUploadError(data.detail || `Upload failed (${resp.status})`);
        setUploadStatus("error");
        return;
      }
      setUploadedFiles((prev) => [
        { document_id: data.document_id, file_name: data.file_name, document_type: data.document_type, file_url: data.file_url, status: data.status },
        ...prev,
      ]);
      setUploadStatus("success");
    } catch (err: any) {
      setUploadError(`Upload failed: ${err?.message}`);
      setUploadStatus("error");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  // ── Orchestrator chat ──────────────────────────────────────────────────────

  async function send(rawText: string, inputType?: string) {
    const text = rawText.trim();
    if (!text || loading) return;

    const historySnapshot = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: rawText }]);
    setInput("");
    setLoading(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "", tools: [] }]);

    try {
      const resp = await fetch(`${ORCHESTRATOR_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: historySnapshot, input_type: inputType }),
      });

      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          const chunk = line.startsWith("data: ") ? line.slice(6) : line.slice(5);
          if (!chunk || chunk === "[DONE]") continue;
          appendToAssistant(chunk);
        }
      }
    } catch (err: any) {
      appendToAssistant(`\n\n[Error: ${err?.message ?? "request failed"}]`);
    } finally {
      setLoading(false);
      setCurrentPhase(null);
    }
  }

  function appendToAssistant(chunk: string) {
    // Detect tool calls for phase tracking
    const toolStartMatch = chunk.match(/\[Tool:\s*([^\]]+)\]\s*Starting/);
    const toolDoneMatch = chunk.match(/\[Tool:\s*([^\]]+)\]\s*Done/);

    if (toolStartMatch) {
      const phase = TOOL_TO_PHASE[toolStartMatch[1].trim()];
      if (phase) setCurrentPhase(phase);
    }
    if (toolDoneMatch) {
      const phase = TOOL_TO_PHASE[toolDoneMatch[1].trim()];
      if (phase) {
        setCompletedPhases((prev) => new Set([...prev, phase]));
        setCurrentPhase((cur) => (cur === phase ? null : cur));
      }
    }

    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (!last || last.role !== "assistant") return prev;

      const tools = [...(last.tools ?? [])];
      let content = last.content;
      let remaining = chunk;
      TOOL_REGEX.lastIndex = 0;
      let cleaned = "";
      let lastEnd = 0;
      let m: RegExpExecArray | null;
      while ((m = TOOL_REGEX.exec(remaining)) !== null) {
        cleaned += remaining.slice(lastEnd, m.index);
        tools.push(`${m[1].trim()}: ${m[2]}`);
        lastEnd = TOOL_REGEX.lastIndex;
      }
      cleaned += remaining.slice(lastEnd);
      content += cleaned;

      next[next.length - 1] = { ...last, content, tools };
      return next;
    });
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  const isFeedbackPhase =
    completedPhases.has("communication") || currentPhase === "feedback" || completedPhases.has("feedback");

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "hsl(var(--policyholder))" }}>
            Policyholder Orchestrator
          </h1>
          <p className="text-sm text-muted-foreground">
            Full end-to-end claim journey — 9 agents orchestrated in one conversation (port 7710)
          </p>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-lg border bg-muted/30">
          <label className="text-sm font-medium whitespace-nowrap">Claim ID:</label>
          <input
            className="rounded-md border px-3 py-1.5 text-sm bg-background w-44"
            value={claimId}
            onChange={(e) => setClaimId(e.target.value)}
            placeholder="CLM-2026-1001"
          />
        </div>
      </div>

      {/* Main layout: phase tracker + chat */}
      <div className="flex gap-4 mb-4">
        <PhaseTracker completedPhases={completedPhases} currentPhase={currentPhase} />

        {/* Orchestrator chat */}
        <div className="flex-1 flex flex-col border rounded-lg bg-card overflow-hidden" style={{ height: 620 }}>
          {/* Chat header */}
          <div className="px-4 py-2 border-b bg-muted/50 flex items-center justify-between text-sm">
            <span className="font-medium">FNOLOrchestrator</span>
            <span className="text-xs text-muted-foreground font-mono">{ORCHESTRATOR_URL}</span>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
            {messages.length === 0 && (
              <div className="text-sm text-muted-foreground italic space-y-2">
                <p>Start by describing your loss below, or use the voice recorder. The orchestrator will guide you through all 9 steps automatically.</p>
                <p className="text-[11px]">Tip: Look up your policy first using the panel below — the orchestrator will skip the policy number question.</p>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                <div
                  className={cn(
                    "max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap",
                    m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                  )}
                >
                  {m.tools && m.tools.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {m.tools.map((t, ti) => (
                        <span
                          key={ti}
                          className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300"
                        >
                          <Wrench className="h-2.5 w-2.5" />
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  {m.content || (m.role === "assistant" && loading && i === messages.length - 1 ? (
                    <Loader2 className="h-3 w-3 animate-spin inline" />
                  ) : "")}
                </div>
              </div>
            ))}
          </div>

          {/* Voice recording strip */}
          <div className="px-3 py-1.5 border-t bg-muted/20 flex flex-wrap items-center gap-2">
            {voiceState === "idle" && (
              <button
                onClick={startRecording}
                className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs bg-muted hover:bg-muted/80"
              >
                <Mic className="h-3.5 w-3.5" /> Record Voice
              </button>
            )}
            {voiceState === "recording" && (
              <button
                onClick={stopRecording}
                className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs bg-red-100 text-red-700 border-red-300 animate-pulse"
              >
                <MicOff className="h-3.5 w-3.5" /> Stop Recording
              </button>
            )}
            {voiceState === "transcribing" && (
              <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground px-2 py-1">
                <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" /> Transcribing…
              </span>
            )}
            {voiceState === "ready" && (
              <div className="flex items-center gap-2 flex-1">
                <input
                  className="flex-1 rounded-md border px-2 py-1 text-xs bg-background"
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  placeholder="Review transcript…"
                />
                <button
                  onClick={sendTranscriptToChat}
                  disabled={!transcript.trim()}
                  className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs bg-primary text-primary-foreground disabled:opacity-40"
                >
                  <Mic className="h-3 w-3" /> Send
                </button>
                <button
                  onClick={() => { setTranscript(""); setVoiceState("idle"); }}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  Discard
                </button>
              </div>
            )}
            {transcribeError && <p className="text-xs text-red-600">{transcribeError}</p>}
          </div>

          {/* Text input */}
          <form
            className="flex gap-2 p-2 border-t"
            onSubmit={(e) => {
              e.preventDefault();
              send(policyContextPrefix() + input);
            }}
          >
            <input
              className="flex-1 rounded-md border px-3 py-2 text-sm bg-background"
              placeholder={
                policyLookupState === "found"
                  ? "Describe your loss or answer the agent's question…"
                  : "Describe your loss (or look up your policy below first)…"
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </form>
        </div>
      </div>

      {/* Supporting panels row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">

        {/* Policy lookup panel */}
        <div className="border rounded-lg bg-card overflow-hidden">
          <button
            onClick={() => setShowPolicyPanel((p) => !p)}
            className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold hover:bg-muted/30 transition-colors"
          >
            <div className="flex items-center gap-2">
              <BadgeCheck className="h-4 w-4" style={{ color: "hsl(var(--policyholder))" }} />
              Step 1 — Verify Policy (Guidewire Lookup)
              {policyLookupState === "found" && (
                <span className="text-xs font-normal text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5">
                  Verified
                </span>
              )}
            </div>
            {showPolicyPanel ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {showPolicyPanel && (
            <div className="px-4 pb-4">
              <p className="text-xs text-muted-foreground mb-3">
                Look up your policy number first. Verified details are automatically injected into every message — the orchestrator won't ask for them again.
              </p>
              <div className="flex gap-2 mb-2">
                <input
                  className="flex-1 rounded-md border px-3 py-1.5 text-sm bg-background"
                  placeholder="Enter policy number"
                  value={policyNumber}
                  onChange={(e) => {
                    setPolicyNumber(e.target.value);
                    if (policyLookupState !== "idle") { setPolicyLookupState("idle"); setPolicyInfo(null); }
                  }}
                  onKeyDown={(e) => e.key === "Enter" && lookupPolicy()}
                  disabled={policyLookupState === "loading"}
                />
                <button
                  onClick={lookupPolicy}
                  disabled={!policyNumber.trim() || policyLookupState === "loading"}
                  className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm bg-primary text-primary-foreground disabled:opacity-40"
                >
                  {policyLookupState === "loading" ? "Looking up…" : "Look up"}
                </button>
              </div>
              {policyLookupState === "found" && policyInfo && (
                <div className="rounded-md bg-green-50 border border-green-200 p-3 text-xs space-y-1">
                  <div className="flex items-center gap-1.5 text-green-800 font-medium mb-1">
                    <BadgeCheck className="h-3.5 w-3.5" /> Verified via Guidewire
                  </div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-green-700">
                    <span><strong>Insured:</strong> {policyInfo.insured_name}</span>
                    <span><strong>Status:</strong> {policyInfo.status}</span>
                    {policyInfo.coverage_type && <span><strong>Coverage:</strong> {policyInfo.coverage_type}</span>}
                    {policyInfo.insured_address && <span className="col-span-2"><strong>Address:</strong> {policyInfo.insured_address}</span>}
                  </div>
                </div>
              )}
              {policyLookupState === "error" && (
                <p className="text-xs text-red-600">{policyError}</p>
              )}
            </div>
          )}
        </div>

        {/* Document upload panel */}
        <div className="border rounded-lg bg-card overflow-hidden">
          <button
            onClick={() => setShowDocPanel((p) => !p)}
            className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold hover:bg-muted/30 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Upload className="h-4 w-4" style={{ color: "hsl(var(--policyholder))" }} />
              Step 8 — Upload Evidence Documents
              {uploadedFiles.length > 0 && (
                <span className="text-xs font-normal text-primary bg-primary/10 border border-primary/20 rounded-full px-2 py-0.5">
                  {uploadedFiles.length} uploaded
                </span>
              )}
            </div>
            {showDocPanel ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {showDocPanel && (
            <div className="px-4 pb-4">
              <p className="text-xs text-muted-foreground mb-3">
                Upload photos, videos, police reports, or repair estimates for claim{" "}
                <strong>{claimId || "—"}</strong>. After uploading, tell the orchestrator "I've uploaded my documents."
              </p>

              <label className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm bg-muted cursor-pointer mb-3 w-fit hover:bg-muted/80">
                <Upload className="h-4 w-4" />
                {uploadStatus === "uploading" ? "Uploading…" : "Choose file to upload"}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,video/*,.pdf,.docx,.doc,.txt,.csv,.md"
                  className="hidden"
                  disabled={uploadStatus === "uploading"}
                  onChange={handleFileChange}
                />
              </label>

              {uploadStatus === "error" && (
                <p className="text-xs text-red-600 mb-2">{uploadError}</p>
              )}

              {uploadedFiles.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">Uploaded this session:</p>
                  {uploadedFiles.map((f) => (
                    <div key={f.document_id} className="flex items-center gap-2 text-xs rounded-md bg-muted/50 px-2 py-1.5">
                      <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-primary bg-primary/10 rounded px-1.5 py-0.5">
                        {f.document_type}
                      </span>
                      <span className="truncate flex-1 font-medium">{f.file_name}</span>
                      <span className={cn("shrink-0", f.status === "Validated" ? "text-green-600" : "text-amber-600")}>
                        {f.status}
                      </span>
                    </div>
                  ))}
                  <button
                    onClick={() => send(`I've uploaded ${uploadedFiles.length} document(s) for claim ${claimId}. Please validate them and proceed.`)}
                    className="mt-2 w-full rounded-md border px-3 py-1.5 text-xs bg-primary/10 text-primary hover:bg-primary/20 font-medium"
                  >
                    Notify orchestrator about uploaded documents
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Feedback panel — visible once communication phase completes */}
      {isFeedbackPhase && (
        <div className="border rounded-lg bg-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare className="h-4 w-4" style={{ color: "hsl(var(--policyholder))" }} />
            <span className="font-semibold text-sm">Step 14 — Rate Your Experience</span>
          </div>
          <p className="text-xs text-muted-foreground mb-3">
            Rate your experience and add any comments. When you click Send Feedback, the orchestrator will record your rating.
          </p>
          <StarRating value={starRating} onChange={setStarRating} />
          {starRating > 0 && (
            <div className="mt-3 space-y-2">
              <textarea
                className="w-full rounded-md border px-3 py-2 text-sm bg-background resize-none"
                rows={2}
                placeholder="Any comments? (optional)"
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
              />
              <button
                onClick={() => {
                  const ratingLabel = ["", "Poor", "Fair", "Good", "Very Good", "Excellent"][starRating];
                  const msg = feedbackText.trim()
                    ? `I rate this experience ${starRating}/5 (${ratingLabel}). ${feedbackText}`
                    : `I rate this experience ${starRating}/5 (${ratingLabel}).`;
                  send(msg);
                  setStarRating(0);
                  setFeedbackText("");
                }}
                disabled={loading}
                className="inline-flex items-center gap-1.5 rounded-md border px-4 py-1.5 text-sm bg-primary text-primary-foreground disabled:opacity-50"
              >
                <MessageSquare className="h-3.5 w-3.5" /> Send Feedback to Orchestrator
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
