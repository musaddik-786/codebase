import { useState, useRef, useEffect } from "react";
import {
  Mic,
  MicOff,
  Upload,
  FileText,
  ClipboardList,
  MessageSquare,
  ShieldCheck,
  CheckCircle2,
  Bell,
  Zap,
  BadgeCheck,
} from "lucide-react";
import { personas, policyholderGroups } from "@/config/agents";
import { AgentChatPanel } from "@/components/AgentChatPanel";

const persona = personas.policyholder;
const bySlug = Object.fromEntries(persona.agents.map((a) => [a.slug, a]));

// ─── Shared claim ID bar ──────────────────────────────────────────────────────
function ClaimIdBar({ claimId, onChange }: { claimId: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-3 mb-5 p-3 rounded-lg border bg-muted/30">
      <label className="text-sm font-medium">Claim ID:</label>
      <input
        className="rounded-md border px-3 py-1.5 text-sm bg-background w-48"
        value={claimId}
        onChange={(e) => onChange(e.target.value)}
        placeholder="CLM-2026-1001"
      />
      <span className="text-xs text-muted-foreground">Used as context across all policyholder agents below.</span>
    </div>
  );
}

// ─── Quick-test button ────────────────────────────────────────────────────────
function QuickTestBtn({ prompt, onFire }: { prompt: string; onFire: (p: string) => void }) {
  return (
    <button
      onClick={() => onFire(prompt)}
      className="inline-flex items-center gap-1 rounded-md border bg-muted text-muted-foreground hover:bg-primary/10 px-2 py-1 text-[11px] transition-colors"
      title="Send a quick-test message"
    >
      <Zap className="h-3 w-3" />
      Quick Test
    </button>
  );
}

// ─── VoiceIntakeCard ─────────────────────────────────────────────────────────
type VoiceState = "idle" | "recording" | "transcribing" | "ready";
type PolicyLookupState = "idle" | "loading" | "found" | "error";

interface PolicyInfo {
  policy_number: string;
  insured_name: string;
  insured_address: string;
  status: string;
  coverage_type?: string;
  effective_date?: string;
  expiration_date?: string;
}

const MCP_BASE = "http://localhost:7700";

