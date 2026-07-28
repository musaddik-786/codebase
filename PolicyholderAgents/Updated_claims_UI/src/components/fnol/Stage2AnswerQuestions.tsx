import { useEffect, useRef, useState } from "react";
import {
  MessageSquare,
  Mic,
  Send,
  Camera,
  UploadCloud,
  X,
  Sparkles,
  ChevronRight,
  Bot,
  User,
  Loader2,
  FileText,
  Shield,
  MapPin,
  Calendar,
  type LucideIcon,
} from "lucide-react";
import { SourceTag, ConfidenceIndicator } from "./SourceTag";
import { AgentMessage } from "./AgentMessage";
import { useVoiceInput } from "@/lib/useVoiceInput";
import {
  type EvidencePhoto,
  type ChatMessage,
  type FnolField,
  type LossSource,
} from "@/lib/fnol-data";

const POLICY_ICONS: LucideIcon[] = [FileText, User, MapPin, Calendar];

const sourceTagFor = (source: LossSource) => {
  switch (source) {
    case "Human Edited":
      return <SourceTag variant="customer-confirmed-solid" label="Human Edited" />;
    case "Confirmed by You":
    case "Customer-Confirmed":
      return <SourceTag variant="customer-confirmed-solid" label="Confirmed by You" />;
    case "You Provided":
    case "Customer-Provided":
      return <SourceTag variant="customer-provided-solid" label="You Provided" />;
    case "From Your Voice":
      return <SourceTag variant="customer-provided-solid" label="From Your Voice" />;
    case "From Description":
      return <SourceTag variant="customer-provided-solid" label="From Description" />;
    case "Policy Record":
      return <SourceTag variant="auto-filled-solid" label="Policy Record" />;
    case "AI Extracted":
    case "AI-Inferred":
    default:
      return <SourceTag variant="ai-inferred-solid" label="AI Extracted" />;
  }
};

type PolicyDetails = {
  policyNumber: string | null;
  insuredName: string | null;
  insuredAddress: string | null;
  policyPeriod: string | null;
};

const FNOL_AGENT_URL = import.meta.env.VITE_FNOL_AGENT_URL ?? "http://localhost:7730";
const MCP_URL = import.meta.env.VITE_MCP_URL ?? "http://localhost:7720";
const CHAT_ENDPOINT = `${FNOL_AGENT_URL}/chat`;
const DOCUMENT_UPLOAD_ENDPOINT = `${MCP_URL}/api/v1/document_submission/api/documents/upload`;

const TOOL_MARKER_REGEX = /\[Tool:\s*[^\]]+\][^\n]*/gi;

const FALLBACK_FIRST_MESSAGE =
  "Hi, I'm your claims assistant. To get started, can you tell me a bit more about what happened?";

// Matches CLM-YYYY-NNNN or CLM-NNNN style claim numbers emitted by the orchestrator.
const CLAIM_NUMBER_RE = /\bCLM-\d{4}-\d+\b|\bCLM-\d+\b/;

