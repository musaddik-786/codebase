interface Props {
  claimId: string;
  onChange: (v: string) => void;
}

export function ClaimIdInput({ claimId, onChange }: Props) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <label className="text-sm font-medium">Claim ID:</label>
      <input
        className="rounded-md border px-3 py-1.5 text-sm bg-background w-48"
        value={claimId}
        onChange={(e) => onChange(e.target.value)}
        placeholder="CLM-2026-1001"
      />
      <span className="text-xs text-muted-foreground">
        Prefixed to messages as "For claim {claimId}: ..."
      </span>
    </div>
  );
}
