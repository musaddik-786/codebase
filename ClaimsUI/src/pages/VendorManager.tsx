import { useState } from "react";
import { personas, vendorGroups } from "@/config/agents";
import { AgentGroupGrid } from "@/components/AgentGroupGrid";

export function VendorManager() {
  const [claimId, setClaimId] = useState("CLM-2026-1001");
  const [vendorId, setVendorId] = useState("VND-2024-001");
  const persona = personas.vendor;

  return (
    <div>
      <h1 className="text-2xl mb-1" style={{ color: `hsl(var(--${persona.color}))` }}>
        Vendor Manager
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
          <label className="text-sm font-medium">Vendor ID:</label>
          <input
            className="rounded-md border px-3 py-1.5 text-sm bg-background w-44"
            value={vendorId}
            onChange={(e) => setVendorId(e.target.value)}
            placeholder="VND-2024-001"
          />
        </div>
        <span className="text-xs text-muted-foreground">
          Both IDs are prefixed to every message sent to vendor agents.
        </span>
      </div>

      <AgentGroupGrid
        groups={vendorGroups}
        agents={persona.agents}
        claimId={claimId}
        secondaryContext={vendorId ? `Vendor ${vendorId}` : undefined}
      />
    </div>
  );
}
