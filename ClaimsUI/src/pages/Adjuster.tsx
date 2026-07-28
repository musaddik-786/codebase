import { useState } from "react";
import { personas, adjusterGroups } from "@/config/agents";
import { ClaimIdInput } from "@/components/ClaimIdInput";
import { AgentGroupGrid } from "@/components/AgentGroupGrid";

export function Adjuster() {
  const [claimId, setClaimId] = useState("CLM-2026-1001");
  const persona = personas.adjuster;

  return (
    <div>
      <h1 className="text-2xl mb-1" style={{ color: `hsl(var(--${persona.color}))` }}>
        Claims Adjuster
      </h1>
      <p className="text-muted-foreground mb-4">{persona.description}</p>
      <ClaimIdInput claimId={claimId} onChange={setClaimId} />
      <AgentGroupGrid groups={adjusterGroups} agents={persona.agents} claimId={claimId} />
    </div>
  );
}
