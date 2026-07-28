export interface ClaimRecord {
  id: string;
  status: string;
  description: string;
  date: string;
  type: string;
  location: string;
  policyholder: string;
  policyNumber: string;
  dateFiled: string;
  dateOfLoss: string;
  estimatedCost: string;
  severity: string;
  coverage: string;
  assessmentSummary: string;
  aiConfidence: number | null;
}
