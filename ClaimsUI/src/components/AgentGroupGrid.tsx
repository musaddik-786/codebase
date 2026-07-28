import { useState } from "react";
import { ChevronDown, ChevronRight, Zap, Info } from "lucide-react";
import type { AgentDef } from "@/config/agents";
import { AgentChatPanel } from "./AgentChatPanel";

interface Group {
  title: string;
  slugs: string[];
}

interface Props {
  groups: Group[];
  agents: AgentDef[];
  claimId: string;
  /** Optional secondary context label (e.g. "Vendor: VND-001" or "SIU Case: SIU-001") */
  secondaryContext?: string;
}

export function AgentGroupGrid({ groups, agents, claimId, secondaryContext }: Props) {
  const [open, setOpen] = useState<Record<string, boolean>>({ [groups[0]?.title ?? ""]: true });
  const [quickPrompt, setQuickPrompt] = useState<Record<string, string | null>>({});

  const bySlug = Object.fromEntries(agents.map((a) => [a.slug, a]));

  function buildMsg(text: string): string {
    const parts: string[] = [];
    if (claimId) parts.push(`For claim ${claimId}`);
    if (secondaryContext) parts.push(secondaryContext);
    parts.push(text);
    return parts.join(": ");
  }

  return (
    <div className="space-y-4">
      {groups.map((group) => {
        const isOpen = open[group.title] ?? false;
        const groupAgents = group.slugs.map((s) => bySlug[s]).filter(Boolean) as AgentDef[];
        return (
          <div key={group.title} className="border rounded-lg overflow-hidden">
            <button
              className="w-full flex items-center justify-between px-4 py-2 bg-muted/50 font-medium text-sm"
              onClick={() => setOpen((o) => ({ ...o, [group.title]: !isOpen }))}
            >
              <span className="flex items-center gap-2">
                {group.title}
                <span className="text-xs font-normal text-muted-foreground">
                  ({groupAgents.length} agent{groupAgents.length !== 1 ? "s" : ""})
                </span>
              </span>
              {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>

            {isOpen && (
              <div className="p-3 grid grid-cols-1 md:grid-cols-2 gap-4">
                {groupAgents.map((agent) => {
                  const qp = quickPrompt[agent.slug] ?? null;
                  return (
                    <div key={agent.slug}>
                      {/* Agent header row */}
                      <div className="flex items-start justify-between mb-1 gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-xs font-mono text-muted-foreground truncate">
                              {agent.name}
                            </span>
                            {agent.status === "placeholder" && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-yellow-100 text-yellow-800 border border-yellow-300 shrink-0">
                                placeholder
                              </span>
                            )}
                          </div>
                          {agent.description && (
                            <p className="text-[11px] text-muted-foreground mt-0.5 leading-tight">
                              {agent.description}
                            </p>
                          )}
                        </div>

                        {agent.quickTestPrompt && (
                          <button
                            title="Insert quick-test prompt"
                            onClick={() =>
                              setQuickPrompt((prev) => ({
                                ...prev,
                                [agent.slug]: prev[agent.slug] ? null : agent.quickTestPrompt ?? null,
                              }))
                            }
                            className={`shrink-0 inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] transition-colors ${
                              qp
                                ? "bg-primary text-primary-foreground border-primary"
                                : "bg-muted text-muted-foreground border-border hover:bg-primary/10"
                            }`}
                          >
                            <Zap className="h-3 w-3" />
                            Quick Test
                          </button>
                        )}
                      </div>

                      {/* Preview of the quick-test prompt before sending */}
                      {qp && (
                        <div className="mb-1 rounded border border-dashed border-primary/40 bg-primary/5 px-2 py-1 text-[11px] text-muted-foreground leading-snug flex gap-1.5 items-start">
                          <Info className="h-3 w-3 mt-0.5 shrink-0 text-primary/60" />
                          <span className="line-clamp-2">{qp}</span>
                        </div>
                      )}

                      <AgentChatPanel
                        agentName={agent.name}
                        baseUrl={agent.baseUrl}
                        buildMessage={buildMsg}
                        externalMessage={qp ?? undefined}
                        onExternalMessageSent={() =>
                          setQuickPrompt((prev) => ({ ...prev, [agent.slug]: null }))
                        }
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
