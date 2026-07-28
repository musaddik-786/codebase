import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  tools?: string[];
}

interface AgentChatPanelProps {
  agentName: string;
  baseUrl: string;
  placeholder?: string;
  /** Optional transform applied to the user's raw text before sending. */
  buildMessage?: (text: string) => string;
  /** External trigger: when this value changes (and is non-empty), send it as a message. */
  externalMessage?: string | null;
  onExternalMessageSent?: () => void;
  /** When true, the input is locked and no messages can be sent. */
  disabled?: boolean;
  /** Message shown below the locked input. */
  disabledHint?: string;
}

const TOOL_REGEX = /\[Tool:\s*([^\]]+)\]\s*(Starting|Done)/gi;

export function AgentChatPanel({
  agentName,
  baseUrl,
  placeholder = "Type a message...",
  buildMessage,
  externalMessage,
  onExternalMessageSent,
  disabled = false,
  disabledHint,
}: AgentChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (externalMessage) {
      send(externalMessage);
      onExternalMessageSent?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [externalMessage]);


  async function send(rawText: string) {
    const text = rawText.trim();
    if (!text || loading || disabled) return;

    const finalMessage = buildMessage ? buildMessage(text) : text;

    // Capture history before state update — these are all completed turns so far
    const historySnapshot = messages.map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    const assistantIndex = (msgs: ChatMessage[]) => msgs.length;
    setMessages((prev) => [...prev, { role: "assistant", content: "", tools: [] }]);

    try {
      const resp = await fetch(`${baseUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: finalMessage, history: historySnapshot }),
      });

      if (!resp.ok || !resp.body) {
        throw new Error(`HTTP ${resp.status}`);
      }

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
    }

    function appendToAssistant(chunk: string) {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (!last || last.role !== "assistant") return prev;

        // Extract tool-call markers
        const tools = [...(last.tools ?? [])];
        let content = last.content;
        let remaining = chunk;
        let m: RegExpExecArray | null;
        TOOL_REGEX.lastIndex = 0;
        let cleaned = "";
        let lastEnd = 0;
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
    void assistantIndex;
  }

  return (
    <div className="flex flex-col border rounded-lg bg-card overflow-hidden h-[480px]">
      <div className="px-4 py-2 border-b bg-muted/50 text-sm font-medium flex items-center justify-between">
        <span>{agentName}</span>
        <span className="text-xs text-muted-foreground font-mono">{baseUrl}</span>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <p className="text-sm text-muted-foreground italic">
            Send a message to start a conversation with {agentName}.
          </p>
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
                <div className="flex flex-wrap gap-1 mb-1">
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

      <form
        className="flex flex-col gap-1 p-2 border-t"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-md border px-3 py-2 text-sm bg-background disabled:opacity-50 disabled:cursor-not-allowed"
            placeholder={disabled ? (disabledHint ?? "Confirm details above to begin…") : placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading || disabled}
          />
          <button
            type="submit"
            disabled={loading || !input.trim() || disabled}
            className="inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
      </form>
    </div>
  );
}