export function Stage2AnswerQuestions({
  policyNumber,
  photos,
  onAddPhotos,
  onRemovePhoto,
  comments,
  onCommentsChange,
  humanReview,
  onHumanReviewChange,
  messages,
  onMessagesChange,
  initialDescription,
  lossFields,
  overallConfidence,
  submissionLoading,
  submissionError,
  onClaimNumberFound,
  onFnolRefreshNeeded,
  isSavingEdits,
  saveEditsError,
  onNext,
  onBack,
}: {
  policyNumber: string;
  photos: EvidencePhoto[];
  onAddPhotos: (files: FileList) => void;
  onRemovePhoto: (id: string) => void;
  comments: string;
  onCommentsChange: (value: string) => void;
  humanReview: Record<string, string>;
  onHumanReviewChange: (field: string, value: string) => void;
  messages: ChatMessage[];
  onMessagesChange: (
    updater: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])
  ) => void;
  initialDescription: string;
  lossFields: FnolField[];
  overallConfidence: number | null;
  submissionLoading: boolean;
  submissionError: string | null;
  onClaimNumberFound?: (claimNumber: string) => void;
  onFnolRefreshNeeded?: () => void;
  isSavingEdits?: boolean;
  saveEditsError?: string | null;
  onNext: () => void;
  onBack: () => void;
}) {
  const [input, setInput] = useState("");
  const currentAgentTextRef = useRef("");
  const [policyDetails, setPolicyDetails] = useState<PolicyDetails | null>(null);
  const [policyLoading, setPolicyLoading] = useState(false);
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [policyFetchDone, setPolicyFetchDone] = useState(false);
  const [sending, setSending] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{
    ok: number;
    failed: number;
    error: string | null;
  } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  const { listening, transcribing, toggle } = useVoiceInput((text) =>
    setInput((prev) => (prev ? `${prev} ${text}` : text))
  );

  const buildPolicyContext = () => {
    const num = policyNumber.trim();
    const parts: string[] = [];
    if (num) parts.push(`policy_number=${num}`);
    if (policyDetails?.insuredName)
      parts.push(`policyholder_name=${policyDetails.insuredName}`);
    if (policyDetails?.insuredAddress)
      parts.push(`policyholder_address=${policyDetails.insuredAddress}`);
    if (policyDetails?.policyPeriod)
      parts.push(`policy_period=${policyDetails.policyPeriod}`);
    if (parts.length === 0) return "";
    return `[POLICY_CONTEXT: ${parts.join(", ")}] `;
  };

  const stripToolMarkers = (chunk: string) =>
    chunk.replace(TOOL_MARKER_REGEX, "");

  const appendToAssistant = (chunk: string) => {
    const cleaned = stripToolMarkers(chunk);
    if (!cleaned) return;
    currentAgentTextRef.current += cleaned;
    onMessagesChange((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (!last || last.role !== "agent") return prev;
      next[next.length - 1] = { ...last, text: last.text + cleaned };
      return next;
    });
  };

  const runChat = async (
    sentText: string,
    displayText: string,
    inputType: string
  ) => {
    if (sending) return;
    // Reconstruct transport history from the displayed conversation so it
    // survives stage navigation. Re-inject the policy context onto the first
    // user turn (the displayed bubble keeps the clean description).
    const history = messages.map((m) => ({
      role: m.role === "agent" ? "assistant" : "user",
      content: m.text,
    }));
    const firstUserIdx = history.findIndex((h) => h.role === "user");
    if (firstUserIdx !== -1) {
      const ctx = buildPolicyContext();
      if (ctx && !history[firstUserIdx].content.startsWith("[POLICY_CONTEXT")) {
        history[firstUserIdx] = {
          ...history[firstUserIdx],
          content: `${ctx}${history[firstUserIdx].content}`,
        };
      }
    }

    onMessagesChange((m) => [
      ...m,
      { role: "user", text: displayText },
      { role: "agent", text: "" },
    ]);
    currentAgentTextRef.current = "";
    setSending(true);

    const handlePayload = (raw: string) => {
      const payload = raw.replace(/^ /, "");
      if (!payload || payload === "[DONE]") return;
      appendToAssistant(payload);
    };

    try {
      const res = await fetch(CHAT_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: sentText,
          history,
          input_type: inputType,
        }),
      });
      if (!res.ok) throw new Error(String(res.status));

      const contentType = res.headers.get("content-type") || "";
      if (!contentType.includes("event-stream") || !res.body) {
        const data = await res.json().catch(() => null);
        const reply =
          (data && (data.message ?? data.reply ?? data.text)) || "";
        appendToAssistant(reply);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (line.startsWith("data:")) handlePayload(line.slice(5));
        }
      }
      // Flush any final fragment left without a trailing newline.
      if (buffer.startsWith("data:")) handlePayload(buffer.slice(5));
    } catch (err) {
      console.error("Chat send error:", err);
      appendToAssistant(
        "Sorry, I had trouble reaching the claims assistant. Please try again."
      );
    } finally {
      setSending(false);
      const agentText = currentAgentTextRef.current;
      if (agentText) {
        const claimMatch = agentText.match(CLAIM_NUMBER_RE);
        if (claimMatch) {
          onClaimNumberFound?.(claimMatch[0]);
        }
        setTimeout(() => onFnolRefreshNeeded?.(), 1500);
      }
    }
  };

  useEffect(() => {
    if (initialized.current) return;
    if (messages.length > 0) {
      initialized.current = true;
      return;
    }
    if (!policyFetchDone) return;
    initialized.current = true;
    const desc = initialDescription.trim();
    if (desc) {
      void runChat(`${buildPolicyContext()}${desc}`, desc, "text");
    } else {
      onMessagesChange([{ role: "agent", text: FALLBACK_FIRST_MESSAGE }]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [policyFetchDone, messages.length]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  useEffect(() => {
    const trimmed = policyNumber.trim();
    if (!trimmed) {
      setPolicyDetails(null);
      setPolicyError(null);
      setPolicyLoading(false);
      setPolicyFetchDone(true);
      return;
    }
    let cancelled = false;
    setPolicyLoading(true);
    setPolicyError(null);
    (async () => {
      try {
        const res = await fetch(
          `/api/policy-details?policyNumber=${encodeURIComponent(trimmed)}`
        );
        const data = await res.json().catch(() => null);
        if (!res.ok) {
          const message =
            res.status === 404
              ? "No matching policy found in the policy system."
              : (data && data.error) || "Could not load policy information.";
          throw new Error(message);
        }
        if (!cancelled) setPolicyDetails(data as PolicyDetails);
      } catch (err) {
        if (!cancelled) {
          setPolicyError(
            err instanceof Error
              ? err.message
              : "Could not load policy information."
          );
          setPolicyDetails(null);
        }
      } finally {
        if (!cancelled) {
          setPolicyLoading(false);
          setPolicyFetchDone(true);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [policyNumber]);

  const policyFields: { label: string; value: string | null }[] = [
    { label: "Policy Number", value: policyDetails?.policyNumber ?? null },
    { label: "Insured Name", value: policyDetails?.insuredName ?? null },
    { label: "Insured Address", value: policyDetails?.insuredAddress ?? null },
    { label: "Policy Period", value: policyDetails?.policyPeriod ?? null },
  ];

  const sendMessage = () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    void runChat(text, text, "text");
  };

  const openPicker = () => fileInputRef.current?.click();

  const handleUploadEvidence = async () => {
    if (uploading || photos.length === 0) return;
    const claimRef = policyNumber.trim();
    if (!claimRef) {
      setUploadResult({
        ok: 0,
        failed: photos.length,
        error: "Enter a policy number before uploading documents.",
      });
      return;
    }
    setUploading(true);
    setUploadResult(null);
    let ok = 0;
    let failed = 0;
    let firstError: string | null = null;
    for (const photo of photos) {
      try {
        const form = new FormData();
        form.append("claim_number", claimRef);
        form.append("uploaded_by_role", "Policyholder");
        form.append("file", photo.file, photo.name);
        const resp = await fetch(DOCUMENT_UPLOAD_ENDPOINT, {
          method: "POST",
          body: form,
        });
        const data = await resp.json().catch(() => null);
        if (!resp.ok) {
          failed += 1;
          if (!firstError) {
            firstError =
              (data && (data.detail || data.error)) ||
              `Upload failed (${resp.status})`;
          }
          continue;
        }
        ok += 1;
      } catch (err) {
        failed += 1;
        if (!firstError) {
          firstError =
            err instanceof Error ? err.message : "Upload failed. Try again.";
        }
      }
    }
    setUploading(false);
    setUploadResult({ ok, failed, error: firstError });
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-2 text-blue-700 font-semibold mb-4">
          <MessageSquare className="h-5 w-5" />
          Chat With Your Claims Assistant
        </div>

        <div
          ref={scrollRef}
          className="h-[420px] overflow-y-auto rounded-xl border border-gray-100 bg-gray-50/60 p-4 space-y-5"
        >
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-3 ${
                msg.role === "user" ? "flex-row-reverse" : ""
              }`}
            >
              {/* Avatar */}
              <div
                className={`h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ${
                  msg.role === "agent"
                    ? "bg-gradient-to-br from-indigo-900 to-blue-600 text-white"
                    : "bg-blue-500 text-white"
                }`}
              >
                {msg.role === "agent" ? (
                  <Bot className="h-4 w-4" />
                ) : (
                  <User className="h-4 w-4" />
                )}
              </div>

              {/* Bubble */}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-sm ${
                  msg.role === "agent"
                    ? "bg-white border border-gray-200"
                    : "bg-blue-600 text-white text-sm leading-relaxed"
                }`}
              >
                {msg.role === "agent" ? (
                  msg.text ? (
                    <AgentMessage text={msg.text} />
                  ) : (
                    /* streaming placeholder dots */
                    <span className="flex gap-1 items-center h-5">
                      <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
                      <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
                      <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
                    </span>
                  )
                ) : (
                  msg.text
                )}
              </div>
            </div>
          ))}
          {sending && messages[messages.length - 1]?.role !== "agent" && (
            <div className="flex items-center gap-2 text-xs text-gray-400 pl-11">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Assistant is typing...
            </div>
          )}
        </div>

        <div className="mt-4 flex items-end gap-2">
          <button
            type="button"
            onClick={toggle}
            aria-label="Speak your answer"
            className={`h-11 w-11 rounded-full flex items-center justify-center flex-shrink-0 text-white transition-colors ${
              listening
                ? "bg-red-500 animate-pulse"
                : transcribing
                ? "bg-blue-400"
                : "bg-gradient-to-br from-indigo-900 to-blue-600 hover:opacity-90"
            }`}
          >
            {transcribing ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Mic className="h-5 w-5" />
            )}
          </button>
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void sendMessage();
              }
            }}
            placeholder={
              listening
                ? "Listening... tap the mic to stop"
                : "Type your answer, or tap the mic to speak..."
            }
            className="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-2.5 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
          />
          <button
            type="button"
            onClick={sendMessage}
            disabled={!input.trim() || sending}
            className={`h-11 w-11 rounded-full flex items-center justify-center flex-shrink-0 text-white transition-colors ${
              !input.trim() || sending
                ? "bg-blue-300 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-2 text-blue-700 font-semibold">
          <Camera className="h-5 w-5" />
          Add Evidence
          <span className="text-[11px] font-semibold text-gray-400">Optional</span>
        </div>
        <p className="text-sm text-gray-500 mt-1 mb-5">
          Upload photos or documents of the damage. You can attach files, but
          it's optional.
        </p>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,application/pdf,.pdf,.doc,.docx,.txt"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              onAddPhotos(e.target.files);
            }
            e.target.value = "";
          }}
        />

        <div
          role="button"
          tabIndex={0}
          onClick={openPicker}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              openPicker();
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
              onAddPhotos(e.dataTransfer.files);
            }
          }}
          className={`rounded-xl border-2 border-dashed px-6 py-12 flex flex-col items-center justify-center text-center transition-colors cursor-pointer outline-none focus-visible:border-blue-400 focus-visible:bg-blue-50/30 ${
            isDragging
              ? "border-blue-400 bg-blue-50/50"
              : "border-gray-200 hover:border-blue-400 hover:bg-blue-50/30"
          }`}
        >
          <UploadCloud className="h-10 w-10 text-gray-300 mb-3" />
          <div className="font-semibold text-gray-700">Drag photos here</div>
          <div className="text-sm text-gray-400 mt-1">or click to browse</div>
        </div>

        {photos.length > 0 && (
          <div className="mt-4">
            <div className="text-sm font-semibold text-gray-600 mb-2">
              {photos.length} file{photos.length > 1 ? "s" : ""} attached
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {photos.map((photo) => (
                <div
                  key={photo.id}
                  className="group relative rounded-xl overflow-hidden border border-gray-200 bg-gray-50"
                >
                  {photo.isImage ? (
                    <img
                      src={photo.url}
                      alt={photo.name}
                      className="h-28 w-full object-cover"
                    />
                  ) : (
                    <div className="h-28 w-full flex items-center justify-center bg-gray-100">
                      <FileText className="h-9 w-9 text-gray-400" />
                    </div>
                  )}
                  <button
                    type="button"
                    aria-label={`Remove ${photo.name}`}
                    onClick={() => onRemovePhoto(photo.id)}
                    className="absolute top-1.5 right-1.5 h-7 w-7 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/80 transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </button>
                  <div className="px-2 py-1.5 text-[11px] text-gray-500 truncate">
                    {photo.name}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {photos.length > 0 && (
          <div className="mt-4 flex flex-col gap-2">
            <button
              type="button"
              onClick={handleUploadEvidence}
              disabled={uploading}
              className={`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 font-bold text-white shadow-md transition-colors ${
                uploading
                  ? "bg-blue-300 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              {uploading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <UploadCloud className="h-5 w-5" />
              )}
              {uploading
                ? "Uploading..."
                : `Upload ${photos.length} document${
                    photos.length > 1 ? "s" : ""
                  }`}
            </button>
            {uploadResult && (
              <div
                className={`text-sm rounded-lg px-3 py-2 border ${
                  uploadResult.failed === 0
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : "bg-red-50 text-red-600 border-red-200"
                }`}
              >
                {uploadResult.ok > 0 &&
                  `${uploadResult.ok} document${
                    uploadResult.ok > 1 ? "s" : ""
                  } uploaded successfully. `}
                {uploadResult.failed > 0 &&
                  `${uploadResult.failed} failed${
                    uploadResult.error ? `: ${uploadResult.error}` : "."
                  }`}
              </div>
            )}
          </div>
        )}

        <textarea
          className="w-full h-24 mt-4 p-4 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none resize-none transition-all"
          placeholder="Add any comments about the evidence (optional)..."
          value={comments}
          onChange={(e) => onCommentsChange(e.target.value)}
        ></textarea>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-2 text-emerald-600 font-semibold">
          <Shield className="h-5 w-5" />
          Your Policy Information
        </div>
        <p className="text-sm text-gray-500 mt-1 mb-5">
          Retrieved from policy system. Please confirm.
        </p>
        {policyLoading ? (
          <div className="flex items-center gap-2 text-sm text-gray-500 px-1 py-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading policy information...
          </div>
        ) : policyError ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {policyError}
          </div>
        ) : (
          <div className="space-y-3">
            {policyFields.map((row, idx) => {
              const Icon = POLICY_ICONS[idx] ?? FileText;
              return (
                <div
                  key={row.label}
                  className="flex items-center justify-between gap-3 rounded-xl border border-gray-200 px-4 py-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Icon className="h-5 w-5 text-emerald-500 flex-shrink-0" />
                    <div className="min-w-0">
                      <div className="text-xs text-gray-400">{row.label}</div>
                      <div className="font-semibold text-gray-800 truncate">
                        {row.value ?? "Not available"}
                      </div>
                    </div>
                  </div>
                  <SourceTag variant="auto-filled" label="Auto-Filled" />
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="bg-violet-50 px-6 py-3 flex items-center gap-2 text-violet-700 font-semibold text-sm">
          <Sparkles className="h-4 w-4" />
          What AI Extracted From Your Description
        </div>
        <div className="p-6 overflow-x-auto">
          {submissionLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-500 py-6">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading extracted loss details...
            </div>
          ) : lossFields.length === 0 ? (
            <div className="text-sm text-gray-500 py-6">
              {submissionError ??
                "No extracted loss details are available yet. Continue chatting with the assistant to capture them."}
            </div>
          ) : (
            <table className="w-full border-collapse min-w-[720px]">
              <thead>
                <tr className="text-left text-sm text-gray-500 border-b border-gray-100">
                  <th className="font-medium py-2 pr-4">Field</th>
                  <th className="font-medium py-2 pr-4">Value</th>
                  <th className="font-medium py-2 pr-4">Source</th>
                  <th className="font-medium py-2">Human Review</th>
                </tr>
              </thead>
              <tbody>
                {lossFields.map((row) => (
                  <tr key={row.field} className="border-b border-gray-50">
                    <td className="py-3 pr-4 text-sm text-gray-700">
                      {row.field}
                      {row.required && <span className="text-red-500"> *</span>}
                    </td>
                    <td className="py-3 pr-4 text-sm font-semibold text-gray-800">
                      {row.value ?? "Not specified"}
                    </td>
                    <td className="py-3 pr-4">{sourceTagFor(row.source)}</td>
                    <td className="py-3 pr-2">
                      <input
                        type="text"
                        value={humanReview[row.field] ?? row.value ?? ""}
                        onChange={(e) =>
                          onHumanReviewChange(row.field, e.target.value)
                        }
                        className="w-full min-w-[180px] rounded-lg border border-gray-200 px-3 py-1.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-amber-200 bg-amber-50 px-6 py-5 flex items-center justify-between gap-4">
        <div className="text-sm font-semibold text-amber-700">
          Overall Agent Confidence
        </div>
        {overallConfidence === null ? (
          <ConfidenceIndicator value={null} />
        ) : (
          <div className="text-3xl font-extrabold text-amber-500">
            {overallConfidence}%
          </div>
        )}
      </div>

      {saveEditsError && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {saveEditsError}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          disabled={isSavingEdits}
          className="rounded-xl border border-gray-200 px-6 py-3 font-semibold text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          Back
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={isSavingEdits}
          className={`flex-1 rounded-xl py-3 font-bold text-white shadow-md transition-colors flex items-center justify-center gap-2 ${
            isSavingEdits ? "bg-blue-400 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700"
          }`}
        >
          {isSavingEdits ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Saving your edits…
            </>
          ) : (
            <>
              Review and Confirm Fields
              <ChevronRight className="h-4 w-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