function VoiceIntakeCard({ claimId }: { claimId: string }) {
  const agent = bySlug["fnol_orchestrator"];

  // Policy lookup state
  const [policyNumber, setPolicyNumber] = useState("");
  const [policyLookupState, setPolicyLookupState] = useState<PolicyLookupState>("idle");
  const [policyInfo, setPolicyInfo] = useState<PolicyInfo | null>(null);
  const [policyError, setPolicyError] = useState<string | null>(null);

  // Voice state
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [transcript, setTranscript] = useState("");
  const [transcribeError, setTranscribeError] = useState<string | null>(null);
  const [quickMsg, setQuickMsg] = useState<string | null>(null);
  const [externalMsg, setExternalMsg] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

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
        setPolicyError(data.error || "Policy not found. Please check the policy number.");
        setPolicyLookupState("error");
        return;
      }
      const p = data.policy;
      setPolicyInfo({
        policy_number: policyNumber.trim(),
        insured_name: p.insured_name || p.insuredName || "Unknown",
        insured_address: p.insured_address || p.policyAddress || "",
        status: p.status || "Active",
        coverage_type: p.product_name || p.coverage_types?.[0] || p.coverage_type || "",
        effective_date: p.effective_date || "",
        expiration_date: p.expiration_date || "",
      });
      setPolicyLookupState("found");
    } catch (err: any) {
      setPolicyError(`Lookup failed: ${err?.message}`);
      setPolicyLookupState("error");
    }
  }

  // Build policy context prefix injected into every message
  function policyContextPrefix(): string {
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

  async function startRecording() {
    setTranscribeError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      // Prefer webm/opus; fall back to whatever the browser supports
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "";

      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        sendToTranscribe();
      };
      mediaRecorderRef.current = recorder;
      recorder.start(250); // collect chunks every 250 ms
      setVoiceState("recording");
    } catch (err: any) {
      setTranscribeError("Microphone access denied. Please allow microphone and try again.");
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
      const resp = await fetch(`${agent.baseUrl}/transcribe`, { method: "POST", body: formData });
      const data = await resp.json();
      if (!resp.ok || data.error) {
        setTranscribeError(data.error || `Transcription failed (${resp.status})`);
        setVoiceState("idle");
        return;
      }
      setTranscript(data.transcript ?? "");
      setVoiceState("ready");
    } catch (err: any) {
      setTranscribeError(`Transcription request failed: ${err?.message}`);
      setVoiceState("idle");
    }
  }

  function sendTranscript() {
    if (!transcript.trim()) return;
    setExternalMsg(policyContextPrefix() + transcript);
    setTranscript("");
    setVoiceState("idle");
  }

  function discardTranscript() {
    setTranscript("");
    setVoiceState("idle");
  }

  return (
    <div className="border rounded-lg p-4 bg-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5" style={{ color: `hsl(var(--${persona.color}))` }} />
          <h3 className="font-semibold">File a New Claim (FNOL)</h3>
        </div>
        <QuickTestBtn prompt={agent.quickTestPrompt} onFire={(p) => setQuickMsg(p)} />
      </div>
      <p className="text-sm text-muted-foreground mb-3">
        Describe your loss by voice or text. Voice is transcribed via Azure gpt-4o-transcribe.
      </p>

      {/* Policy lookup */}
      <div className="mb-3 p-3 rounded-md border bg-muted/30">
        <p className="text-xs font-medium mb-2">Step 1 — Verify your policy</p>
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-md border px-3 py-1.5 text-sm bg-background"
            placeholder="Enter policy number"
            value={policyNumber}
            onChange={(e) => {
              setPolicyNumber(e.target.value);
              if (policyLookupState !== "idle") {
                setPolicyLookupState("idle");
                setPolicyInfo(null);
              }
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
          <div className="mt-2 flex items-center gap-2 text-xs text-green-700">
            <BadgeCheck className="h-3.5 w-3.5 text-green-600 shrink-0" />
            <span>
              Policy details verified via Guidewire —{" "}
              <strong>{policyInfo.insured_name}</strong>
              {policyInfo.coverage_type ? ` · ${policyInfo.coverage_type}` : ""}
              {` · ${policyInfo.status}`}
            </span>
          </div>
        )}
        {policyLookupState === "error" && (
          <p className="mt-2 text-xs text-red-600">{policyError}</p>
        )}
      </div>

      {/* Recording controls */}
      <div className="flex flex-wrap gap-2 mb-2">
        {voiceState === "idle" && (
          <button
            onClick={startRecording}
            className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm bg-muted hover:bg-muted/80"
          >
            <Mic className="h-4 w-4" /> Record Voice
          </button>
        )}

        {voiceState === "recording" && (
          <button
            onClick={stopRecording}
            className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm bg-red-100 text-red-700 border-red-300 animate-pulse"
          >
            <MicOff className="h-4 w-4" /> Stop Recording
          </button>
        )}

        {voiceState === "transcribing" && (
          <span className="inline-flex items-center gap-2 text-sm text-muted-foreground px-3 py-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
            Transcribing…
          </span>
        )}
      </div>

      {/* Error */}
      {transcribeError && (
        <p className="text-xs text-red-600 mb-2">{transcribeError}</p>
      )}

      {/* Transcript review */}
      {voiceState === "ready" && (
        <div className="mb-3">
          <p className="text-xs text-muted-foreground mb-1">Review transcript before sending:</p>
          <textarea
            className="w-full rounded-md border px-3 py-2 text-sm bg-background resize-y"
            rows={3}
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={sendTranscript}
              disabled={!transcript.trim()}
              className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm bg-primary text-primary-foreground disabled:opacity-40"
            >
              <Mic className="h-4 w-4" /> Send to Agent
            </button>
            <button
              onClick={discardTranscript}
              className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm bg-muted"
            >
              Discard
            </button>
            <button
              onClick={startRecording}
              className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm bg-muted"
            >
              <Mic className="h-4 w-4" /> Re-record
            </button>
          </div>
        </div>
      )}

      <AgentChatPanel
        agentName={agent.name}
        baseUrl={agent.baseUrl}
        placeholder={policyLookupState === "found" ? "Describe what happened…" : "Look up your policy above first, then describe what happened…"}
        buildMessage={(text) => policyContextPrefix() + text}
        externalMessage={externalMsg ?? quickMsg ?? undefined}
        onExternalMessageSent={() => {
          setExternalMsg(null);
          setQuickMsg(null);
        }}
      />
    </div>
  );
}

