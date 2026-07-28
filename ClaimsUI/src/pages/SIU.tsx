import { useState } from "react";
import { personas, siuGroups } from "@/config/agents";
import { AgentGroupGrid } from "@/components/AgentGroupGrid";

export function SIU() {
  const [claimId, setClaimId] = useState("CLM-2026-1001");
  const [siuCaseId, setSiuCaseId] = useState("SIU-2026-0001");
  const persona = personas.siu;

  return (
    <div>
      <h1 className="text-2xl mb-1" style={{ color: `hsl(var(--${persona.color}))` }}>
        SIU Investigator
      </h1>
      <p className="text-muted-foreground mb-4">{persona.description}</p>

      {/* ID inputs */}
      <div className="flex flex-wrap items-center gap-4 mb-4 p-3 rounded-lg border bg-muted/30">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Claim ID:</label>
          <input
            className="rounded-md border px-3 py-1.5 text-sm bg-background w-44"
            value={claimId}
            onChange={(e) => setClaimId(e.target.value)}
            placeholder="CLM-2026-1001"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">SIU Case ID:</label>
          <input
            className="rounded-md border px-3 py-1.5 text-sm bg-background w-44"
            value={siuCaseId}
            onChange={(e) => setSiuCaseId(e.target.value)}
            placeholder="SIU-2026-0001"
          />
        </div>
        <span className="text-xs text-muted-foreground">
          Both IDs are prefixed to every message sent to SIU agents.
        </span>
      </div>

      <AgentGroupGrid
        groups={siuGroups}
        agents={persona.agents}
        claimId={claimId}
        secondaryContext={siuCaseId ? `SIU Case ${siuCaseId}` : undefined}
      />
    </div>
  );
}