// ─── ClaimStatusCard ──────────────────────────────────────────────────────────
function ClaimStatusCard({ claimId }: { claimId: string }) {
  const agent = bySlug["claim_status"];
  const stages = ["Submitted", "Triage", "Investigation", "Assessment", "Settlement", "Closed"];
  const [currentStage, setCurrentStage] = useState<number>(0);
  const [subStatus, setSubStatus] = useState<string | null>(null);
  const [slaStatus, setSlaStatus] = useState<string | null>(null);
  const [quickMsg, setQuickMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!claimId) return;

    async function fetchStatus() {
      try {
        const resp = await fetch(
          `${MCP_BASE}/api/v1/claim_status/api/claim_status/summary/${claimId}`
        );
        if (!resp.ok) return;
        const data = await resp.json();
        if (data.error) return;
        // current_stage from DB is 1-based; convert to 0-based index
        const stageIndex = Math.max(0, (data.current_stage ?? 1) - 1);
        setCurrentStage(Math.min(stageIndex, stages.length - 1));
        setSubStatus(data.sub_status ?? null);
        setSlaStatus(data.overall_sla_status ?? null);
      } catch {
        // silently ignore — agent chat is still available
      }
    }

    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [claimId]);

  return (
    <div className="border rounded-lg p-4 bg-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-5 w-5" style={{ color: `hsl(var(--${persona.color}))` }} />
          <h3 className="font-semibold">Follow My Claim</h3>
        </div>
        <QuickTestBtn
          prompt={`What is the current status of claim ${claimId}?`}
          onFire={(p) => setQuickMsg(p)}
        />
      </div>
      <div className="flex items-center mb-2 overflow-x-auto">
        {stages.map((stage, i) => (
          <div key={stage} className="flex items-center flex-1 min-w-[90px]">
            <div className="flex flex-col items-center flex-1">
              <div
                className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  i <= currentStage ? "text-white" : "bg-muted text-muted-foreground"
                }`}
                style={i <= currentStage ? { backgroundColor: `hsl(var(--${persona.color}))` } : {}}
              >
                {i + 1}
              </div>
              <span className="text-[10px] mt-1 text-center">{stage}</span>
            </div>
            {i < stages.length - 1 && (
              <div
                className="h-0.5 flex-1 -mt-4"
                style={{
                  backgroundColor:
                    i < currentStage ? `hsl(var(--${persona.color}))` : "hsl(var(--border))",
                }}
              />
            )}
          </div>
        ))}
      </div>
      {(subStatus || slaStatus) && (
        <div className="flex items-center gap-3 mb-3 text-xs text-muted-foreground">
          {subStatus && <span>Status: <strong className="text-foreground">{subStatus}</strong></span>}
          {slaStatus && (
            <span className={slaStatus === "on_track" ? "text-green-600" : "text-amber-600"}>
              SLA: <strong>{slaStatus === "on_track" ? "On Track" : "Delayed"}</strong>
            </span>
          )}
        </div>
      )}
      <AgentChatPanel
        agentName={agent.name}
        baseUrl={agent.baseUrl}
        placeholder="Ask about your claim status..."
        buildMessage={(text) => `For claim ${claimId}: ${text}`}
        externalMessage={quickMsg ?? undefined}
        onExternalMessageSent={() => setQuickMsg(null)}
      />
    </div>
  );
}

// ─── DocumentSubmissionCard ───────────────────────────────────────────────────
type UploadStatus = "idle" | "uploading" | "success" | "error";

interface UploadedFile {
  document_id: string;
  file_name: string;
  document_type: string;
  file_url: string;
  status: string;
}

function DocumentSubmissionCard({ claimId }: { claimId: string }) {
  const agent = bySlug["document_submission"];
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [quickMsg, setQuickMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
        {
          document_id: data.document_id,
          file_name: data.file_name,
          document_type: data.document_type,
          file_url: data.file_url,
          status: data.status,
        },
        ...prev,
      ]);
      setUploadStatus("success");
    } catch (err: any) {
      setUploadError(`Upload failed: ${err?.message}`);
      setUploadStatus("error");
    } finally {
      // reset input so the same file can be re-uploaded if needed
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div className="border rounded-lg p-4 bg-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Upload className="h-5 w-5" style={{ color: `hsl(var(--${persona.color}))` }} />
          <h3 className="font-semibold">Submit Evidence</h3>
        </div>
        <QuickTestBtn
          prompt={agent.quickTestPrompt}
          onFire={(p) => setQuickMsg(p)}
        />
      </div>

      <p className="text-sm text-muted-foreground mb-3">
        Upload images, videos, or documents (PDF, DOCX, TXT) as evidence for claim{" "}
        <strong>{claimId || "—"}</strong>. Files are stored in Azure Blob Storage and tracked in the database.
      </p>

      {/* File upload button */}
      <label className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm bg-muted cursor-pointer mb-2 w-fit hover:bg-muted/80">
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

      {/* Uploaded files list */}
      {uploadedFiles.length > 0 && (
        <div className="mb-3 space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Uploaded this session:</p>
          {uploadedFiles.map((f) => (
            <div key={f.document_id} className="flex items-center gap-2 text-xs rounded-md bg-muted/50 px-2 py-1.5">
              <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-primary bg-primary/10 rounded px-1.5 py-0.5">
                {f.document_type}
              </span>
              <span className="truncate flex-1 font-medium">{f.file_name}</span>
              <span className={`shrink-0 ${f.status === "Validated" ? "text-green-600" : "text-amber-600"}`}>
                {f.status}
              </span>
            </div>
          ))}
        </div>
      )}

      <AgentChatPanel
        agentName={agent.name}
        baseUrl={agent.baseUrl}
        placeholder="Ask about uploaded evidence or request a validation check…"
        buildMessage={(text) => `For claim ${claimId}: ${text}`}
        externalMessage={quickMsg ?? undefined}
        onExternalMessageSent={() => setQuickMsg(null)}
      />
    </div>
  );
}

// ─── PolicyCoverageCard ───────────────────────────────────────────────────────
function PolicyCoverageCard({ claimId }: { claimId: string }) {
  const agent = bySlug["policy_coverage"];
  const [quickMsg, setQuickMsg] = useState<string | null>(null);

  return (
    <div className="border rounded-lg p-4 bg-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5" style={{ color: `hsl(var(--${persona.color}))` }} />
          <h3 className="font-semibold">Policy Coverage Verification</h3>
        </div>
        <QuickTestBtn
          prompt={`Verify coverage for claim ${claimId}`}
          onFire={(p) => setQuickMsg(p)}
        />
      </div>
      <p className="text-sm text-muted-foreground mb-3">
        Checks if your policy covers this claim, and calculates the net payable after deductibles.
      </p>
      <AgentChatPanel
        agentName={agent.name}
        baseUrl={agent.baseUrl}
        placeholder="e.g. Does my policy cover water damage from a burst pipe?"
        buildMessage={(text) => `For claim ${claimId}: ${text}`}
        externalMessage={quickMsg ?? undefined}
        onExternalMessageSent={() => setQuickMsg(null)}
      />
    </div>
  );
}

// ─── ClaimReadinessCard ───────────────────────────────────────────────────────
function ClaimReadinessCard({ claimId }: { claimId: string }) {
  const agent = bySlug["claim_readiness"];
  const [quickMsg, setQuickMsg] = useState<string | null>(null);

  return (
    <div className="border rounded-lg p-4 bg-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5" style={{ color: `hsl(var(--${persona.color}))` }} />
          <h3 className="font-semibold">Claim Readiness Score</h3>
        </div>
        <QuickTestBtn
          prompt={`Score the readiness of claim ${claimId} for formal submission`}
          onFire={(p) => setQuickMsg(p)}
        />
      </div>
      <p className="text-sm text-muted-foreground mb-3">
        Scores FNOL completeness and tells you what's missing before you submit.
      </p>
      <AgentChatPanel
        agentName={agent.name}
        baseUrl={agent.baseUrl}
        placeholder="e.g. Is my claim ready to submit?"
        buildMessage={(text) => `For claim ${claimId}: ${text}`}
        externalMessage={quickMsg ?? undefined}
        onExternalMessageSent={() => setQuickMsg(null)}
      />
    </div>
  );
}

// ─── CommunicationCard ────────────────────────────────────────────────────────
function CommunicationCard({ claimId }: { claimId: string }) {
  const agent = bySlug["communication"];
  const [quickMsg, setQuickMsg] = useState<string | null>(null);

  return (
    <div className="border rounded-lg p-4 bg-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Bell className="h-5 w-5" style={{ color: `hsl(var(--${persona.color}))` }} />
          <h3 className="font-semibold">Status Notifications</h3>
        </div>
        <QuickTestBtn
          prompt={`Draft a status notification for claim ${claimId}`}
          onFire={(p) => setQuickMsg(p)}
        />
      </div>
      <p className="text-sm text-muted-foreground mb-3">
        Drafts clear, friendly status update messages to keep you informed at every stage.
      </p>
      <AgentChatPanel
        agentName={agent.name}
        baseUrl={agent.baseUrl}
        placeholder="e.g. Send me a status update for my claim"
        buildMessage={(text) => `For claim ${claimId}: ${text}`}
        externalMessage={quickMsg ?? undefined}
        onExternalMessageSent={() => setQuickMsg(null)}
      />
    </div>
  );
}

// ─── FeedbackCard ─────────────────────────────────────────────────────────────
function FeedbackCard({ claimId }: { claimId: string }) {
  const agent = bySlug["feedback"];
  const [quickMsg, setQuickMsg] = useState<string | null>(null);

  return (
    <div className="border rounded-lg p-4 bg-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" style={{ color: `hsl(var(--${persona.color}))` }} />
          <h3 className="font-semibold">Feedback</h3>
        </div>
        <QuickTestBtn
          prompt={agent.quickTestPrompt.replace("CLM-2026-1001", claimId || "CLM-2026-1001")}
          onFire={(p) => setQuickMsg(p)}
        />
      </div>
      <AgentChatPanel
        agentName={agent.name}
        baseUrl={agent.baseUrl}
        placeholder="Share your feedback about the claims process..."
        buildMessage={(text) => `For claim ${claimId}: ${text}`}
        externalMessage={quickMsg ?? undefined}
        onExternalMessageSent={() => setQuickMsg(null)}
      />
    </div>
  );
}

// ─── OtherAgents (Duplicate Check, Segmentation) ──────────────────────────────
function OtherAgents({ claimId }: { claimId: string }) {
  const slugs = ["duplicate_check", "segmentation"];
  const others = slugs.map((s) => bySlug[s]).filter(Boolean);
  const [quickMsgs, setQuickMsgs] = useState<Record<string, string | null>>({});

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {others.map((agent) => (
        <div key={agent.slug}>
          <div className="flex items-center justify-between mb-1">
            <div>
              <span className="text-xs font-mono text-muted-foreground">{agent.name}</span>
              {agent.description && (
                <p className="text-[11px] text-muted-foreground mt-0.5">{agent.description}</p>
              )}
            </div>
            <QuickTestBtn
              prompt={agent.quickTestPrompt.replace("CLM-2026-1001", claimId || "CLM-2026-1001")}
              onFire={(p) => setQuickMsgs((prev) => ({ ...prev, [agent.slug]: p }))}
            />
          </div>
          <AgentChatPanel
            agentName={agent.name}
            baseUrl={agent.baseUrl}
            buildMessage={(text) => `For claim ${claimId}: ${text}`}
            externalMessage={quickMsgs[agent.slug] ?? undefined}
            onExternalMessageSent={() =>
              setQuickMsgs((prev) => ({ ...prev, [agent.slug]: null }))
            }
          />
        </div>
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export function Policyholder() {
  const [claimId, setClaimId] = useState("CLM-2026-1001");

  return (
    <div>
      <h1 className="text-2xl mb-1" style={{ color: `hsl(var(--${persona.color}))` }}>
        Policyholder
      </h1>
      <p className="text-muted-foreground mb-4">{persona.description}</p>

      <ClaimIdBar claimId={claimId} onChange={setClaimId} />

      {/* Primary cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <VoiceIntakeCard claimId={claimId} />
        <ClaimStatusCard claimId={claimId} />
        <DocumentSubmissionCard claimId={claimId} />
        <FeedbackCard claimId={claimId} />
      </div>

      {/* Coverage & communication */}
      <h2 className="text-base font-semibold mb-3 text-muted-foreground">Coverage & Communication</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <PolicyCoverageCard claimId={claimId} />
        <ClaimReadinessCard claimId={claimId} />
        <CommunicationCard claimId={claimId} />
      </div>

      {/* Utility agents */}
      <h2 className="text-base font-semibold mb-3 text-muted-foreground">Other Agents</h2>
      <OtherAgents claimId={claimId} />
    </div>
  );
}
